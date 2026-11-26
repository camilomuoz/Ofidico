# Visor de accidentes ofídicos · Quimbi Adventours

Aplicación Streamlit con mapa nacional y municipal, filtros 2022–2024, comparación anual y descarga CSV. Los datos se consultan en SIVIGILA y se contrastan contra totales independientes de la API. Solo se incluye el evento 100.

## Ejecutar

Desde esta carpeta, con Python 3.12 o superior:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publicar en Streamlit Community Cloud

1. Subir a un repositorio GitHub `app.py`, `datos.py`, `requirements.txt`, `.streamlit/config.toml` y la carpeta `data` completa.
2. Iniciar sesión en https://share.streamlit.io/ y crear una aplicación desde ese repositorio; archivo principal: `app.py`.
3. Seleccionar Python 3.12 o superior y acceso público para insertarla en el blog.
4. Copiar la URL real asignada por Streamlit. No hay una URL pública hasta completar el despliegue.

## Insertar en Odoo

En el editor del artículo del blog, insertar un bloque de código HTML/incrustación si está disponible en la versión de Odoo y pegar este fragmento. Reemplazar `TU-APP` por el subdominio real que devuelva Streamlit:

```html
<iframe
  src="https://TU-APP.streamlit.app/?embed=true"
  title="Accidentes ofídicos en Colombia: mapa y datos 2022–2024"
  width="100%"
  height="1100"
  style="border:0;border-radius:12px;"
  loading="lazy">
</iframe>
```

Mantener el desplazamiento dentro del marco para acceder a la tabla. Si Odoo restringe los iframes, usar un enlace a la aplicación o ajustar la configuración con el administrador. El dominio de Odoo no cambia: Streamlit aloja el visor.

Documentación de incrustación: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app/embed-your-app

## Datos y actualización

- Fuente: INS / SIVIGILA, https://www.datos.gov.co/d/wns8-p38i
- Filtro: `cod_eve='100'`, años 2022–2024. Se suma `conteo`; no se cuentan filas como casos.
- Consulta agregada paginada por año, departamento y municipio. Caché durante 24 horas.
- Si falla la API, se muestra `data/casos.csv` con advertencia y fecha de respaldo.
- Para renovar el respaldo: `python datos.py`. Esto verifica los totales antes de guardar.
- Los territorios sin coincidencia cartográfica permanecen en las tablas y totales y se informa su cantidad.
- Gris significa ausencia de registros en la consulta, no riesgo cero. Los valores son conteos notificados, no tasas poblacionales.

## Cartografía y licencia

Marco Geoestadístico Nacional 2025, DANE (https://www.dane.gov.co). Simplificación de https://github.com/ytolosa/mapas-colombia, bajo CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Se incluyen los GeoJSON de escala nacional, variante de coordenadas reales, sin modificar su geometría. Es cartografía simplificada de referencia y puede diferir de los límites de 2022–2024. No está avalada por el DANE. Fondo: OpenStreetMap y sus colaboradores; Folium conserva su atribución.

El mapa requiere conexión para cargar Leaflet y el fondo cartográfico. Las geometrías y el respaldo de casos se incluyen localmente.
