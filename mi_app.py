import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Monitor Dólar vs. Plazo Fijo en Argentina",
    page_icon="💵",
    layout="wide"
)

# --- Estilos CSS para mejorar la apariencia ---
st.markdown("""
<style>
    .stSpinner > div > div {
        border-top-color: #28a745;
    }
</style>""", unsafe_allow_html=True)

st.title("💵 Monitor y Comparador: Dólar vs. Plazo Fijo")
st.markdown("Herramienta para analizar cotizaciones históricas y comparar el rendimiento del dólar contra un plazo fijo.")

# --- Funciones de Carga y Procesamiento de Datos ---
@st.cache_data(ttl=3600)  # Cachear los datos por 1 hora
def cargar_datos():
    """Carga, combina y procesa los datos del dólar y plazo fijo desde las APIs."""
    try:
        # Cargar datos del Dólar
        url_dolar = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
        response_dolar = requests.get(url_dolar)
        response_dolar.raise_for_status()
        data_dolar = response_dolar.json()
        df_dolar = pd.DataFrame(data_dolar)
        df_dolar['fecha'] = pd.to_datetime(df_dolar['fecha'])
        df_dolar = df_dolar.pivot_table(index='fecha', columns='casa', values='venta')
        df_dolar.columns = [str(col).capitalize() for col in df_dolar.columns]

        # Cargar datos del Plazo Fijo
        url_pf = 'https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo'
        response_pf = requests.get(url_pf)
        response_pf.raise_for_status()
        data_pf = response_pf.json()
        df_pf = pd.DataFrame(data_pf, columns=['fecha', 'valor'])
        df_pf['fecha'] = pd.to_datetime(df_pf['fecha'])
        df_pf = df_pf.set_index('fecha').rename(columns={'valor': 'TNA Plazo Fijo'})

        # Combinar y limpiar
        df_completo = df_dolar.join(df_pf, how='left')
        df_completo['TNA Plazo Fijo'] = pd.to_numeric(df_completo['TNA Plazo Fijo'], errors='coerce').ffill()
        df_completo.dropna(subset=df_dolar.columns, inplace=True)
        
        return df_completo
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con la API: {e}. Por favor, intenta recargar la página más tarde.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al procesar los datos: {e}")
        return None

# --- Cuerpo Principal de la Aplicación ---
with st.spinner('Cargando y procesando datos históricos...'):
    df_completo = cargar_datos()

