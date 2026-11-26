"""Consulta agregada y paginada de accidentes ofídicos del INS."""
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = Path(__file__).parent
API = 'https://www.datos.gov.co/resource/wns8-p38i.json'
WHERE = "cod_eve = '100' AND ano in ('2022','2023','2024')"
GROUP = 'ano,cod_dpto_o,cod_mun_o,departamento_ocurrencia,municipio_ocurrencia'

def session():
    s = requests.Session()
    s.mount('https://', HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429,500,502,503,504])))
    return s

def normalize(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError('La fuente no devolvió registros.')
    for col, width in [('cod_dpto_o',2),('cod_mun_o',5)]:
        df[col] = df[col].fillna('').astype(str).str.zfill(width)
    for col in ['ano','casos']:
        df[col] = pd.to_numeric(df[col], errors='raise').astype(int)
    if (df.casos < 0).any() or set(df.ano) != {2022,2023,2024}:
        raise ValueError('Cobertura o conteos inesperados en la fuente.')
    for col in ['departamento_ocurrencia','municipio_ocurrencia']:
        df[col] = df[col].fillna('SIN INFORMACIÓN')
    return df

def fetch_data():
    rows, offset, batch = [], 0, 1000
    with session() as s:
        while True:
            r = s.get(API, params={'$select':GROUP+',sum(conteo) as casos', '$where':WHERE,
                '$group':GROUP, '$order':GROUP, '$limit':batch, '$offset':offset}, timeout=45)
            r.raise_for_status()
            page = r.json()
            if not isinstance(page,list):
                raise ValueError('Respuesta inesperada de datos.gov.co')
            rows.extend(page)
            if len(page) < batch:
                break
            offset += batch
        df = normalize(rows)
        r = s.get(API, params={'$select':'ano,sum(conteo) as casos','$where':WHERE,'$group':'ano'}, timeout=45)
        r.raise_for_status()
        expected = {int(x['ano']):int(x['casos']) for x in r.json()}
        if df.groupby('ano').casos.sum().to_dict() != expected:
            raise ValueError('La descarga no coincide con los totales de la fuente. Reintenta.')
    return df, datetime.now(timezone.utc).isoformat()

def save_snapshot():
    df, stamp = fetch_data()
    df.to_csv(BASE/'data/casos.csv',index=False)
    (BASE/'data/snapshot.json').write_text(json.dumps({'consultado_utc':stamp,'fuente':API,
        'filtro':WHERE,'totales':df.groupby('ano').casos.sum().to_dict()},indent=2),encoding='utf-8')
    print(df.groupby('ano').casos.sum().to_dict())

if __name__ == '__main__':
    save_snapshot()
