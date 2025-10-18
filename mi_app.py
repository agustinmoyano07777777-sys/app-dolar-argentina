import streamlit as st
import pandas as pd
import requests

# Configuración de la página
st.set_page_config(
    page_title="Cotizaciones del Dólar en Argentina",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Monitor del Dólar en Argentina")
st.markdown("Visualización de las cotizaciones históricas y el spread respecto al dólar oficial.")

# --- Carga y Procesamiento de Datos ---
@st.cache_data
def cargar_datos():
    """
    Función para obtener y procesar los datos de la API.
    """
    url = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        
        # --- Limpieza y transformación de datos ---
        df['fecha'] = pd.to_datetime(df['fecha'])
        df_pivote = df.pivot_table(index='fecha', columns='casa', values='venta')
        df_pivote.columns = [str(col).capitalize() for col in df_pivote.columns]
        df_pivote = df_pivote.dropna(subset=['Oficial'])
        
        return df_pivote
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al procesar los datos: {e}")
        return None

# Cargar los datos y mostrar un mensaje de estado
with st.spinner('Cargando datos históricos desde la API...'):
    datos_dolar = cargar_datos()

if datos_dolar is not None and not datos_dolar.empty:
    st.success("¡Datos cargados correctamente!")

    # --- Gráfico de Cotizaciones Históricas ---
    st.header("📈 Gráfico de Cotizaciones Históricas (Valor de Venta)")

    opciones_disponibles = datos_dolar.columns.tolist()
    # ----> CÓDIGO CORREGIDO <----
    # Definimos las opciones que nos gustaría tener por defecto
    opciones_preferidas = ['Oficial', 'Blue', 'Mep', 'Ccl']
    # Creamos la lista de opciones por defecto, SOLO con las que de verdad existen
    opciones_por_defecto_hist = [opt for opt in opciones_preferidas if opt in opciones_disponibles]

    cotizaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones que quieres visualizar:',
        options=opciones_disponibles,
        default=opciones_por_defecto_hist  # Usamos la lista segura
    )

    if cotizaciones_seleccionadas:
        st.line_chart(datos_dolar[cotizaciones_seleccionadas])
    else:
        st.warning("Por favor, selecciona al menos una cotización para mostrar el gráfico.")

    # --- Cálculo y Gráfico del Spread ---
    st.header("📊 Spread vs. Dólar Oficial (%)")
    st.markdown("La 'brecha' muestra la diferencia porcentual entre cada cotización y el dólar oficial.")

    dolares_para_spread = [col for col in opciones_disponibles if col != 'Oficial']
    # ----> CÓDIGO CORREGIDO <----
    spreads_preferidos = ['Blue', 'Mep', 'Ccl']
    # Creamos la lista de opciones por defecto para el spread, SOLO con las que existen
    opciones_por_defecto_spread = [opt for opt in spreads_preferidos if opt in dolares_para_spread]

    spreads_seleccionados = st.multiselect(
        'Selecciona las cotizaciones para ver su spread con el Oficial:',
        options=dolares_para_spread,
        default=opciones_por_defecto_spread # Usamos la lista segura
    )

    if spreads_seleccionados:
        df_spread = pd.DataFrame(index=datos_dolar.index)
        for dolar in spreads_seleccionados:
            df_spread[f'Brecha {dolar}'] = (datos_dolar[dolar] / datos_dolar['Oficial'] - 1) * 100
        st.line_chart(df_spread)
    else:
        st.warning("Por favor, selecciona al menos una cotización para mostrar el gráfico de spread.")

    # --- Mostrar Datos en una Tabla ---
    st.header("📋 Tabla de Datos")
    if st.checkbox('Mostrar la tabla con los últimos 10 datos históricos'):
        st.dataframe(datos_dolar.sort_index(ascending=False).head(10))

else:
    st.error("No se pudieron cargar los datos. Por favor, intenta refrescar la página más tarde.")
