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
@st.cache_data(ttl=3600)  # Cachear los datos por 1 hora para no sobrecargar la API
def cargar_y_procesar_datos():
    """
    Carga los datos desde la API, los procesa y los prepara en un DataFrame de Pandas.
    Devuelve el DataFrame procesado o None si hay un error.
    """
    url = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
    try:
        # Hacemos la petición a la API
        response = requests.get(url)
        response.raise_for_status()  # Lanza un error si la petición falla (ej: 404, 500)
        
        # Convertimos la respuesta JSON a un DataFrame de Pandas
        data = response.json()
        df = pd.DataFrame(data)

        # --- Limpieza y Transformación de Datos ---
        # Convertimos la columna 'fecha' a un formato de fecha real
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Reorganizamos la tabla (pivot) para tener las fechas como índice y cada tipo de dólar como una columna
        # Esto es fundamental para trabajar con series de tiempo
        df_pivote = df.pivot_table(index='fecha', columns='casa', values='venta')
        
        # Limpiamos y estandarizamos los nombres de las columnas (ej: 'blue' -> 'Blue')
        df_pivote.columns = [str(col).capitalize() for col in df_pivote.columns]
        
        # Nos aseguramos de tener la columna 'Oficial' que es clave para los cálculos
        if 'Oficial' not in df_pivote.columns:
            st.error("No se encontró la columna 'Oficial' en los datos de la API.")
            return None
            
        return df_pivote.sort_index() # Ordenamos por fecha

    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al intentar acceder a la API: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al procesar los datos: {e}")
        return None

# --- Cuerpo Principal de la Aplicación ---
# Mostramos un mensaje mientras se cargan los datos
with st.spinner('Cargando datos históricos desde la API...'):
    datos_dolar = cargar_y_procesar_datos()

# Solo si los datos se cargaron correctamente, mostramos los análisis
if datos_dolar is not None and not datos_dolar.empty:
    
    st.success("¡Datos cargados y procesados correctamente!")

    # --- SECCIÓN 1: Gráfico de Cotizaciones Históricas ---
    st.header("📈 Cotizaciones Históricas del Dólar")
    
    # Damos al usuario la opción de elegir qué cotizaciones ver
    opciones_disponibles = datos_dolar.columns.tolist()
    opciones_default = [opt for opt in ['Oficial', 'Blue', 'Mep', 'Ccl'] if opt in opciones_disponibles]

    cotizaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones que quieres visualizar:',
        options=opciones_disponibles,
        default=opciones_default
    )

    if cotizaciones_seleccionadas:
        st.line_chart(datos_dolar[cotizaciones_seleccionadas])
    else:
        st.warning("Por favor, selecciona al menos una cotización para mostrar el gráfico.")

    # --- SECCIÓN 2: Cálculo y Gráfico del Spread (Brecha Cambiaria) ---
    st.header("📊 Brecha Cambiaria vs. Dólar Oficial (%)")
    st.markdown("La 'brecha' o 'spread' muestra la diferencia porcentual entre cada cotización y el dólar oficial. Permite ver qué tan 'caro' está un dólar respecto al otro.")

    # Calculamos la brecha para todos los dólares excepto el oficial
    dolares_para_brecha = [col for col in opciones_disponibles if col != 'Oficial']
    if dolares_para_brecha:
        # El cálculo es (valor_dolar / valor_oficial - 1) * 100
        df_brecha = (datos_dolar[dolares_para_brecha].div(datos_dolar['Oficial'], axis=0) - 1) * 100

        opciones_brecha_default = [opt for opt in ['Blue', 'Mep', 'Ccl'] if opt in df_brecha.columns]
        brecha_seleccionada = st.multiselect(
            "Selecciona las brechas a visualizar:",
            options=dolares_para_brecha,
            default=opciones_brecha_default
        )
        if brecha_seleccionada:
            st.line_chart(df_brecha[brecha_seleccionada])
        else:
            st.warning("Por favor, selecciona una cotización para calcular su brecha.")

    # --- SECCIÓN 3: Gráfico de Variaciones Diarias ---
    st.header("📉 Variación Diaria Porcentual (%)")
    st.markdown("Este gráfico muestra el cambio porcentual de cada cotización de un día para el otro. Es útil para detectar días de alta volatilidad.")
    
    # Calculamos la variación diaria con la función .pct_change()
    df_variaciones = datos_dolar.pct_change() * 100
    
    # Damos al usuario la opción de elegir qué variaciones ver
    variaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones para ver su variación diaria:',
        options=opciones_disponibles,
        default=opciones_default,
        key='variaciones_multiselect' # Una 'key' única para evitar conflictos de widgets
    )

    if variaciones_seleccionadas:
        # Mostramos los últimos 60 días para que el gráfico sea legible
        st.bar_chart(df_variaciones[variaciones_seleccionadas].tail(60))
    else:
        st.warning("Por favor, selecciona al menos una cotización para mostrar su variación.")

    # --- SECCIÓN 4: Tabla de Datos (Opcional) ---
    with st.expander("Ver Tabla con los Últimos Datos"):
        st.dataframe(datos_dolar.sort_index(ascending=False).head(20).round(2), use_container_width=True)

else:
    st.error("No se pudieron cargar los datos necesarios. Por favor, intenta refrescar la página en unos minutos.")
