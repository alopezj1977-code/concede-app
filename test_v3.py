import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine.core import load_config, run, ConfigError

ROOT=Path(__file__).parents[1]
CFG=load_config(ROOT/'config/concede_v3.json')

def sample():
    return pd.DataFrame({'id':[1,2,3,4],'nom_estab':['A','B','C','D'],'raz_social':['A SA','B SA','C SA','D SA'],'nombre_act':['Almacenamiento y logística','Comercio al por mayor de alimentos','Restaurante','Servicios de oficina'],'per_ocu':['51 a 100 personas','11 a 30 personas','51 a 100 personas','6 a 10 personas'],'entidad':['Querétaro','Nuevo León','Tamaulipas','Querétaro'],'municipio':['Querétaro','Monterrey','Reynosa','Querétaro']})

def test_catalog_32(): assert len(CFG['geography']['entities'])==32

def test_multiselect():
    df=sample(); r1,_=run(df,CFG,['QUERÉTARO'],'Q'); r2,_=run(df,CFG,['NUEVO LEÓN','TAMAULIPAS'],'NT'); assert len(r1)==len(r2)==len(df)

def test_need_zero():
    r,_=run(sample(),CFG,['QUERÉTARO'],'N'); assert (r['Score_Necesidad']==0).all()

def test_unknown_size_errors():
    df=sample(); df.loc[0,'per_ocu']='ESTRATO DESCONOCIDO'
    try: run(df,CFG,['QUERÉTARO'],'E')
    except ConfigError: return
    raise AssertionError

def test_employee_minimum_is_live():
    df=sample(); _,m11=run(df,CFG,['QUERÉTARO','NUEVO LEÓN','TAMAULIPAS'],'11',employee_minimum=11); _,m50=run(df,CFG,['QUERÉTARO','NUEVO LEÓN','TAMAULIPAS'],'50',employee_minimum=50); _,m300=run(df,CFG,['QUERÉTARO','NUEVO LEÓN','TAMAULIPAS'],'300',employee_minimum=300)
    assert m11['eligible']>=m50['eligible']>=m300['eligible']

def test_classification_80_60():
    assert CFG['priority']['bands']==[{'code':'AAA','min':80,'max':100},{'code':'AA','min':60,'max':79.99},{'code':'VALIDAR','min':0,'max':59.99}]

def test_score_weights(): assert CFG['score']['weights']=={'sector':35,'size':25,'geography':10,'need':30}

def test_potential_separate():
    r,m=run(sample(),CFG,['QUERÉTARO'],'P'); assert m['valor_potencial']==m['aaa']*69600; assert 'Score_V3' in r.columns

if __name__=='__main__':
    for f in [test_catalog_32,test_multiselect,test_need_zero,test_unknown_size_errors,test_employee_minimum_is_live,test_classification_80_60,test_score_weights,test_potential_separate]: f()
    print('CONCEDE V3 tests: PASS')
