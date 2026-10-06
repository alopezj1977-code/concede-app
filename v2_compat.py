import pandas as pd
import unicodedata

def normalize_str(val):
    if not isinstance(val,str): return ""
    val=val.strip().lower()
    return "".join(c for c in unicodedata.normalize('NFD',val) if unicodedata.category(c)!='Mn')

def clasifica_sector_denue(act):
    if pd.isna(act): return 'Otro'
    txt=str(act).upper()
    if any(w in txt for w in ['DISTRIBUCION DE ENERGIA','DISTRIBUCION DE AGUA','CONSTRUCCION DE OBRAS','TRATAMIENTO DE AGUAS','SUBESTACION','SISTEMAS DE RIEGO','PERFORACIONES','OBRAS PARA EL TRATAMIENTO','RESTAURANTE','PREPARACION DE ALIMENTOS PARA CONSUMO','SERVICIOS DE PREPARACION DE ALIMENTOS','CAFETERIA','COMEDOR']): return 'Otro'
    if any(w in txt for w in ['AZUCAR','INGENIO','GRANO','FERTILIZANTE','AGROINDUSTR','SEMILLA','AGRICOLA']): return 'Agroindustria'
    if any(w in txt for w in ['ALIMENTO','BEBIDA','CONSUMO','PRODUCTOS DE ASEO','HIGIENE','PAPEL','COSMETIC']): return 'CPG / Consumo'
    if any(w in txt for w in ['COMERCIO AL POR MAYOR','MAYORISTA','DISTRIBUCION DE ALIMENTOS','DISTRIBUCION COMERCIAL','DISTRIBUCION DE MERCANCIAS','DISTRIBUCION DE PRODUCTOS','CENTRAL DE ABASTO']): return 'Retail / Mayoristas'
    if any(w in txt for w in ['AUTOTRANSPORTE','TRANSPORTE DE CARGA','ALMACENAMIENTO','ALMACEN GENERAL','LOGISTIC','AGENCIA ADUANAL','TRANSPORTE FERROVIARIO','FLETE','FORWARDER']): return 'Logística'
    if any(w in txt for w in ['FERTILIZANTE']): return 'Fertilizantes'
    if any(w in txt for w in ['SERVICIOS PROFESIONALES','CONSULTORIA','DESPACHO','ASESORIA']): return 'Servicios profesionales'
    if any(w in txt for w in ['COMERCIO AL POR MENOR','TIENDA DE ABARROTES','MINISUPER']): return 'Comercio minorista local'
    return 'Otro'

def score_sector(activity, sector):
    # Historical V2 scoring: affinity=100, non-affinity=0.
    if sector in ['Agroindustria','CPG / Consumo','Retail / Mayoristas','Logística']: return 100.0
    return 0.0

def score_size_historical(val):
    if pd.isna(val): return 0.0
    s=str(val).upper()
    # Intentionally preserved because this is a compatibility profile, not V3 logic.
    if any(m in s for m in ['0 A 5','1 A 5','0 A 5 PERSONAS','0-5']): return 0.0
    elif any(m in s for m in ['6 A 10','6-10','6 A 10 PERSONAS']): return 40.0
    elif any(m in s for m in ['11 A 30','11-30','11 A 30 PERSONAS']): return 65.0
    elif any(m in s for m in ['31 A 50','31-50','31 A 50 PERSONAS']): return 85.0
    elif any(m in s for m in ['51 A 100','51-100','51 A 100 PERSONAS']): return 100.0
    elif any(m in s for m in ['101 A 250','101-250','101 A 250 PERSONAS']): return 90.0
    elif any(m in s for m in ['251 Y MÁS','251 Y MAS','251+','251 EN ADELANTE']): return 75.0
    return 50.0

def run_v2_compat(df):
    raw=len(df)
    eligible=df[df['per_ocu'].astype(str).str.lower().str.strip().isin(['11 a 30 personas','31 a 50 personas','51 a 100 personas','101 a 250 personas','251 y más personas'])].copy()
    eligible['Sector_Comercial']=eligible['nombre_act'].apply(clasifica_sector_denue)
    eligible['Score_Sector']=eligible['Sector_Comercial'].apply(lambda x: score_sector(None,x))
    eligible['Score_Tamano']=eligible['per_ocu'].apply(score_size_historical)
    eligible['Score_Geografia']=100.0
    eligible['Score_Necesidad']=0.0
    eligible['Match_Score']=eligible['Score_Sector']*.35+eligible['Score_Tamano']*.25+eligible['Score_Geografia']*.25+eligible['Score_Necesidad']*.15
    aaa=int((eligible['Match_Score']>=75).sum())
    return {'raw':raw,'eligible':len(eligible),'aaa':aaa,'pipeline':aaa*69600}
