# app.py
# 4MSFTS | Motor de Generación de Demanda — multi-cliente
# Streamlit single-file. Los datos de ejemplo NO representan cartera real.
# La matriz de cada cliente vive en configs/*.json — para adaptar a un cliente
# nuevo NO se toca este archivo, solo se agrega/edita su JSON en esa carpeta.

import io
import json
import glob
import os
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="4MSFTS | Motor de Demanda", page_icon="🎯", layout="wide")

# --------------------------- Estilo ejecutivo ---------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background:#f4f7fb; border:1px solid #dce4ef; padding:14px 16px; border-radius:12px;}
.small-note {color:#64748b;font-size:0.88rem;}
.peso-pct {color:#0f766e; font-weight:600; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")


# --------------------------- Carga de configuraciones por cliente ---------------------------
def cargar_configs():
    configs = {}
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        configs[cfg.get("cliente", os.path.basename(path))] = cfg
    return configs


def _normaliza(texto):
    if not texto:
        return ""
    texto = str(texto).strip().upper()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


# El INEGI nombra a varios estados con su sufijo oficial completo en el DENUE
# (ej. "Coahuila de Zaragoza", "Veracruz de Ignacio de la Llave"), no con el
# nombre corto que usa la gente. Esta tabla traduce el nombre "humano" que
# elige el usuario en el menu a todas las variantes reales que puede traer
# el DENUE, para que el filtro de geografia no falle en silencio.
ALIAS_ESTADOS = {
    "CIUDAD DE MEXICO": ["CIUDAD DE MEXICO", "DISTRITO FEDERAL", "CDMX"],
    "ESTADO DE MEXICO": ["MEXICO", "ESTADO DE MEXICO"],
    "COAHUILA": ["COAHUILA", "COAHUILA DE ZARAGOZA"],
    "VERACRUZ": ["VERACRUZ", "VERACRUZ DE IGNACIO DE LA LLAVE"],
    "MICHOACAN": ["MICHOACAN", "MICHOACAN DE OCAMPO"],
}


def estado_coincide(estado_dato, estados_objetivo):
    """Compara el estado de una empresa contra la lista de estados objetivo,
    usando la tabla de alias para nombres oficiales largos del DENUE."""
    dato_norm = _normaliza(estado_dato)
    for objetivo in estados_objetivo:
        obj_norm = _normaliza(objetivo)
        variantes = ALIAS_ESTADOS.get(obj_norm, [obj_norm])
        if any(_normaliza(v) == dato_norm for v in variantes):
            return True
    return False


CONFIGS = cargar_configs()
if not CONFIGS:
    st.error(
        "No se encontró ningún archivo de configuración en la carpeta 'configs/'. "
        "Agrega al menos un archivo JSON (por ejemplo configs/consede.json) con la matriz del cliente."
    )
    st.stop()

# --------------------------- Sidebar: selector de cliente ---------------------------
st.sidebar.title("Matriz de Control")
cliente_sel = st.sidebar.selectbox("Cliente / matriz activa", list(CONFIGS.keys()))
CFG = CONFIGS[cliente_sel]
st.sidebar.caption(f"{CFG.get('descripcion', '')}")
st.sidebar.caption("¿Cliente nuevo? Agrega un archivo .json en la carpeta configs/ con su propia matriz — no se toca este código.")
st.sidebar.markdown("---")

SECTORES = CFG["sectores"]
SECTORES_AFINES = set(CFG.get("sectores_afines", []))
REGIONES = CFG["regiones"]
ZONAS = sum(REGIONES.values(), [])
NECESIDADES = CFG["necesidades"]
NECESIDADES_AFINES = set(CFG.get("necesidades_afines", []))
MARCAS_EXCLUIR = CFG.get("marcas_excluir", [])
MADUREZ = ["Bajo", "Medio", "Alto", "Por confirmar"]
DIAG = CFG.get("diagnostico_madurez")

DEMO = pd.DataFrame([
    ["Empresa Semilla A", "Agroindustria", 320, "Guanajuato", "Alto", "Almacenaje alto volumen", 1800000],
    ["Empresa Semilla B", "Consumo masivo", 180, "Nuevo León", "Medio", "Transporte terrestre", 950000],
    ["Empresa Semilla C", "Logística", 520, "Veracruz", "Alto", "Operación In-House", 2400000],
    ["Empresa Semilla D", "Servicios profesionales", 45, "CDMX", "Bajo", "Flete aislado", 120000],
    ["Empresa Semilla E", "Retail / Mayoristas", 95, "Querétaro", "Medio", "Picking y etiquetado", 680000],
    ["Empresa Semilla F", "Agroindustria", 28, "Colima", "Bajo", "Mensajería", 90000],
    ["Empresa Semilla G", "CPG / Consumo", 450, "Coahuila", "Alto", "Transporte intermodal", 2100000],
    ["Empresa Semilla H", "Fertilizantes", 250, "Tamaulipas", "Medio", "Almacenaje de sacos", 1300000],
    ["Empresa Semilla I", "Automotriz", 700, "Jalisco", "Alto", "Operación In-House", 1750000],
    ["Empresa Semilla J", "Comercio minorista local", 12, "Oaxaca", "Bajo", "Flete aislado", 60000],
], columns=["Empresa", "Sector", "Empleados", "Estado", "Madurez", "Necesidad", "Valor potencial MXN"])


# --------------------------- Mapeo automático de DENUE crudo ---------------------------
def es_denue(columnas):
    cols = {c.strip().lower() for c in columnas}
    return "nom_estab" in cols or "nombre_act" in cols


def mapea_denue(df_crudo):
    df = df_crudo.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    empresa = df.get("nom_estab", pd.Series([""] * len(df))).fillna("")
    razon = df.get("raz_social", pd.Series([""] * len(df))).fillna("")
    empresa = empresa.where(empresa.str.strip() != "", razon)
    out = pd.DataFrame({
        "Empresa": empresa,
        "Sector": df.get("nombre_act", ""),
        "Empleados": df.get("per_ocu", ""),
        "Estado": df.get("entidad", ""),
        "Madurez": "Por confirmar",
        "Necesidad": "",
        "Valor potencial MXN": 0,
    })
    return out


def _parsea_empleados(valor):
    if pd.isna(valor) or valor == "":
        return 0
    texto = str(valor).strip()
    try:
        return float(texto)
    except ValueError:
        pass
    t = _normaliza(texto)
    numeros = [int(n) for n in t.replace("A", " ").split() if n.isdigit()]
    if "Y MAS" in t:
        return float(numeros[0]) if numeros else 0
    if len(numeros) >= 2:
        return (numeros[0] + numeros[1]) / 2
    if len(numeros) == 1:
        return float(numeros[0])
    return 0


def clasifica_sector_denue(rama_texto):
    """Aproxima el Sector (categoria de la matriz) a partir del texto libre de
    actividad economica del DENUE, usando los sectores afines del cliente."""
    t = _normaliza(rama_texto)
    mapa = {
        "Agroindustria": ["AZUCAR", "INGENIO", "GRANO", "FERTILIZANTE", "AGROINDUSTR", "SEMILLA", "AGRICOLA"],
        "CPG / Consumo": ["ALIMENTO", "BEBIDA", "CONSUMO", "HIGIENE", "PAPEL", "COSMETIC"],
        "Retail / Mayoristas": ["COMERCIO AL POR MAYOR", "MAYORISTA", "ABASTO", "DISTRIBUCION DE ALIMENTOS", "DISTRIBUCION COMERCIAL"],
        "Logística": ["AUTOTRANSPORTE", "TRANSPORTE DE CARGA", "ALMACENAMIENTO", "ALMACEN GENERAL", "LOGISTIC", "AGENCIA ADUANAL", "FLETE", "FORWARDER"],
        "Fertilizantes": ["FERTILIZANTE"],
        "Servicios profesionales": ["SERVICIOS PROFESIONALES", "CONSULTORIA", "DESPACHO", "ASESORIA"],
        "Comercio minorista local": ["COMERCIO AL POR MENOR", "TIENDA DE ABARROTES", "MINISUPER"],
    }
    for sector, kws in mapa.items():
        for kw in kws:
            if kw in t:
                return sector
    return "Otro"


# --------------------------- Scoring ---------------------------
def score_row(r, target, weights):
    sector = 100 if r["Sector"] == target["sector"] else (60 if r["Sector"] in SECTORES_AFINES else 0)
    emp = float(r["Empleados"])
    if target["empleados_min"] <= emp <= target["empleados_max"]:
        size = 100
    elif emp >= 50:
        size = max(35, 100 - min(abs(emp - target["empleados_max"]), abs(emp - target["empleados_min"])) / max(target["empleados_max"], 1) * 55)
    else:
        size = 0
    geo = 100 if estado_coincide(r["Estado"], target["estados"]) else 0
    need = 100 if r["Necesidad"] in NECESIDADES_AFINES else (50 if r["Necesidad"] == "" else 0)
    denom = sum(weights.values()) or 1
    return round((sector * weights["Sector"] + size * weights["Tamaño"] + geo * weights["Geografía"] + need * weights["Necesidad"]) / denom, 1)


def es_marca_excluida(nombre_empresa):
    t = _normaliza(nombre_empresa)
    for marca in MARCAS_EXCLUIR:
        if _normaliza(marca) in t:
            return marca
    return None


def classify(r):
    if r["Match Score"] >= CFG["umbral_aaa"] and r["Necesidad"] in NECESIDADES_AFINES:
        return "Alineación total"
    if r["Match Score"] >= CFG["umbral_aa"] and r["Madurez"] in ["Bajo", "Medio", "Por confirmar"]:
        return "Alto valor / madurez por desarrollar"
    if r["Match Score"] < CFG["umbral_baja"]:
        return "Baja alineación"
    return "Cuenta oportunista"


# --------------------------- Sidebar: perfil objetivo y pesos ---------------------------
st.sidebar.caption("Ajusta el perfil objetivo y los pesos. Cambios recalculan el análisis.")
idx_sector = SECTORES.index(CFG["sector_objetivo_default"]) if CFG["sector_objetivo_default"] in SECTORES else 0
sector_obj = st.sidebar.selectbox("Sector / industria objetivo", SECTORES, index=idx_sector)
emp_min, emp_max = st.sidebar.slider("Rango de empleados", 1, 5000, tuple(CFG["empleados_rango_default"]), step=10)
estados_obj = st.sidebar.multiselect("Estados / corredores objetivo", ZONAS, default=ZONAS)
presupuesto = st.sidebar.number_input(
    "Ticket promedio por cuenta cerrada (MXN)", min_value=0, value=1000000, step=50000,
    help="Tú lo capturas con base en el historial real de contratos. No se calcula de ninguna base de datos."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Ponderación de la matriz")
pd_ = CFG["pesos_default"]
w_sector = st.sidebar.slider("Sector / rama", 1, 10, pd_["Sector"])
w_tamano = st.sidebar.slider("Tamaño de empresa", 1, 10, pd_["Tamaño"])
w_geo = st.sidebar.slider("Geografía / rutas", 1, 10, pd_["Geografía"])
w_nec = st.sidebar.slider("Requerimiento operativo", 1, 10, pd_["Necesidad"])
weights = {"Sector": w_sector, "Tamaño": w_tamano, "Geografía": w_geo, "Necesidad": w_nec}

# --- Normalizacion VISIBLE: se muestra el % real que representa cada peso ---
suma_pesos = sum(weights.values()) or 1
st.sidebar.markdown(
    "".join(
        f'<div class="peso-pct">{k}: {v} → {v/suma_pesos*100:.0f}% del peso total</div>'
        for k, v in weights.items()
    ),
    unsafe_allow_html=True,
)
st.sidebar.caption("Los pesos se normalizan automáticamente para sumar 100%, sin importar los valores de los sliders.")

st.sidebar.markdown("---")
uploaded = st.sidebar.file_uploader("Cargar cartera real (CSV o Excel)", type=["csv", "xlsx"])

# --------------------------- Estado de sesión (para poder editar Madurez luego) ---------------------------
fuente_actual = uploaded.name if uploaded else f"DEMO::{cliente_sel}"
if st.session_state.get("_fuente") != fuente_actual:
    st.session_state["_fuente"] = fuente_actual
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                try:
                    df_crudo = pd.read_csv(uploaded, encoding="utf-8")
                except UnicodeDecodeError:
                    uploaded.seek(0)
                    df_crudo = pd.read_csv(uploaded, encoding="latin-1")
            else:
                df_crudo = pd.read_excel(uploaded)
            if es_denue(df_crudo.columns):
                st.sidebar.info("Formato DENUE detectado — mapeando Empresa, Sector, Empleados y Estado automáticamente.")
                data = mapea_denue(df_crudo)
                data["Sector"] = data["Sector"].apply(clasifica_sector_denue)
                data["Empleados"] = data["Empleados"].apply(_parsea_empleados)
                excluidas = data["Empresa"].apply(es_marca_excluida)
                n_excl = excluidas.notna().sum()
                data = data[excluidas.isna()].reset_index(drop=True)
                st.sidebar.success(f"{len(data):,} registros cargados. {n_excl:,} excluidos por ser marcas con flotilla/almacenes propios conocidos.")
                st.sidebar.warning("Madurez y Necesidad quedaron 'Por confirmar' / vacías — el DENUE no las tiene. Complétalas con el Diagnóstico de Madurez o en la llamada de Chema.")
            else:
                required = {"Empresa", "Sector", "Empleados", "Estado"}
                missing = required - set(df_crudo.columns)
                if missing:
                    st.sidebar.error("Faltan columnas obligatorias: " + ", ".join(sorted(missing)))
                    data = DEMO.copy()
                else:
                    data = df_crudo.copy()
                    for opc, default in [("Madurez", "Por confirmar"), ("Necesidad", ""), ("Valor potencial MXN", 0)]:
                        if opc not in data.columns:
                            data[opc] = default
                    st.sidebar.success(f"{len(data):,} registros cargados.")
        except Exception as e:
            st.sidebar.error(f"No se pudo leer el archivo: {e}")
            data = DEMO.copy()
    else:
        data = DEMO.copy()
    st.session_state["cartera"] = data

data = st.session_state["cartera"].copy()

# --------------------------- Normalización de tipos ---------------------------
for c in ["Empleados", "Valor potencial MXN"]:
    data[c] = pd.to_numeric(data[c], errors="coerce").fillna(0)
data["Sector"] = data["Sector"].fillna("Otro").astype(str)
data["Estado"] = data["Estado"].fillna("").astype(str)
data["Madurez"] = data["Madurez"].fillna("Por confirmar").astype(str)
data["Necesidad"] = data["Necesidad"].fillna("").astype(str)

target = {"sector": sector_obj, "empleados_min": emp_min, "empleados_max": emp_max, "estados": estados_obj}
data["Match Score"] = data.apply(lambda r: score_row(r, target, weights), axis=1)
data["Clasificación"] = data.apply(classify, axis=1)
data["Prioridad"] = np.select([data["Match Score"] >= CFG["umbral_aaa"], data["Match Score"] >= CFG["umbral_aa"]], ["AAA", "AA"], default="Validar")
data = data.sort_values("Match Score", ascending=False).reset_index(drop=True)

# --------------------------- Main dashboard ---------------------------
st.title(f"🎯 {cliente_sel} | Motor de Generación de Demanda")
st.caption("Explorador de afinidad de cuentas · Prototipo interactivo 4MSFTS")
if uploaded is None:
    st.warning("Estás viendo DATOS DE EJEMPLO (ficticios). Carga un CSV real en la barra lateral para ver resultados reales.", icon="⚠️")
st.info("El puntaje es una simulación basada en los campos disponibles. La matriz no aporta datos suficientes para deducir necesidad real, facturación, decisor ni presupuesto por empresa: esos puntos deben confirmarse en llamada.")

f1, f2, f3 = st.columns(3)
f1.metric("Match Score promedio", f"{data['Match Score'].mean():.1f}%")
n_aaa = (data["Prioridad"] == "AAA").sum()
f2.metric("Cuentas AAA", f"{n_aaa:,}")
pipeline_estimado = n_aaa * presupuesto
f3.metric("Pipeline potencial estimado", f"${pipeline_estimado:,.0f} MXN", help="Cuentas AAA × ticket promedio capturado arriba. No es un valor observado por cuenta.")

# --------------------------- Diagnóstico de Madurez (manual, batería real) ---------------------------
if DIAG:
    with st.expander("🧪 Diagnóstico de Madurez — " + DIAG["titulo"]):
        st.caption(DIAG["objetivo"])
        empresa_diag = st.selectbox("Empresa a diagnosticar", data["Empresa"].tolist(), key="empresa_diag")
        respuestas = []
        for i, preg in enumerate(DIAG["preguntas"]):
            resp = st.select_slider(
                preg["texto"], options=list(DIAG["escala"].keys()),
                value="Ni de acuerdo ni en desacuerdo" if "Ni de acuerdo ni en desacuerdo" in DIAG["escala"] else list(DIAG["escala"].keys())[2],
                key=f"diag_{i}",
            )
            respuestas.append(DIAG["escala"][resp] * preg["peso"])
        score_diag = sum(respuestas)
        banda = next(b for b in DIAG["bandas"] if score_diag <= b["max"])
        st.markdown(f"**Resultado: {score_diag:.2f} / 5 — {banda['etiqueta']}** ({banda['madurez']})")
        st.caption(banda["detalle"])
        if st.button("Guardar este resultado como Madurez de la empresa"):
            idx = st.session_state["cartera"].index[st.session_state["cartera"]["Empresa"] == empresa_diag]
            st.session_state["cartera"].loc[idx, "Madurez"] = banda["madurez"]
            st.success(f"Madurez de '{empresa_diag}' actualizada a '{banda['madurez']}'. Vuelve a correr el análisis arriba ↑")
            st.rerun()

st.markdown("### Matriz de oportunidades")
left, right = st.columns([3, 1])
with left:
    fig = px.scatter(data, x="Match Score", y="Valor potencial MXN", color="Clasificación",
                      size="Empleados", hover_name="Empresa",
                      hover_data=["Sector", "Estado", "Empleados", "Madurez", "Necesidad", "Prioridad"],
                      range_x=[0, 100], title="Afinidad vs. valor potencial")
    fig.add_vline(x=CFG["umbral_aaa"], line_dash="dash", annotation_text=f"Umbral AAA ({CFG['umbral_aaa']}%)")
    fig.add_vline(x=CFG["umbral_aa"], line_dash="dot", annotation_text=f"Umbral AA ({CFG['umbral_aa']}%)")
    fig.update_layout(height=480, xaxis_title="Match Score (%)", yaxis_title="Valor potencial estimado (MXN)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("**Lectura de cuadrantes**")
    st.markdown("- **Alineación total:** score alto y necesidad logística pertinente.")
    st.markdown("- **Alto valor / madurez por desarrollar:** score medio-alto y madurez baja/media/sin confirmar.")
    st.markdown("- **Baja alineación:** score bajo.")
    st.markdown("- **Oportunista:** resto; validar antes de priorizar.")
    st.caption("Clasificación operativa ilustrativa; no equivale a oportunidad confirmada.")
    if "Valor potencial MXN" in data.columns and (data["Valor potencial MXN"] == 0).all():
        st.caption("⚠️ 'Valor potencial MXN' está en 0 para todos — viene de datos reales del DENUE, que no incluye esta cifra. El eje Y no es informativo hasta que se capture manualmente.")

st.markdown("### Tabla dinámica de cuentas")
c1, c2, c3 = st.columns(3)
with c1:
    clas_sel = st.multiselect("Clasificación", sorted(data["Clasificación"].unique()), default=sorted(data["Clasificación"].unique()))
with c2:
    min_score = st.slider("Match mínimo", 0, 100, 0)
with c3:
    estado_sel = st.multiselect("Estado", sorted(data["Estado"].unique()), default=sorted(data["Estado"].unique()))
view = data[data["Clasificación"].isin(clas_sel) & (data["Match Score"] >= min_score) & data["Estado"].isin(estado_sel)].copy()
st.dataframe(view, use_container_width=True, hide_index=True)

csv = view.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Descargar resultados CSV", data=csv, file_name=f"{cliente_sel}_cuentas_priorizadas.csv", mime="text/csv")
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    view.to_excel(writer, index=False, sheet_name="Cuentas priorizadas")
st.download_button("⬇️ Descargar resultados Excel", data=excel_buffer.getvalue(), file_name=f"{cliente_sel}_cuentas_priorizadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Reglas del juego y limitaciones"):
    st.markdown(f"""
    - Matriz activa: **{cliente_sel}**, cargada desde `configs/{cliente_sel.lower()}.json` (o el archivo correspondiente).
    - Pesos iniciales de esa matriz: Sector {pd_['Sector']}, Tamaño {pd_['Tamaño']}, Geografía {pd_['Geografía']}, Necesidad {pd_['Necesidad']} — se normalizan siempre a 100%, muévelos como quieras.
    - Al subir un CSV crudo del DENUE, Sector/Empleados/Estado se mapean solos; Madurez y Necesidad quedan pendientes de confirmar (no existen en esa fuente).
    - Se excluyen automáticamente marcas con flotilla/almacenes propios conocidos (lista en el archivo de configuración del cliente).
    - El Diagnóstico de Madurez usa la batería real de preguntas — no es un estimado inventado, pero sí requiere que alguien la conteste por cada empresa.
    - El ticket promedio y el pipeline estimado son una referencia capturada por el usuario, no evidencia de capacidad de compra de una cuenta.
    - Antes de producción: validar pesos y reglas con Chema, documentar campos y conectar la base real con fuente/fecha.
    """)

st.markdown('<div class="small-note">4MSFTS · Menos es más · Evidencia antes de tecnología</div>', unsafe_allow_html=True)
