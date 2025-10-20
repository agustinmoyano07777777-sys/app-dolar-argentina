import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Comparador de Dólares en Argentina",
    page_icon="💵",
    layout="wide"
)

# --- Auto-Refresco de la Página ---
refresh_interval_seconds = 1200  # 20 minutos
st.markdown(
    f"<script>setTimeout(function(){{window.location.reload();}}, {refresh_interval_seconds * 1000});</script>",
    unsafe_allow_html=True,
)

# --- Título y Descripción ---
st.title("💵 Comparador Interactivo de Dólares en Argentina")
st.markdown("Visualiza y compara las cotizaciones históricas, la brecha cambiaria y las variaciones diarias del dólar. **La página se actualiza cada 20 minutos.**"by Agus.M)

# --- Carga y Procesamiento de Datos ---
@st.cache_data(ttl=refresh_interval_seconds)
def cargar_y_procesar_datos():
    """Carga y procesa los datos de la API en un DataFrame de Pandas."""
    url = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        df['fecha'] = pd.to_datetime(df['fecha'])
        df_pivote = df.pivot_table(index='fecha', columns='casa', values='venta')
        df_pivote.columns = [str(col).capitalize() for col in df_pivote.columns]
        
        if 'Oficial' not in df_pivote.columns:
            return None
            
        return df_pivote.sort_index()

    except Exception as e:
        st.error(f"Error al cargar o procesar los datos: {e}")
        return None

# --- Cuerpo Principal de la Aplicación ---
with st.spinner('Cargando datos históricos desde la API...'):
    datos_dolar = cargar_y_procesar_datos()

if datos_dolar is not None and not datos_dolar.empty:
    st.success(f"¡Datos cargados y procesados! Próxima actualización en 20 minutos.")

    opciones_disponibles = datos_dolar.columns.tolist()
    opciones_default = [opt for opt in ['Oficial', 'Blue', 'Mep', 'Ccl'] if opt in opciones_disponibles]

    # --- SECCIÓN 1: Cotizaciones Históricas ---
    st.header("📈 Cotizaciones Históricas del Dólar")
    cotizaciones_seleccionadas_hist = st.multiselect('Selecciona cotizaciones a visualizar:', options=opciones_disponibles, default=opciones_default)
    if cotizaciones_seleccionadas_hist:
        st.line_chart(datos_dolar[cotizaciones_seleccionadas_hist])

    # --- SECCIÓN 2: Brecha Cambiaria ---
    st.header("📊 Brecha Cambiaria vs. Dólar Oficial (%)")
    dolares_para_brecha = [col for col in opciones_disponibles if col != 'Oficial']
    if dolares_para_brecha:
        df_brecha = (datos_dolar[dolares_para_brecha].div(datos_dolar['Oficial'], axis=0) - 1) * 100
        opciones_brecha_default = [opt for opt in ['Blue', 'Mep', 'Ccl'] if opt in df_brecha.columns]
        brecha_seleccionada = st.multiselect("Selecciona las brechas a visualizar:", options=dolares_para_brecha, default=opciones_brecha_default)
        if brecha_seleccionada:
            st.line_chart(df_brecha[brecha_seleccionada])

    # --- SECCIÓN 3: Variación Diaria Porcentual con Selector de Fecha ---
    st.header("📉 Variación Diaria Porcentual (%)")
    st.markdown("Usa los filtros para explorar la volatilidad en un período específico de todo el historial.")
    
    df_variaciones = datos_dolar.pct_change() * 100
    df_variaciones_continuas = df_variaciones.resample('D').asfreq().fillna(0)
    
    variaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones para el análisis de volatilidad:',
        options=opciones_disponibles, default=opciones_default, key='variaciones_multiselect'
    )
    
    fecha_minima = df_variaciones_continuas.index.min().date()
    fecha_maxima = df_variaciones_continuas.index.max().date()
    fecha_default_inicio = max(fecha_minima, fecha_maxima - timedelta(days=365))
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde:", value=fecha_default_inicio, min_value=fecha_minima, max_value=fecha_maxima, key='var_start_date')
    with col2:
        fecha_fin = st.date_input("Hasta:", value=fecha_maxima, min_value=fecha_minima, max_value=fecha_maxima, key='var_end_date')

    # --- BLOQUE CORREGIDO ---
    # Se verifica si hay selecciones y si el rango de fechas es válido.
    if variaciones_seleccionadas and fecha_inicio <= fecha_fin:
        df_filtrado = df_variaciones_continuas[variaciones_seleccionadas][fecha_inicio:fecha_fin]
        st.bar_chart(df_filtrado)
    else:
        # Este es el bloque que faltaba. Provee un feedback útil al usuario.
        st.warning("Por favor, selecciona al menos una cotización y asegúrate de que el rango de fechas sea válido.")

    # --- SECCIÓN 4: Tabla de Datos ---
    with st.expander("Ver Tabla con los Últimos Datos"):
        df_tabla = datos_dolar.sort_index(ascending=False).head(20).round(2)
        df_tabla.index = df_tabla.index.strftime('%Y-%m-%d')
        st.dataframe(df_tabla, use_container_width=True)

else:
    st.error("No se pudieron cargar los datos necesarios. Intenta refrescar la página en unos minutos.")
