# app.py
# CONCEDE | Motor de afinidad de cuentas
# Streamlit single-file prototype. Los datos de ejemplo NO representan cartera real.
# La matriz disponible establece pesos 35/25/25/15 (suman 100) y criterios cualitativos.
# La necesidad operativa requiere validación comercial; no se infiere del DENUE.

import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CONCEDE | Motor de Demanda", page_icon="🎯", layout="wide")

# --------------------------- Estilo ejecutivo ---------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background:#f4f7fb; border:1px solid #dce4ef; padding:14px 16px; border-radius:12px;}
.small-note {color:#64748b;font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)

# --------------------------- Datos demostrativos ---------------------------
# Sustituye este bloque cargando el CSV/XLSX real desde la barra lateral.
# La matriz fuente define: sector 35, tamaño 25, geografía 25, requerimiento 15.
DEMO = pd.DataFrame([
    ["Empresa Semilla A","Agroindustria",320,"Guanajuato","Alto","Almacenaje alto volumen",1800000],
    ["Empresa Semilla B","Consumo masivo",180,"Nuevo León","Medio","Transporte terrestre",950000],
    ["Empresa Semilla C","Logística",520,"Veracruz","Alto","Operación In-House",2400000],
    ["Empresa Semilla D","Servicios profesionales",45,"CDMX","Bajo","Flete aislado",120000],
    ["Empresa Semilla E","Retail / Mayoristas",95,"Querétaro","Medio","Picking y etiquetado",680000],
    ["Empresa Semilla F","Agroindustria",28,"Colima","Bajo","Mensajería",90000],
    ["Empresa Semilla G","CPG / Consumo",450,"Coahuila","Alto","Transporte intermodal",2100000],
    ["Empresa Semilla H","Fertilizantes",250,"Tamaulipas","Medio","Almacenaje de sacos",1300000],
    ["Empresa Semilla I","Automotriz",700,"Jalisco","Alto","Operación In-House",1750000],
    ["Empresa Semilla J","Comercio minorista local",12,"Oaxaca","Bajo","Flete aislado",60000],
], columns=["Empresa","Sector","Empleados","Estado","Madurez","Necesidad","Valor potencial MXN"])

SECTORES = ["Agroindustria","CPG / Consumo","Retail / Mayoristas","Logística","Fertilizantes","Automotriz","Servicios profesionales","Comercio minorista local","Otro"]
REGIONES = {
    "Bajío / Centro": ["CDMX","Estado de México","Querétaro","Guanajuato","Aguascalientes","Hidalgo"],
    "Norte": ["Nuevo León","Tamaulipas","Coahuila"],
    "Puertos estratégicos": ["Colima","Veracruz","Tabasco"],
}
ZONAS = sum(REGIONES.values(), [])
MADUREZ = ["Bajo","Medio","Alto"]
NECESIDADES = ["Almacenaje alto volumen","Almacenaje de sacos / granel","Transporte terrestre","Transporte ferroviario / intermodal","Operación In-House","Kitting / picking / etiquetado / reenvasado","Flete aislado","Mudanza","Mensajería"]

def score_row(r, target, weights):
    # Puntaje categórico transparente; necesidad se puntúa como señal y debe confirmarse.
    sector = 100 if r["Sector"] == target["sector"] else (60 if r["Sector"] in ["Agroindustria","CPG / Consumo","Retail / Mayoristas","Logística","Fertilizantes"] else 0)
    emp = float(r["Empleados"])
    if target["empleados_min"] <= emp <= target["empleados_max"]:
        size = 100
    elif emp >= 50:
        size = max(35, 100 - min(abs(emp-target["empleados_max"]), abs(emp-target["empleados_min"])) / max(target["empleados_max"],1)*55)
    else:
        size = 0
    geo = 100 if r["Estado"] in target["estados"] else 0
    needs_good = ["Almacenaje alto volumen","Almacenaje de sacos / granel","Transporte terrestre","Transporte ferroviario / intermodal","Operación In-House","Kitting / picking / etiquetado / reenvasado"]
    need = 100 if r["Necesidad"] in needs_good else 0
    denom = sum(weights.values()) or 1
    return round((sector*weights["Sector"] + size*weights["Tamaño"] + geo*weights["Geografía"] + need*weights["Necesidad"]) / denom, 1)

def classify(r):
    if r["Match Score"] >= 80 and r["Necesidad"] in ["Almacenaje alto volumen","Almacenaje de sacos / granel","Transporte terrestre","Transporte ferroviario / intermodal","Operación In-House","Kitting / picking / etiquetado / reenvasado"]:
        return "Alineación total"
    if r["Match Score"] >= 60 and r["Madurez"] in ["Bajo","Medio"]:
        return "Alto valor / madurez por desarrollar"
    if r["Match Score"] < 45:
        return "Baja alineación"
    return "Cuenta oportunista"

# --------------------------- Sidebar ---------------------------
st.sidebar.title("Matriz de Control")
st.sidebar.caption("Ajusta el perfil objetivo y los pesos. Cambios recalculan el análisis.")
sector_obj = st.sidebar.selectbox("Sector / industria objetivo", SECTORES, index=0)
emp_min, emp_max = st.sidebar.slider("Rango de empleados", 1, 5000, (50, 500), step=10)
estados_obj = st.sidebar.multiselect("Estados / corredores objetivo", ZONAS, default=["Guanajuato","Querétaro","Nuevo León","Tamaulipas","Coahuila","Veracruz","Colima"])
madurez_obj = st.sidebar.selectbox("Madurez tecnológica de referencia", MADUREZ, index=1)
presupuesto = st.sidebar.number_input("Presupuesto estimado por cuenta (MXN)", min_value=0, value=1000000, step=100000)
st.sidebar.markdown("---")
st.sidebar.subheader("Ponderación de la matriz")
w_sector = st.sidebar.slider("Sector / rama", 1, 10, 7)
w_tamano = st.sidebar.slider("Tamaño de empresa", 1, 10, 5)
w_geo = st.sidebar.slider("Geografía / rutas", 1, 10, 5)
w_nec = st.sidebar.slider("Requerimiento operativo", 1, 10, 3)
weights = {"Sector":w_sector, "Tamaño":w_tamano, "Geografía":w_geo, "Necesidad":w_nec}

st.sidebar.markdown("---")
uploaded = st.sidebar.file_uploader("Cargar cartera real (CSV o Excel)", type=["csv","xlsx"])
if uploaded:
    try:
        data = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        required = {"Empresa","Sector","Empleados","Estado","Madurez","Necesidad","Valor potencial MXN"}
        missing = required - set(data.columns)
        if missing:
            st.sidebar.error("Faltan columnas: " + ", ".join(sorted(missing)))
            data = DEMO.copy()
        else:
            st.sidebar.success(f"{len(data):,} registros cargados.")
    except Exception as e:
        st.sidebar.error(f"No se pudo leer el archivo: {e}")
        data = DEMO.copy()
else:
    data = DEMO.copy()

# --------------------------- Normalización y cálculo ---------------------------
for c in ["Empleados","Valor potencial MXN"]:
    data[c] = pd.to_numeric(data[c], errors="coerce").fillna(0)
data["Sector"] = data["Sector"].fillna("Otro").astype(str)
data["Estado"] = data["Estado"].fillna("").astype(str)
data["Madurez"] = data["Madurez"].fillna("Bajo").astype(str)
data["Necesidad"] = data["Necesidad"].fillna("").astype(str)

target = {"sector":sector_obj, "empleados_min":emp_min, "empleados_max":emp_max, "estados":estados_obj, "madurez":madurez_obj, "presupuesto":presupuesto}
data["Match Score"] = data.apply(lambda r: score_row(r, target, weights), axis=1)
data["Clasificación"] = data.apply(classify, axis=1)
data["Prioridad"] = np.select([data["Match Score"]>=80, data["Match Score"]>=60], ["AAA","AA"], default="Validar")
data = data.sort_values("Match Score", ascending=False).reset_index(drop=True)

# --------------------------- Main dashboard ---------------------------
st.title("🎯 CONCEDE | Motor de Generación de Demanda")
st.caption("Explorador de afinidad de cuentas · Prototipo interactivo 4MSFTS")
st.info("El puntaje es una simulación basada en los campos disponibles. La matriz no aporta datos suficientes para deducir necesidad real, facturación, decisor ni presupuesto por empresa: esos puntos deben confirmarse en llamada.")

f1, f2, f3 = st.columns(3)
f1.metric("Match Score promedio", f"{data['Match Score'].mean():.1f}%")
f2.metric("Cuentas AAA", f"{(data['Prioridad']=='AAA').sum():,}")
pipeline = data.loc[data["Match Score"]>=60, "Valor potencial MXN"].sum()
f3.metric("Pipeline potencial (cuentas ≥60%)", f"${pipeline:,.0f} MXN")

st.markdown("### Matriz de oportunidades")
left, right = st.columns([3,1])
with left:
    fig = px.scatter(data, x="Match Score", y="Valor potencial MXN", color="Clasificación",
                     size="Empleados", hover_name="Empresa",
                     hover_data=["Sector","Estado","Empleados","Madurez","Necesidad","Prioridad"],
                     range_x=[0,100], title="Afinidad vs. valor potencial")
    fig.add_vline(x=80, line_dash="dash", annotation_text="Umbral AAA (80%)")
    fig.add_vline(x=60, line_dash="dot", annotation_text="Umbral AA (60%)")
    fig.update_layout(height=480, xaxis_title="Match Score (%)", yaxis_title="Valor potencial estimado (MXN)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("**Lectura de cuadrantes**")
    st.markdown("- **Alineación total:** score ≥80 y necesidad logística pertinente.")
    st.markdown("- **Alto valor / madurez por desarrollar:** score ≥60 y madurez baja/media.")
    st.markdown("- **Baja alineación:** score <45.")
    st.markdown("- **Oportunista:** resto; validar antes de priorizar.")
    st.caption("Clasificación operativa ilustrativa; no equivale a oportunidad confirmada.")

st.markdown("### Tabla dinámica de cuentas")
c1,c2,c3 = st.columns(3)
with c1:
    clas_sel = st.multiselect("Clasificación", sorted(data["Clasificación"].unique()), default=sorted(data["Clasificación"].unique()))
with c2:
    min_score = st.slider("Match mínimo", 0, 100, 0)
with c3:
    estado_sel = st.multiselect("Estado", sorted(data["Estado"].unique()), default=sorted(data["Estado"].unique()))
view = data[data["Clasificación"].isin(clas_sel) & (data["Match Score"]>=min_score) & data["Estado"].isin(estado_sel)].copy()
st.dataframe(view, use_container_width=True, hide_index=True)

csv = view.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Descargar resultados CSV", data=csv, file_name="CONCEDE_cuentas_priorizadas.csv", mime="text/csv")
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    view.to_excel(writer, index=False, sheet_name="Cuentas priorizadas")
st.download_button("⬇️ Descargar resultados Excel", data=excel_buffer.getvalue(), file_name="CONCEDE_cuentas_priorizadas.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Reglas del juego y limitaciones"):
    st.markdown("""
    - Pesos iniciales tomados de la matriz de cliente semilla: Sector 35, Tamaño 25, Geografía 25, Requerimiento 15.
    - En esta app los sliders modifican pesos relativos; se normalizan para que el resultado permanezca en escala 0–100.
    - La matriz describe criterios cualitativos, pero no entrega un diccionario completo de equivalencias ni valores observados por empresa.
    - Los datos precargados son ficticios y sirven únicamente para probar la interfaz.
    - El presupuesto capturado es una referencia del usuario; no se usa como evidencia de capacidad de compra de una cuenta.
    - Antes de producción: validar pesos y reglas con Chema, documentar campos y conectar la base real con fuente/fecha.
    """)

st.markdown('<div class="small-note">4MSFTS · Menos es más · Evidencia antes de tecnología</div>', unsafe_allow_html=True)
