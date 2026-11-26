from pathlib import Path
import copy
import json
import pandas as pd
import folium
from branca.colormap import LinearColormap
import streamlit as st
from datos import fetch_data, normalize

ROOT = Path(__file__).parent
st.set_page_config(page_title='Accidentes ofídicos | Quimbi Adventours',page_icon='🌿',layout='wide')

@st.cache_data(ttl=86400, show_spinner=False)
def live_data():
    return fetch_data()

@st.cache_data
def geography(level):
    return json.loads((ROOT/f'data/{level}.geojson').read_text(encoding='utf-8'))

st.caption('QUIMBI ADVENTOURS · DATOS DE INTERÉS')
st.title('Accidentes ofídicos en Colombia')
st.markdown('Explora los casos notificados en **2022, 2023 y 2024**. Selecciona un territorio para conocer sus cifras y comparar los tres años.')
with st.spinner('Consultando los datos del INS…'):
    try:
        df, stamp = live_data()
        offline = False
    except Exception:
        df = normalize(pd.read_csv(ROOT/'data/casos.csv',dtype=str).to_dict('records'))
        stamp = json.loads((ROOT/'data/snapshot.json').read_text())['consultado_utc']
        offline = True
if offline:
    st.warning('La fuente no está disponible en este momento. Se muestra la copia de respaldo con la fecha de consulta indicada abajo.')

deps = geography('departamentos')
muns = geography('municipios')
dep_names = {f['properties']['divipola_dep']:f['properties']['dpto_nombre'].title() for f in deps['features']}
# Preserve notification codes absent from current cartography.
for row in df.itertuples():
    dep_names.setdefault(row.cod_dpto_o, str(row.departamento_ocurrencia).title())
c1,c2,c3 = st.columns([1,2,2])
years = sorted(c1.multiselect('Años',[2022,2023,2024],default=[2022,2023,2024],placeholder='Selecciona uno o varios años'))
dep = c2.selectbox('Departamento',['Todos']+sorted(dep_names,key=dep_names.get),format_func=lambda x:'Toda Colombia' if x=='Todos' else dep_names[x])
municipalities = {f['properties']['divipola_mun']:f['properties']['mpio_nombre'].title() for f in muns['features'] if f['properties']['divipola_dep']==dep}
for row in df[df.cod_dpto_o==dep].itertuples():
    municipalities.setdefault(row.cod_mun_o,str(row.municipio_ocurrencia).title())
mun = c3.selectbox('Municipio',['Todos']+sorted(municipalities,key=municipalities.get),format_func=lambda x:'Todos los municipios' if x=='Todos' else municipalities[x],disabled=dep=='Todos',key=f'municipio_{dep}')
territory = df if dep=='Todos' else df[df.cod_dpto_o==dep]
if mun!='Todos':
    territory = territory[territory.cod_mun_o==mun]
if not years:
    st.info('Selecciona al menos un año para ver el mapa y los datos.')
    st.stop()
filtered = territory[territory.ano.isin(years)]
period = ', '.join(map(str,years))
period_file = '_'.join(map(str,years))
title = 'Colombia' if dep=='Todos' else dep_names[dep]
if mun!='Todos':
    title += ' · '+municipalities[mun]
st.subheader(f'{title} · {period}')
st.metric('Total de casos · período seleccionado',f'{int(filtered.casos.sum()):,}'.replace(',','.') if len(filtered) else 'Sin registros')
metrics = st.columns(len(years))
for container,y in zip(metrics,years):
    subset = territory[territory.ano==y]
    container.metric(f'Casos notificados · {y}',f'{int(subset.casos.sum()):,}'.replace(',','.') if len(subset) else 'Sin registros')
st.caption('El mapa suma los casos de los años seleccionados. Las tarjetas y la gráfica muestran el detalle anual del mismo territorio.')

is_national = dep=='Todos'
geo = copy.deepcopy(deps if is_national else muns)
code_field = 'divipola_dep' if is_national else 'divipola_mun'
name_field = 'dpto_nombre' if is_national else 'mpio_nombre'
data_field = 'cod_dpto_o' if is_national else 'cod_mun_o'
if not is_national:
    geo['features'] = [f for f in geo['features'] if f['properties']['divipola_dep']==dep and (mun=='Todos' or f['properties']['divipola_mun']==mun)]