if df_completo is not None and not df_completo.empty:
    
    st.header("🔬 Comparativa Histórica: Dólar vs. Plazo Fijo")

    # --- Controles de Usuario ---
    st.subheader("1. Configuración del Análisis")
    col1, col2 = st.columns(2)
    with col1:
        opciones_dolar = [d for d in ['Blue', 'Mep', 'Ccl'] if d in df_completo.columns]
        dolar_a_comparar = st.selectbox("Selecciona el tipo de dólar:", options=opciones_dolar, help="Elige la cotización del dólar que quieres usar para la comparación.")
    with col2:
        periodo_dias = st.number_input("Período de inversión (días):", min_value=1, max_value=365, value=30, help="Define cuántos días dura cada período de inversión a analizar.")
    
    st.subheader("2. Filtro de Fechas")
    col_f1, col_f2 = st.columns(2)
    
    hoy = date.today()
    fecha_minima_disponible = df_completo.index.min().date()
    valor_defecto_inicio = hoy - timedelta(days=90) # Default a 3 meses atrás
    
    with col_f1:
        fecha_inicio = st.date_input("Mostrar períodos que terminaron DESDE:", value=max(valor_defecto_inicio, fecha_minima_disponible), min_value=fecha_minima_disponible, max_value=hoy)
    with col_f2:
        fecha_fin = st.date_input("Mostrar períodos que terminaron HASTA:", value=hoy, min_value=fecha_minima_disponible, max_value=hoy)
    
    # --- Lógica de Cálculo y Visualización ---
    if dolar_a_comparar and periodo_dias and fecha_inicio <= fecha_fin:
        
        df_daily = df_completo.resample('D').ffill()
        df_daily[f'{dolar_a_comparar} Inicial'] = df_daily[dolar_a_comparar].shift(periodo_dias)
        
        df_calculo = df_daily.loc[df_completo.index].copy().sort_index(ascending=False)
        df_calculo.dropna(subset=[f'{dolar_a_comparar} Inicial', 'TNA Plazo Fijo'], inplace=True)
        
        df_calculo['Fecha Inicial'] = df_calculo.index - pd.to_timedelta(periodo_dias, unit='d')
        df_calculo = df_calculo.rename(columns={dolar_a_comparar: f'{dolar_a_comparar} Final'})
        
        df_calculo['Variación Dólar %'] = ((df_calculo[f'{dolar_a_comparar} Final'] / df_calculo[f'{dolar_a_comparar} Inicial']) - 1) * 100
        df_calculo['Rendimiento PF %'] = (df_calculo['TNA Plazo Fijo'] / 365) * periodo_dias
        
        df_calculo['Conclusión'] = df_calculo.apply(lambda row: "🟢 Dólar" if row['Variación Dólar %'] > row['Rendimiento PF %'] else "🔵 Plazo Fijo", axis=1)
        
        df_display = df_calculo.reset_index().rename(columns={'fecha': 'Fecha Final'})
        
        df_filtrado = df_display[
            (df_display['Fecha Final'].dt.date >= fecha_inicio) & 
            (df_display['Fecha Final'].dt.date <= fecha_fin)
        ]
        
        st.subheader("3. Resultados de la Comparación")

        if not df_filtrado.empty:
            columnas_ordenadas = [
                'Fecha Inicial', 'Fecha Final', 
                f'{dolar_a_comparar} Inicial', f'{dolar_a_comparar} Final', 'Variación Dólar %',
                'Rendimiento PF %', 'Conclusión'
            ]
            
            st.dataframe(df_filtrado[columnas_ordenadas].style.format({
                f'{dolar_a_comparar} Inicial': '${:,.2f}',
                f'{dolar_a_comparar} Final': '${:,.2f}',
                'Variación Dólar %': '{:,.2f}%',
                'Rendimiento PF %': '{:,.2f}%',
                'Fecha Inicial': '{:%Y-%m-%d}',
                'Fecha Final': '{:%Y-%m-%d}'
            }), use_container_width=True)
        else:
            st.warning("No hay períodos de inversión completos que hayan finalizado en el rango de fechas seleccionado. Por favor, elige un rango más amplio o diferente.")

    # --- Sección de Gráficos y Datos Adicionales ---
    with st.expander("Ver Gráficos y Datos Históricos Adicionales"):
        
        st.header("📈 Gráfico de Cotizaciones Históricas")
        opciones_disponibles = df_completo.columns.drop('TNA Plazo Fijo').tolist()
        opciones_preferidas = ['Oficial', 'Blue', 'Mep', 'Ccl']
        opciones_por_defecto_hist = [opt for opt in opciones_preferidas if opt in opciones_disponibles]
        
        cotizaciones_seleccionadas = st.multiselect(
            'Selecciona cotizaciones a visualizar:', 
            options=opciones_disponibles, 
            default=opciones_por_defecto_hist, 
            key='multiselect_cotizaciones'
        )
        if cotizaciones_seleccionadas:
            st.line_chart(df_completo[cotizaciones_seleccionadas])
        
        st.header("📊 Spread vs. Dólar Oficial (%)")
        st.line_chart((df_completo[opciones_por_defecto_hist].drop('Oficial', axis=1)).divide(df_completo['Oficial'], axis=0) * 100 - 100)

        st.header("📋 Tabla de Datos Recientes")
        st.dataframe(df_completo.sort_index(ascending=False).head(20).round(2))

else:
    st.error("Fallo en la carga de datos inicial. La aplicación no puede continuar.")
