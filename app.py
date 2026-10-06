```python
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core import load_config, run, ConfigError, identify_columns


ROOT = Path(__file__).parent
CFG = load_config(ROOT / "concede_v3.json")

st.set_page_config(
    page_title="CONCEDE V3",
    page_icon="🎯",
    layout="wide"
)

ENTIDADES = CFG["geography"]["entities"]
OPTIONS = ["TODAS LAS ENTIDADES"] + ENTIDADES

st.title("🎯 CONCEDE V3 | Motor de Generación de Demanda")
st.caption(
    "Motor único · 32 entidades · parámetros por corrida · "
    "Score / Prioridad / Valor Potencial separados"
)

with st.sidebar:
    st.header("P0.2 · Cobertura")

    selected = st.multiselect(
        "Entidades objetivo",
        OPTIONS,
        default=["TODAS LAS ENTIDADES"]
    )

    st.header("Elegibilidad")

    employee_minimum = st.number_input(
        "Mínimo de empleados",
        min_value=0,
        value=int(CFG["eligibility"]["employee_minimum"]),
        step=1
    )

    max_default = CFG["eligibility"].get("employee_maximum")

    employee_maximum = st.number_input(
        "Máximo de empleados (0 = sin límite)",
        min_value=0,
        value=0 if max_default is None else int(max_default),
        step=1
    )

    st.caption(
        "La elegibilidad es configurable por corrida. "
        "0 en máximo = sin límite superior."
    )

    st.header("Fuente")

    uploaded = st.file_uploader(
        "CSV / Excel",
        type=["csv", "xlsx"]
    )

    run_label = st.text_input(
        "Run_ID (opcional)"
    )

    st.header("Necesidad")

    st.info(
        "Sin evidencia comercial, Score_Necesidad = 0. "
        "No se infiere desde DENUE."
    )


if uploaded is None:
    st.warning(
        "Carga la base de la corrida. CONCEDE V3 no descarga "
        "automáticamente el DENUE nacional."
    )
    st.stop()


try:
    if uploaded.name.lower().endswith(".csv"):
        try:
            df = pd.read_csv(
                uploaded,
                encoding="utf-8",
                low_memory=False
            )
        except UnicodeDecodeError:
            uploaded.seek(0)
            df = pd.read_csv(
                uploaded,
                encoding="latin1",
                low_memory=False
            )
    else:
        df = pd.read_excel(uploaded)

except Exception as e:
    st.error(f"No fue posible leer la fuente: {e}")
    st.stop()


selected_real = (
    ENTIDADES
    if "TODAS LAS ENTIDADES" in selected
    else selected
)

max_emp = (
    None
    if employee_maximum == 0
    else employee_maximum
)

run_id = (
    run_label.strip()
    or datetime.datetime.now().strftime("CONCEDE-%Y%m%d-%H%M%S")
)


try:
    result, metrics = run(
        df,
        CFG,
        selected_real,
        run_id=run_id,
        employee_minimum=employee_minimum,
        employee_maximum=max_emp
    )

except ConfigError as e:
    st.error(str(e))
    st.stop()


m = st.columns(6)

m[0].metric(
    "Universo",
    f"{metrics['raw']:,}"
)

m[1].metric(
    "Elegibles",
    f"{metrics['eligible']:,}"
)

m[2].metric(
    "Candidatos",
    f"{metrics['commercial_candidates']:,}"
)

m[3].metric(
    "AAA",
    f"{metrics['aaa']:,}"
)

m[4].metric(
    "AA",
    f"{metrics['aa']:,}"
)

m[5].metric(
    "Valor potencial",
    f"${metrics['valor_potencial']:,.0f}"
)


st.caption(
    "Clasificación V3: AAA 80–100 · AA 60–79.99 · "
    "VALIDAR <60. Valor potencial = AAA × ticket promedio configurado."
)


show = [
    "Run_ID",
    "Rule_Version",
    "Sector_Comercial",
    "Estrato_Tamano",
    "Score_Sector",
    "Score_Tamano",
    "Score_Geografia",
    "Score_Necesidad",
    "Score_V3",
    "Prioridad",
    "Capacidad_Propia",
    "CRM_Estado",
    "Target_Geografico",
    "Candidato_Comercial"
]


mp = identify_columns(result)

for logical in [
    "id",
    "nom_estab",
    "raz_social",
    "nombre_act",
    "entidad",
    "municipio"
]:
    c = mp.get(logical)

    if c and c not in show:
        show.insert(0, c)


show = [
    c
    for c in show
    if c in result.columns
]


st.dataframe(
    result[show]
    .sort_values(
        ["Candidato_Comercial", "Score_V3"],
        ascending=[False, False]
    )
    .head(5000),
    use_container_width=True,
    height=520
)


st.download_button(
    "⬇️ Descargar corrida CSV",
    result.to_csv(
        index=False,
        encoding="utf-8-sig"
    ),
    file_name=f"{run_id}.csv",
    mime="text/csv"
)
```