counts = filtered.groupby(data_field).casos.sum().to_dict()
scale = LinearColormap(['#d5eee3','#65b99b','#19836f','#084b43'],vmin=0,vmax=max(max(counts.values(),default=1),1),caption=f'Casos acumulados · {period}')
for f in geo['features']:
    p = f['properties']
    p['casos'] = counts.get(p[code_field])
    p['detalle'] = f"{p['casos']:,}".replace(',','.') if p['casos'] is not None else 'Sin registros en la fuente'
    p['nombre'] = p[name_field].title()
map_col,detail_col = st.columns([2.2,1])
with map_col:
    if geo['features']:
        m = folium.Map(location=[4.5,-73.5],zoom_start=5,tiles='OpenStreetMap',control_scale=True)
        layer = folium.GeoJson(geo,name='Casos notificados',style_function=lambda f:{'fillColor':'#dce2e1' if f['properties']['casos'] is None else scale(f['properties']['casos']), 'color':'#ffffff','weight':1,'fillOpacity':0.83},highlight_function=lambda f:{'weight':3,'color':'#173b35'},tooltip=folium.GeoJsonTooltip(fields=['nombre','detalle'],aliases=['Territorio','Casos'],sticky=False),popup=folium.GeoJsonPopup(fields=['nombre','detalle'],aliases=['Territorio','Casos'])).add_to(m)
        m.fit_bounds(layer.get_bounds(),padding=[15,15])
        scale.add_to(m)
        st.iframe(m.get_root().render(),height=530)
        st.caption('Gris: sin registros. Pasa el cursor o toca un territorio para ver sus datos. Usa los filtros superiores para cambiar el detalle.')
    else:
        st.info('Este código de notificación no tiene geometría disponible. Sus datos se conservan en las tarjetas y la tabla.')
    mapped = {f['properties'][code_field] for f in geo['features']}
    unmatched = filtered[~filtered[data_field].isin(mapped)].casos.sum()
    if unmatched:
        st.warning(f'{int(unmatched)} casos del filtro no tienen correspondencia cartográfica; están incluidos en los totales.')
with detail_col:
    st.markdown('#### Comparación anual')
    annual = filtered.groupby('ano').casos.sum().reindex(years)
    annual.index = annual.index.astype(str)
    st.bar_chart(annual.rename('Casos'),color='#19836f',height=260)
    st.markdown('#### Cómo leer el mapa')
    st.write('El color representa el número de casos notificados por lugar de ocurrencia. Un color más intenso indica más casos.')
    st.write('Son conteos absolutos, no tasas de incidencia ni una medida del riesgo individual. La ausencia de registros no demuestra ausencia de accidentes o de serpientes.')

st.subheader('Datos del territorio')
st.caption(f'Años incluidos: {period}. La tabla conserva el detalle por año; el mapa muestra su suma.')
table = filtered[['departamento_ocurrencia','municipio_ocurrencia','ano','casos']].groupby(['departamento_ocurrencia','municipio_ocurrencia','ano'],as_index=False).casos.sum().rename(columns={'departamento_ocurrencia':'Departamento','municipio_ocurrencia':'Municipio','ano':'Año','casos':'Casos'}).sort_values('Casos',ascending=False)
if table.empty:
    st.info('No hay registros para esta selección en la fuente consultada.')
else:
    st.dataframe(table,hide_index=True,width='stretch')
st.download_button('Descargar selección en CSV',table.to_csv(index=False).encode('utf-8-sig'),file_name=f'accidentes_ofidicos_{period_file}_{dep}_{mun}.csv',mime='text/csv')
with st.expander('Fuente y metodología'):
    st.markdown('**Fuente:** [INS · SIVIGILA, datos.gov.co](https://www.datos.gov.co/d/wns8-p38i). Se filtra el evento 100, ACCIDENTE OFÍDICO, y se suma el campo `conteo` para 2022–2024. La consulta se pagina y se contrasta con los totales anuales de la API.')
    st.write(f'Última consulta de los datos mostrados (UTC): {stamp}. Caché: 24 horas. Los registros de la fuente pueden actualizarse.')
    st.markdown('**Cartografía:** Marco Geoestadístico Nacional 2025, [DANE](https://www.dane.gov.co). Simplificación: [ytolosa/mapas-colombia](https://github.com/ytolosa/mapas-colombia), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Límites actuales usados como referencia para datos históricos; no representan necesariamente la división territorial de cada año. Las uniones usan códigos DIVIPOLA, no coincidencias de nombres.')
    st.write('Este visor es informativo y no sustituye una valoración médica. No identifica especies ni determina si un lugar es seguro.')
