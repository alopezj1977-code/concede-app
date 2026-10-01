# app.py
# 4MSFTS | Motor de Generación de Demanda – multi-cliente
# Streamlit single-file. Los datos de ejemplo NO representan cartera real.
# La matriz de cada cliente vive en configs/*.json – para adaptar a un cliente
# nuevo NO se toca este archivo, solo se agrega/edita su JSON en esa carpeta.

import io
import json
import glob
import os
import unicodedata
from typing import Tuple, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="4MSFTS | Motor de Demanda", page_icon="🎯", layout="wide")

# -------------------------- Estilo ejecutivo --------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background:#f4f7fb; border:1px solid #dce4ef; padding:14px 16px; border-radius:12px;}
.small-note {color:#64748b;font-size:0.88rem;}
.peso-pct {color:#0f766e; font-weight:600; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")

# Columnas clave para la optimizacion extrema de memoria con bases del DENUE (RAM)
COLS_DENUE = ["nom_estab", "raz_social", "nombre_act", "per_ocu", "entidad"]

# Mapeo universal de campos DENUE / archivos genéricos
COL_ALIASES = {
    "nom_estab": ["nom_estab", "nombre", "empresa", "nombre_establecimiento", "establecimiento", "nombre comercial"],
    "raz_social": ["raz_social", "razon social", "razon_social", "empresa_razon"],
    "nombre_act": ["nombre_act", "actividad", "giró", "giro", "sector", "rama", "actividad_economica"],
    "per_ocu": ["per_ocu", "empleados", "tamano", "tamaño", "personal", "estrato_personal", "rango_empleados"],
    "entidad": ["entidad", "estado", "ubicacion", "region", "entidad_federativa"],
}

ESTADOS_MEXICO = [
    "TODAS LAS ENTIDADES", "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR",
    "CAMPECHE", "CHIAPAS", "CHIHUAHUA", "CIUDAD DE MÉXICO", "COAHUILA", "COLIMA",
    "DURANGO", "ESTADO DE MÉXICO", "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO",
    "MICHOACÁN", "MORELOS", "NAYARIT", "NUEVO LEÓN", "OAXACA", "PUEBLA", "QUERÉTARO",
    "QUINTANA ROO", "SAN LUIS POTOSÍ", "SINALOA", "SONORA", "TABASCO", "TAMAULIPAS",
    "TLAXCALA", "VERACRUZ", "YUCATÁN", "ZACATECAS"
]


def normalize_str(val: str) -> str:
    """Normaliza cadenas quitando acentos y espacios extra para matching robusto."""
    if not isinstance(val, str):
        return ""
    val = val.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", val)
        if unicodedata.category(c) != "Mn"
    )


def cargar_configuraciones() -> dict:
    """Carga todos los archivos JSON presentes en configs/."""
    configs = {}
    pattern = os.path.join(CONFIG_DIR, "*.json")
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        key = os.path.splitext(filename)[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                configs[key] = json.load(f)
        except Exception as e:
            st.error(f"Error al cargar {filename}: {e}")
    return configs


def identificar_columnas(df: pd.DataFrame) -> dict:
    """Detecta dinámicamente qué columnas del DataFrame corresponden a las variables del Motor."""
    columnas_lower = {normalize_str(col): col for col in df.columns}
    mapping = {}
    for std_col, aliases in COL_ALIASES.items():
        matched = None
        for alias in aliases:
            norm_alias = normalize_str(alias)
            if norm_alias in columnas_lower:
                matched = columnas_lower[norm_alias]
                break
        mapping[std_col] = matched
    return mapping


def clasifica_sector_denue(df: pd.DataFrame, col_act: Optional[str]) -> pd.Series:
    """
    P0.6: Clasificación comercial DENUE recuperada textualmente del commit V1 db62ce9.
    Orden estricto V1 y fallback 'Otro'.
    """
    if not col_act or col_act not in df.columns:
        return pd.Series(["Otro"] * len(df), index=df.index)

    def mapear_actividad(act):
        if pd.isna(act):
            return "Otro"
        txt = str(act).upper()
        
        # Descalificadores directos de V1 real (db62ce9)
        if any(w in txt for w in [
            "DISTRIBUCION DE ENERGIA", "DISTRIBUCION DE AGUA", "CONSTRUCCION DE OBRAS",
            "TRATAMIENTO DE AGUAS", "SUBESTACION", "SISTEMAS DE RIEGO", "PERFORACIONES",
            "OBRAS PARA EL TRATAMIENTO", "RESTAURANTE", "PREPARACION DE ALIMENTOS PARA CONSUMO",
            "SERVICIOS DE PREPARACION DE ALIMENTOS", "CAFETERIA", "COMEDOR"
        ]):
            return "Otro"

        # 1. Agroindustria (evaluado ANTES de Fertilizantes según orden V1)
        if any(w in txt for w in ["AZUCAR", "INGENIO", "GRANO", "FERTILIZANTE", "AGROINDUSTR", "SEMILLA", "AGRICOLA"]):
            return "Agroindustria"

        # 2. CPG / Consumo
        if any(w in txt for w in ["ALIMENTO", "BEBIDA", "CONSUMO", "PRODUCTOS DE ASEO", "HIGIENE", "PAPEL", "COSMETIC"]):
            return "CPG / Consumo"

        # 3. Retail / Mayoristas
        if any(w in txt for w in [
            "COMERCIO AL POR MAYOR", "MAYORISTA", "DISTRIBUCION DE ALIMENTOS",
            "DISTRIBUCION COMERCIAL", "DISTRIBUCION DE MERCANCIAS", "DISTRIBUCION DE PRODUCTOS",
            "CENTRAL DE ABASTO"
        ]):
            return "Retail / Mayoristas"

        # 4. Logística
        if any(w in txt for w in [
            "AUTOTRANSPORTE", "TRANSPORTE DE CARGA", "ALMACENAMIENTO", "ALMACEN GENERAL",
            "LOGISTIC", "AGENCIA ADUANAL", "TRANSPORTE FERROVIARIO", "FLETE", "FORWARDER"
        ]):
            return "Logística"

        # 5. Fertilizantes
        if any(w in txt for w in ["FERTILIZANTE"]):
            return "Fertilizantes"

        # 6. Servicios profesionales
        if any(w in txt for w in ["SERVICIOS PROFESIONALES", "CONSULTORIA", "DESPACHO", "ASESORIA"]):
            return "Servicios profesionales"

        # 7. Comercio minorista local
        if any(w in txt for w in ["COMERCIO AL POR MENOR", "TIENDA DE ABARROTES", "MINISUPER"]):
            return "Comercio minorista local"

        return "Otro"

    return df[col_act].apply(mapear_actividad)


def detectar_capacidad_propia(df: pd.DataFrame, col_nom: Optional[str], col_raz: Optional[str], marcas_excluir: list) -> pd.Series:
    """
    P0.4: Genera una bandera booleana / texto indicando si el registro tiene
    capacidad logística propia probable, SIN eliminarlo del DataFrame.
    """
    if not marcas_excluir:
        return pd.Series(["No"] * len(df), index=df.index)

    marcas_norm = [normalize_str(m) for m in marcas_excluir if m]

    def check_row(row):
        txt_nom = normalize_str(row[col_nom]) if col_nom and col_nom in row and pd.notna(row[col_nom]) else ""
        txt_raz = normalize_str(row[col_raz]) if col_raz and col_raz in row and pd.notna(row[col_raz]) else ""
        combined = f"{txt_nom} {txt_raz}"
        for marca in marcas_norm:
            if marca in combined:
                return "Sí"
        return "No"

    return df.apply(check_row, axis=1)


def calcular_score_tamano_p01(val) -> float:
    """
    P0.1: Sensibilidad de scoring por estrato de empleados (DENUE).
    Calcula una afinidad continua/escalonada según la cercanía al tamaño objetivo.
    """
    if pd.isna(val):
        return 0.0

    s = str(val).upper()
    if any(m in s for m in ["0 A 5", "1 A 5", "0 A 5 PERSONAS", "0-5"]):
        return 0.0
    elif any(m in s for m in ["6 A 10", "6-10", "6 A 10 PERSONAS"]):
        return 40.0
    elif any(m in s for m in ["11 A 30", "11-30", "11 A 30 PERSONAS"]):
        return 65.0
    elif any(m in s for m in ["31 A 50", "31-50", "31 A 50 PERSONAS"]):
        return 85.0
    elif any(m in s for m in ["51 A 100", "51-100", "51 A 100 PERSONAS"]):
        return 100.0
    elif any(m in s for m in ["101 A 250", "101-250", "101 A 250 PERSONAS"]):
        return 90.0
    elif any(m in s for m in ["251 Y MÁS", "251 Y MAS", "251+", "251 EN ADELANTE"]):
        return 75.0
    else:
        try:
            num = float(val)
            if num <= 5: return 0.0
            elif num <= 10: return 40.0
            elif num <= 30: return 65.0
            elif num <= 50: return 85.0
            elif num <= 100: return 100.0
            elif num <= 250: return 90.0
            else: return 75.0
        except ValueError:
            return 50.0


def es_elegible_target_51plus(val) -> bool:
    """
    P0.6: Universo Elegible Target reconciliado con el benchmark V1.

    Regla: 11 personas ocupadas o más.
    0-5: fuera | 6-10: fuera | 11-30: dentro | 31-50: dentro
    51-100: dentro | 101-250: dentro | 251+: dentro

    Nota: el nombre histórico de la función se conserva para no alterar
    interfaces internas; la lógica P0.6 es ahora 11+ y NO depende de la
    entidad geográfica seleccionada. La geografía se aplica exclusivamente
    dentro del scoring P0.2.
    """
    if pd.isna(val):
        return False
    s = str(val).upper().strip()
    if any(m in s for m in [
        "11 A 30", "11-30", "11 A 30 PERSONAS",
        "31 A 50", "31-50", "31 A 50 PERSONAS",
        "51 A 100", "51-100", "51 A 100 PERSONAS",
        "101 A 250", "101-250", "101 A 250 PERSONAS",
        "251 Y MÁS", "251 Y MAS", "251+", "251 EN ADELANTE"
    ]):
        return True
    try:
        num = float(val)
        return num >= 11
    except ValueError:
        return False


def parse_empleados_num_p02_h1(val) -> int:
    """P0.2-H1: Convierte texto de estrato DENUE a entero representativo para evitar TypeError en Plotly."""
    if pd.isna(val):
        return 0
    s = str(val).upper()
    if "0 A 5" in s: return 3
    if "6 A 10" in s: return 8
    if "11 A 30" in s: return 20
    if "31 A 50" in s: return 40
    if "51 A 100" in s: return 75
    if "101 A 250" in s: return 175
    if "251" in s: return 300
    try:
        return int(float(val))
    except ValueError:
        return 10


def calcular_score_sector(val, sectores_afines: list, sector_clasificado: str = "") -> float:
    if pd.isna(val) and not sector_clasificado:
        return 50.0
    if sector_clasificado and sectores_afines:
        for sec in sectores_afines:
            if normalize_str(sec) in normalize_str(sector_clasificado):
                return 100.0
    val_norm = normalize_str(str(val))
    if sectores_afines:
        for sec in sectores_afines:
            if normalize_str(sec) in val_norm:
                return 100.0
    return 0.0


def calcular_score_geografia_p02(val, estados_seleccionados: list) -> float:
    """P0.2: Scoring geográfico nacional con soporte multiselección y GEO_NEUTRAL."""
    if not estados_seleccionados or "TODAS LAS ENTIDADES" in estados_seleccionados or "GEO_NEUTRAL" in estados_seleccionados:
        return 100.0
    if pd.isna(val):
        return 20.0
    val_norm = normalize_str(str(val))
    for est in estados_seleccionados:
        target_norm = normalize_str(est)
        if target_norm in val_norm or val_norm in target_norm:
            return 100.0
    return 0.0


def procesar_scoring(df: pd.DataFrame, mapping: dict, config: dict, estados_sel: list) -> pd.DataFrame:
    """
    Ejecuta el pipeline entero de scoring P0.1, P0.2, P0.4 y P0.6 sobre el DataFrame.
    """
    res = df.copy()

    col_nom = mapping.get("nom_estab")
    col_raz = mapping.get("raz_social")
    col_act = mapping.get("nombre_act")
    col_emp = mapping.get("per_ocu")
    col_ent = mapping.get("entidad")

    # P0.6: Clasificación sectorial comercial
    res["Sector_Comercial"] = clasifica_sector_denue(res, col_act)

    # P0.4: Señal de capacidad propia probable
    marcas_excluir = config.get("marcas_excluir_capacidad_propia", [])
    res["Señal: Capacidad propia probable"] = detectar_capacidad_propia(res, col_nom, col_raz, marcas_excluir)

    # P0.2-H1: Columna numérica auxiliar para gráficos Plotly
    res["Empleados_Num"] = res[col_emp].apply(parse_empleados_num_p02_h1) if col_emp and col_emp in res.columns else 10

    # Scores individuales
    sectores_afines = config.get("sectores_afines", [])
    res["Score_Sector"] = res.apply(
        lambda r: calcular_score_sector(r[col_act], sectores_afines, r["Sector_Comercial"]) if col_act and col_act in res.columns else 50.0,
        axis=1
    )
    res["Score_Tamano"] = res[col_emp].apply(calcular_score_tamano_p01) if col_emp and col_emp in res.columns else 50.0
    res["Score_Geografia"] = res[col_ent].apply(lambda x: calcular_score_geografia_p02(x, estados_sel)) if col_ent and col_ent in res.columns else 100.0
    res["Score_Necesidad"] = 0.0  # Benchmark V1: sin señal de necesidad, no sumar afinidad artificial

    # Ponderación
    pesos = config.get("pesos_defecto", {"sector": 35, "tamano": 25, "geografia": 25, "necesidad": 15})
    w_sec = pesos.get("sector", 35) / 100.0
    w_tam = pesos.get("tamano", 25) / 100.0
    w_geo = pesos.get("geografia", 25) / 100.0
    w_nec = pesos.get("necesidad", 15) / 100.0

    res["Match Score"] = (
        res["Score_Sector"] * w_sec +
        res["Score_Tamano"] * w_tam +
        res["Score_Geografia"] * w_geo +
        res["Score_Necesidad"] * w_nec
    )

    # Categorización AAA / AA / A
    umb = config.get("umbrales", {"AAA": 75, "AA": 55})
    u_aaa = umb.get("AAA", 75)
    u_aa = umb.get("AA", 55)

    def categorizar(s):
        if s >= u_aaa: return "AAA"
        if s >= u_aa: return "AA"
        return "A"

    res["Categoria"] = res["Match Score"].apply(categorizar)
    return res


def render_p03_funnel_panel(df_raw, df_elegibles, umbral_aaa, ticket_promedio):
    """
    Renderiza el panel de métricas del Funnel Comercial (P0.3 / P0.6).
    Garantiza trazabilidad dinámica del universo de referencia sin hardcoding.
    """
    # Nivel 1: Universo DENUE de Referencia (CSV Crudo)
    universo_referencia_denue = len(df_raw)
    
    # Nivel 2: Universo Elegible Target (>= 51 empleados)
    universo_elegible_tamano = len(df_elegibles)
    
    # Nivel 3 a 6: Cálculos sobre Universo Elegible usando campo nativo 'Match Score'
    afinidad_promedio = df_elegibles['Match Score'].mean() if universo_elegible_tamano > 0 else 0.0
    cuentas_aaa = len(df_elegibles[df_elegibles['Match Score'] >= umbral_aaa])
    penetracion_aaa = (cuentas_aaa / universo_elegible_tamano * 100) if universo_elegible_tamano > 0 else 0.0
    pipeline_potencial = cuentas_aaa * ticket_promedio

    st.subheader("📊 Funnel de Inteligencia Comercial")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("1. Universo DENUE Referencia", f"{universo_referencia_denue:,} registros DENUE", 
                  help="Total de registros/unidades económicas del archivo crudo INEGI.")
    with col2:
        st.metric("2. Universo Elegible Target", f"{universo_elegible_tamano:,} registros elegibles",
                  help="Registros con 11 o más personas ocupadas.")
    with col3:
        st.metric("3. Índice Afinidad Promedio", f"{afinidad_promedio:.1f} / 100",
                  help="Calculado sobre el universo elegible target.")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("4. Cuentas Alta Prioridad (AAA)", f"{cuentas_aaa:,}")
    with col5:
        st.metric("5. Penetración AAA", f"{penetracion_aaa:.2f}%")
    with col6:
        st.metric("6. Pipeline Potencial Estimado", f"${pipeline_potencial:,.2f} MXN")

    st.caption(
        "**Notas metodológicas:**\n"
        "• **Universo de referencia:** Registros DENUE cargados en la corrida.\n"
        "• **Universo elegible target:** Registros con 11 o más personas ocupadas (0-10 fuera del universo elegible).\n"
        "• **Afinidad:** Índice relativo de alineación con el perfil objetivo (Match Score); no implica intención de compra.\n"
        "• **Pipeline:** Estimación matemática basada en ticket configurado ($69,600 MXN); requiere validación comercial."
    )


def generar_datos_ejemplo() -> pd.DataFrame:
    """Genera dataset mock para validación de UI cuando no hay archivo cargado."""
    return pd.DataFrame({
        "nom_estab": ["Logística del Bajío", "Manufacturas León", "Plásticos Silao", "Textiles Irapuato", "Calzado Celaya", "Transportes Querétaro", "Empaques Romita", "Sistemas San Fe", "Comercial San Miguel", "Distribuidora Salamanca"],
        "raz_social": ["Logística Bajío SA de CV", "Manufacturas León S de RL", "Plásticos Silao SA", "Textiles Irapuato SA de CV", "Calzado Celaya SA", "Transportes Querétaro SA de CV", "Bimbo de México SA de CV", "Sistemas San Fe SA", "Walmart de México SAB", "Distribuidora Salamanca SA"],
        "nombre_act": ["Autotransporte de carga general", "Fabricación de partes de vehículos", "Fabricación de productos de plástico", "Fabricación de prendas de vestir", "Fabricación de calzado", "Servicios de almacenamiento", "Fabricación de envases de cartón", "Comercio al por mayor", "Supermercados", "Comercio de abarrotes"],
        "per_ocu": ["51 a 100 personas", "101 a 250 personas", "51 a 100 personas", "101 a 250 personas", "51 a 100 personas", "251 y más personas", "251 y más personas", "51 a 100 personas", "251 y más personas", "101 a 250 personas"],
        "entidad": ["Guanajuato", "Guanajuato", "Guanajuato", "Guanajuato", "Guanajuato", "Querétaro", "Guanajuato", "Guanajuato", "Guanajuato", "Guanajuato"]
    })


def render_diagnostico_madurez():
    """Módulo cualitativo de Diagnóstico de Madurez Operativa."""
    st.subheader("📋 Diagnóstico de Madurez Operativa y Logística")
    st.markdown("Avaliación cualitativa complementaria para la gestión telefónica / presencial de cuentas AA y AAA.")
    
    col1, col2 = st.columns(2)
    with col1:
        q1 = st.selectbox("1. ¿Cuenta con infraestructura de almacenamiento propia?", ["Sí, capacidad suficiente", "Sí, saturado / overflow", "No, subcontrata 100%"])
        q2 = st.selectbox("2. ¿Flota de transporte asignada?", ["Propia completa", "Mixta", "Tercerizada / Búsqueda de proveedores"])
    with col2:
        q3 = st.selectbox("3. ¿Sistemas de gestión operativa (WMS/TMS/ERP)?", ["ERP + WMS/TMS integrado", "Básico / Excel", "Sin sistema automatizado"])
        q4 = st.selectbox("4. ¿Nivel de urgencia / estacionalidad actual?", ["Alta (Temporada Pico / Urgente)", "Media (Planeación trimestral)", "Baja / Exploratoria"])
        
    st.text_area("Notas del Prospectador / SDR:", placeholder="Registrar comentarios de la llamada...")


def main():
    st.title("🎯 CONCEDE | Motor de Generación de Demanda")
    st.markdown("<p class='small-note'>Entorno de Pruebas: Branch <b>motor-v2</b></p>", unsafe_allow_html=True)

    configs = cargar_configuraciones()
    if not configs:
        st.error("No se encontraron archivos JSON de configuración en la carpeta configs/.")
        st.stop()

    # Sidebar: Selección de Cliente / Matriz
    st.sidebar.header("🏢 Cliente Objetivo")
    cliente_sel = st.sidebar.selectbox("Seleccionar Configuración:", list(configs.keys()))
    config = configs[cliente_sel]

    st.sidebar.divider()
    st.sidebar.header("🌍 Cobertura Geográfica (P0.2)")

    estados_sel = st.sidebar.multiselect(
        "Entidades Federativas Objetivos:",
        ESTADOS_MEXICO,
        default=["TODAS LAS ENTIDADES"],
        help="Selecciona una o más entidades. 'TODAS LAS ENTIDADES' aplica criterio neutral (100% en geografía)."
    )

    st.sidebar.divider()
    st.sidebar.header("⚙️ Parámetros Comerciales")

    ticket_prom = config.get("ticket_promedio", 69600.0)
    ticket_input = st.sidebar.number_input("Ticket Promedio por Cuenta (MXN)", value=float(ticket_prom), step=5000.0, format="%.2f")

    umb = config.get("umbrales", {"AAA": 75, "AA": 55})
    umbral_aaa = st.sidebar.slider("Umbral Cuenta AAA", min_value=50.0, max_value=90.0, value=float(umb.get("AAA", 75)), step=5.0)

    # Carga de Archivo DENUE con fallback exclusivo por UnicodeDecodeError usando exactamente COLS_DENUE
    st.sidebar.divider()
    st.sidebar.header("📁 Ingesta de Datos DENUE")
    uploaded_file = st.sidebar.file_uploader("Cargar CSV / Excel de INEGI:", type=["csv", "xlsx"])

    is_demo = False
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                try:
                    df_raw = pd.read_csv(
                        uploaded_file,
                        encoding="utf-8",
                        usecols=lambda c: normalize_str(c) in [normalize_str(x) for x in COLS_DENUE],
                        low_memory=False
                    )
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(
                        uploaded_file,
                        encoding="latin-1",
                        usecols=lambda c: normalize_str(c) in [normalize_str(x) for x in COLS_DENUE],
                        low_memory=False
                    )
            else:
                df_raw = pd.read_excel(uploaded_file)
            st.success(f"Dataset cargado exitosamente: **{len(df_raw):,}** registros leídos.")
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()
    else:
        df_raw = generar_datos_ejemplo()
        is_demo = True
        st.info("💡 **Modo Demostración Activo:** Mostrando dataset de ejemplo (10 registros). Carga un archivo DENUE en la barra lateral para analizar datos reales.")

    mapping = identificar_columnas(df_raw)

    # Filtro de elegibilidad V1 / reconciliacion de benchmark
    col_emp = mapping.get("per_ocu")
    if col_emp and col_emp in df_raw.columns:
        df_elegibles = df_raw[df_raw[col_emp].apply(es_elegible_target_51plus)].copy()
    else:
        df_elegibles = df_raw.copy()

    # Procesar Scoring P0.1, P0.2, P0.4, P0.6
    df_scored = procesar_scoring(df_elegibles, mapping, config, estados_sel)

    # Render Panel P0.3
    render_p03_funnel_panel(df_raw, df_scored, umbral_aaa, ticket_input)

    st.divider()

    # Pestañas de Análisis Completas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Matriz de Priorización", 
        "📊 Gráficos & Dispersión", 
        "📋 Diagnóstico de Madurez", 
        "⚙️ Configuración & Diagnóstico"
    ])

    with tab1:
        st.subheader("📋 Cartera de Cuentas Priorizadas")
        
        # Filtro rápido por Categoría
        cats = st.multiselect("Filtrar por Categoría:", ["AAA", "AA", "A"], default=["AAA", "AA"])
        df_show = df_scored[df_scored["Categoria"].isin(cats)].copy()

        st.dataframe(
            df_show.sort_values(by="Match Score", ascending=False),
            use_container_width=True
        )

        # Descarga
        csv = df_show.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 Descargar Cartera Filtrada (CSV)",
            data=csv,
            file_name=f"cartera_priorizada_{cliente_sel}.csv",
            mime="text/csv"
        )

    with tab2:
        st.subheader("📊 Análisis Espacial y Dispersión de Cuentas")
        col_nom = mapping.get("nom_estab", "nom_estab")

        # Fix P0.4: Pasa la señal al símbolo de forma segura si la columna está en df_scored
        symbol_col = "Señal: Capacidad propia probable" if "Señal: Capacidad propia probable" in df_scored.columns else None

        fig = px.scatter(
            df_scored,
            x="Match Score",
            y="Empleados_Num",
            color="Categoria",
            symbol=symbol_col,
            hover_name=col_nom if col_nom and col_nom in df_scored.columns else None,
            title="Afinidad (Match Score) vs Tamaño de Empresa (Empleados)",
            labels={"Empleados_Num": "Empleados Estimados", "Match Score": "Índice de Afinidad (0-100)"},
            color_discrete_map={"AAA": "#0f766e", "AA": "#2563eb", "A": "#94a3b8"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        render_diagnostico_madurez()

    with tab4:
        st.subheader("⚙️ Diagnóstico de Reglas de Negocio")
        st.json(config)


if __name__ == "__main__":
    main()
