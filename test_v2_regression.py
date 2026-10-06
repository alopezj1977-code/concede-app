import pandas as pd
from pathlib import Path
import sys
ROOT=Path(__file__).parents[1]; sys.path.insert(0,str(ROOT))
from compat.v2_compat import run_v2_compat
DATA=Path('/mnt/data/denue_inegi_11_.csv')

def test_v2_baseline():
    df=pd.read_csv(DATA,encoding='latin1',low_memory=False)
    m=run_v2_compat(df)
    assert m=={'raw':296441,'eligible':18410,'aaa':1711,'pipeline':119085600},m
    print('V2 REGRESSION PASS:',m)
if __name__=='__main__': test_v2_baseline()
