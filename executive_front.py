"""CONSEDE / 4MSFTS executive front.

Presentation-only design system and command-center overview. It does not
change Score V3, source data, Radar calculations, or Mailing delivery.
"""
import streamlit as st


def apply_executive_theme():
    st.markdown(
        """
        <style>
        :root {
          --cns-navy:#142f43; --cns-teal:#12b5a5; --cns-green:#78b85e;
          --cns-gold:#d5ad59; --cns-red:#d64550; --cns-ink:#172f42;
          --cns-muted:#71879a; --cns-canvas:#f1f5f7; --cns-line:#dce5e9;
        }
        html,body,[data-testid="stAppViewContainer"]{background:var(--cns-canvas);color:var(--cns-ink);font-family:Inter,"Segoe UI",Arial,sans-serif}
        [data-testid="stHeader"]{background:var(--cns-teal);height:5px}
        .block-container{max-width:1540px;padding-top:2rem;padding-bottom:2.7rem}
        [data-testid="stSidebar"],[data-testid="stSidebar"]>div:first-child{background:var(--cns-navy);border-right:1px solid #29485c}
        [data-testid="stSidebar"] *{color:#e6eef3}
        [data-testid="stSidebar"] label,[data-testid="stSidebar"] .stCaption{color:#a9bdca!important}
        h1,h2,h3,h4{color:var(--cns-ink)!important;letter-spacing:-.025em}
        h1{font-size:2.25rem!important;font-weight:760!important}
        h2{font-size:1.45rem!important;font-weight:720!important}
        h3{font-size:1.12rem!important;font-weight:700!important}
        p,li,label,[data-testid="stCaptionContainer"]{color:#526b7d}
        [data-testid="stMetric"]{background:#fff;border:1px solid var(--cns-line);border-left:5px solid var(--cns-teal);border-radius:12px;padding:14px 16px;box-shadow:0 2px 5px rgba(18,42,58,.10)}
        [data-testid="stMetricLabel"] p{color:var(--cns-muted)!important;font-size:.75rem!important;font-weight:750!important;text-transform:uppercase;letter-spacing:.04em}
        [data-testid="stMetricValue"]{color:var(--cns-ink)!important;font-size:1.75rem!important;font-weight:780!important}
        [data-testid="stDataFrame"],[data-testid="stTable"]{background:#fff;border:1px solid var(--cns-line);border-radius:10px}
        [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-baseweb="select"]>div{background:#fff;border-color:#cbd8df;border-radius:8px}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{gap:.35rem;border-bottom:1px solid var(--cns-line)}
        [data-testid="stTabs"] button[role="tab"]{color:#5c7485;font-weight:650;padding:.7rem 1rem}
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{color:var(--cns-teal);border-bottom:3px solid var(--cns-teal)}
        .stButton>button,.stDownloadButton>button{border-radius:8px;border:1px solid #cbd8df;font-weight:700;min-height:2.5rem}
        .stButton>button[kind="primary"]{background:var(--cns-teal);color:white;border-color:var(--cns-teal)}
        [data-testid="stAlert"]{border-radius:9px}
        .cns-command-head{display:flex;justify-content:space-between;gap:1rem;margin:.6rem 0 1.8rem}
        .cns-eyebrow{color:#71879a;font-size:.72rem;font-weight:800;letter-spacing:.12em;margin-bottom:.5rem}
        .cns-command-head h1{font-size:2.3rem!important;margin:0}
        .cns-command-head p{margin:.4rem 0 0;color:#71879a}
        .cns-page-index{color:#71879a;font-size:.75rem;font-weight:750}
        .cns-kpi-card{background:#fff;min-height:136px;border:1px solid #dce5e9;border-left:6px solid var(--cns-teal);border-radius:12px;padding:16px;box-shadow:0 2px 5px rgba(18,42,58,.11);margin-bottom:1.5rem}
        .cns-kpi-green{border-left-color:var(--cns-green)}.cns-kpi-gold{border-left-color:var(--cns-gold)}.cns-kpi-red{border-left-color:var(--cns-red)}
        .cns-kpi-label{color:#71879a;font-size:.68rem;font-weight:800}
        .cns-kpi-title{color:#172f42;font-size:1.7rem;font-weight:800;margin:.7rem 0 .5rem}
        .cns-kpi-value{color:#172f42;font-size:.82rem;font-weight:750}
        .cns-kpi-note{color:#8295a4;font-size:.68rem;margin-top:.3rem}
        .cns-command-grid{display:grid;grid-template-columns:1.35fr 1fr;gap:1.2rem;margin:.2rem 0 1.2rem}
        .cns-panel-title{color:#172f42;font-size:1.15rem;font-weight:780;margin-bottom:1.1rem}
        .cns-progress-row{display:grid;grid-template-columns:minmax(125px,.8fr) minmax(130px,1.7fr) 55px 68px;gap:.65rem;align-items:center;margin:1.1rem 0}
        .cns-progress-label{color:#71879a;font-size:.75rem}
        .cns-progress-track{height:14px;border-radius:4px;background:#dfe7ea;overflow:hidden}
        .cns-progress-fill{height:100%;border-radius:3px}
        .cns-fill-teal{background:#12b5a5}.cns-fill-green{background:#78b85e}.cns-fill-gold{background:#d5ad59}.cns-fill-navy{background:#18384e}
        .cns-progress-value{color:#172f42;font-size:.76rem;font-weight:750;text-align:right}
        .cns-progress-tag{color:#172f42;font-size:.69rem;font-weight:750}
        .cns-attention-item{display:flex;gap:.8rem;margin:1.3rem 0}
        .cns-attention-item span{flex:0 0 11px;width:11px;height:11px;background:#12b5a5;border-radius:2px;margin-top:.28rem}
        .cns-attention-item p{margin:0;color:#526b7d;font-size:.83rem}
        .cns-command-footer{color:#172f42;font-size:1rem;font-weight:780;margin:2rem .3rem 2.2rem}
        @media(max-width:950px){.cns-command-grid{grid-template-columns:1fr}.cns-progress-row{grid-template-columns:1fr 1.5fr 42px 58px;gap:.4rem}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_command_center(metrics=None):
    """Show real run metrics only; never manufacture campaign or Radar counts."""
    data = metrics or {}
    raw = int(data.get("raw", 0) or 0)
    eligible = int(data.get("eligible", 0) or 0)
    aaa = int(data.get("aaa", 0) or 0)
    aa = int(data.get("aa", 0) or 0)
    leads = aaa + aa
    has_run = bool(metrics)

    st.markdown(
        """
        <div class="cns-command-head">
          <div><div class="cns-eyebrow">4MSFTS · COMMERCIAL INTELLIGENCE</div>
          <h1>Centro de mando</h1>
          <p>Una lectura ejecutiva del universo, los leads prioritarios y la actividad comercial.</p></div>
          <div class="cns-page-index">01 / 12</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards = [
        ("UNIVERSO OBJETIVO","BASE",f"{raw:,}" if has_run else "—","empresas de origen","teal"),
        ("EMPRESAS FILTRADAS","PERFIL",f"{eligible:,}" if has_run else "—","coincidencia comercial","green"),
        ("PRECLASIFICACIÓN","SCORE V3 ≥60",f"{leads:,}" if has_run else "—","bandas matemáticas; no es AAA comercial","gold"),
        ("SEÑALES DETECTADAS","RADAR","EXPEDIENTE","evidencia individual por empresa","red"),
        ("CAMPAÑAS","MAILING","ACTIVACIÓN","envío y seguimiento","teal"),
    ]
    cols=st.columns(5,gap="medium")
    for col,(label,title,value,note,color) in zip(cols,cards):
        with col:
            st.markdown(
                f'<div class="cns-kpi-card cns-kpi-{color}"><div class="cns-kpi-label">{label}</div>'
                f'<div class="cns-kpi-title">{title}</div><div class="cns-kpi-value">{value}</div>'
                f'<div class="cns-kpi-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="cns-command-grid"><section><div class="cns-panel-title">Lectura del universo comercial</div>',unsafe_allow_html=True)
    stages=[
        ("Universo identificado",raw,raw,"teal","Base"),
        ("Perfil validado",eligible,raw,"green","Filtro"),
        ("Score V3 ≥60",leads,raw,"gold","Score"),
        ("Por validar",int(data.get("validar",0) or 0),raw,"navy","VALIDAR"),
    ]
    for label,value,maximum,color,tag in stages:
        ratio=min(100.0,value/maximum*100) if has_run and maximum else 0
        val=f"{value:,}" if has_run else "—"
        st.markdown(
            f'<div class="cns-progress-row"><div class="cns-progress-label">{label}</div>'
            f'<div class="cns-progress-track"><div class="cns-progress-fill cns-fill-{color}" style="width:{ratio:.2f}%"></div></div>'
            f'<div class="cns-progress-value">{val}</div><div class="cns-progress-tag">{tag}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '</section><section><div class="cns-panel-title">Atención ejecutiva</div>'
        '<div class="cns-attention-item"><span></span><p>Cuentas con mayor ajuste matemático para priorizar su validación</p></div>'
        '<div class="cns-attention-item"><span></span><p>El interés genuino se confirma después del contacto y debe respaldarse con evidencia objetiva</p></div>'
        '<div class="cns-attention-item"><span></span><p>Mailing activa el contacto; una banda de Score no convierte por sí sola a una cuenta en AAA comercial</p></div>'
        '</section></div><div class="cns-command-footer">AAA comercial solo después de contacto, interés genuino y evidencia objetiva. Score V3 es preclasificación, no validación de interés.</div>',
        unsafe_allow_html=True,
    )
