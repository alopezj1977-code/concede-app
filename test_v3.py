import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from core import load_config, run, ConfigError

ROOT = Path(__file__).parent
CFG = load_config(ROOT / 'concede_v3.json')

def sample():
    return pd.DataFrame({
        'id':[1,2,3,4],
        'nom_estab':['A','B','C','D'],
        'raz_social':['A SA','B SA','C SA','D SA'],
        'nombre_act':['Almacenamiento y logística','Comercio al por mayor de alimentos','Restaurante','Servicios de oficina'],
        'per_ocu':['51 a 100 personas','11 a 30 personas','51 a 100 personas','6 a 10 personas'],
        'entidad':['Veracruz de Ignacio de la Llave','Nuevo León','Tamaulipas','Querétaro'],
        'cve_ent':['30','19','28','22'],
        'municipio':['Xalapa','Monterrey','Reynosa','Querétaro']
    })

def test_catalog_32(): assert len(CFG['geography']['entities']) == 32

def test_veracruz_name_and_code_match():
    r,m = run(sample(), CFG, ['VERACRUZ'], 'VER')
    assert m['target_geography'] == 1, m
    assert m['commercial_candidates'] == 1, m
    assert r.loc[0,'Entidad_CANONICA'] == 'VERACRUZ'

def test_veracruz_code_is_authoritative():
    df = sample(); df.loc[0,'entidad'] = 'NOMBRE DISTINTO'
    r,m = run(df, CFG, ['VERACRUZ'], 'VERCODE')
    assert m['target_geography'] == 1, m
    assert r.loc[0,'Entidad_CANONICA'] == 'VERACRUZ'

def test_multiselect():
    r,m = run(sample(), CFG, ['VERACRUZ','NUEVO LEÓN'], 'M')
    assert m['target_geography'] == 2
    assert m['commercial_candidates'] == 2

def test_need_zero():
    r,_ = run(sample(), CFG, ['VERACRUZ'], 'N')
    assert (r['Score_Necesidad'] == 0).all()

def test_unknown_size_errors():
    df=sample(); df.loc[0,'per_ocu']='ESTRATO DESCONOCIDO'
    try: run(df,CFG,['VERACRUZ'],'E')
    except ConfigError: return
    raise AssertionError('Expected ConfigError')

def test_employee_minimum_is_live():
    _,m11=run(sample(),CFG,['VERACRUZ','NUEVO LEÓN','TAMAULIPAS'],'11',employee_minimum=11)
    _,m50=run(sample(),CFG,['VERACRUZ','NUEVO LEÓN','TAMAULIPAS'],'50',employee_minimum=50)
    assert m11['eligible'] >= m50['eligible']

def test_classification_and_weights():
    assert CFG['priority']['bands'] == [
        {'code':'AAA','min':80,'max':100},
        {'code':'AA','min':60,'max':79.99},
        {'code':'VALIDAR','min':0,'max':59.99}
    ]
    assert CFG['score']['weights'] == {'sector':35,'size':25,'geography':10,'need':30}

def test_potential_separate():
    _,m=run(sample(),CFG,['VERACRUZ'],'P')
    assert m['valor_potencial'] == m['aaa'] * 69600

TESTS=[
    test_catalog_32,test_veracruz_name_and_code_match,test_veracruz_code_is_authoritative,
    test_multiselect,test_need_zero,test_unknown_size_errors,test_employee_minimum_is_live,
    test_classification_and_weights,test_potential_separate
]

if __name__ == '__main__':
    for t in TESTS:
        t(); print('PASS', t.__name__)
    print(f'CONCEDE V3 TESTS EXECUTED: {len(TESTS)}/{len(TESTS)} PASS')
