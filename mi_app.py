import streamlit as st
import pandas as pd
import requests

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Comparador de Dólares en Argentina",
    page_icon="💵",
    layout="wide"
)

# --- Título y Descripción ---
st.title("💵 Comparador Interactivo de Dólares en Argentina")
st.markdown("Visualiza y compara las cotizaciones históricas, la brecha cambiaria y las variaciones diarias del dólar.")

# --- Carga y Procesamiento de Datos ---
@st.cache_data(ttl=3600)  # Cachear los datos por 1 hora
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

    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al acceder a la API: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos: {e}")
        return None

# --- Cuerpo Principal de la Aplicación ---
with st.spinner('Cargando datos históricos desde la API...'):
    datos_dolar = cargar_y_procesar_datos()

if datos_dolar is not None and not datos_dolar.empty:
    st.success("¡Datos cargados y procesados correctamente!")

    opciones_disponibles = datos_dolar.columns.tolist()
    opciones_default = [opt for opt in ['Oficial', 'Blue', 'Mep', 'Ccl'] if opt in opciones_disponibles]

    # --- SECCIÓN 1: Gráfico de Cotizaciones Históricas ---
    st.header("📈 Cotizaciones Históricas del Dólar")
    cotizaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones que quieres visualizar:',
        options=opciones_disponibles, default=opciones_default
    )
    if cotizaciones_seleccionadas:
        st.line_chart(datos_dolar[cotizaciones_seleccionadas])
    else:
        st.warning("Selecciona al menos una cotización para mostrar el gráfico.")

    # --- SECCIÓN 2: Gráfico del Spread (Brecha Cambiaria) ---
    st.header("📊 Brecha Cambiaria vs. Dólar Oficial (%)")
    st.markdown("Muestra la diferencia porcentual entre cada cotización y el dólar oficial.")

    dolares_para_brecha = [col for col in opciones_disponibles if col != 'Oficial']
    if dolares_para_brecha:
        df_brecha = (datos_dolar[dolares_para_brecha].div(datos_dolar['Oficial'], axis=0) - 1) * 100
        opciones_brecha_default = [opt for opt in ['Blue', 'Mep', 'Ccl'] if opt in df_brecha.columns]
        brecha_seleccionada = st.multiselect(
            "Selecciona las brechas a visualizar:",
            options=dolares_para_brecha, default=opciones_brecha_default
        )
        if brecha_seleccionada:
            st.line_chart(df_brecha[brecha_seleccionada])

    # --- SECCIÓN 3: Gráfico de Variaciones Diarias (FORMATO DE FECHA CORREGIDO) ---
    st.header("📉 Variación Diaria Porcentual (%)")
    st.markdown("Muestra el cambio porcentual de cada cotización respecto al día anterior. Los fines de semana se muestran con 0% de variación.")
    
    df_variaciones = datos_dolar.pct_change() * 100
    
    variaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones para ver su variación diaria:',
        options=opciones_disponibles,
        default=opciones_default,
        key='variaciones_multiselect'
    )

    if variaciones_seleccionadas:
        df_variaciones_continuas = df_variaciones.resample('D').asfreq().fillna(0)
        df_grafico = df_variaciones_continuas[variaciones_seleccionadas].tail(90)
        
        # --- LÍNEA MODIFICADA ---
        # Cambiamos el formato de la fecha al formato DD/MM/AA
        df_grafico.index = df_grafico.index.strftime('%d/%m/%y')
        
        st.bar_chart(df_grafico)
    else:
        st.warning("Selecciona al menos una cotización para mostrar su variación.")

    # --- SECCIÓN 4: Tabla de Datos (Opcional) ---
    with st.expander("Ver Tabla con los Últimos Datos"):
        st.dataframe(datos_dolar.sort_index(ascending=False).head(20).round(2), use_container_width=True)

else:
    st.error("No se pudieron cargar los datos necesarios. Por favor, intenta refrescar la página en unos minutos.")
