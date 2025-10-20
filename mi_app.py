import streamlit as st
import pandas as pd
import requests

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Análisis Dólar vs. Plazo Fijo en Argentina",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Monitor del Dólar y Plazo Fijo en Argentina")
st.markdown("Visualización de cotizaciones históricas, spread y comparativa de rendimiento con plazos fijos.")

# --- Funciones de Carga y Procesamiento de Datos ---

@st.cache_data
def cargar_datos_dolar():
    """Función para obtener y procesar las cotizaciones de dólares."""
    url = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df_pivote = df.pivot_table(index='fecha', columns='casa', values='venta')
        df_pivote.columns = [str(col).capitalize() for col in df_pivote.columns]
        df_pivote = df_pivote.dropna(subset=['Oficial'])
        return df_pivote
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API de dólares: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos del dólar: {e}")
        return None

@st.cache_data
def cargar_datos_plazo_fijo():
    """Función para obtener las tasas de plazo fijo."""
    url = 'https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.set_index('fecha')
        # Renombramos la columna para mayor claridad
        df = df.rename(columns={'valor': 'TNA Plazo Fijo'})
        # Convertimos la TNA a valor porcentual
        df['TNA Plazo Fijo'] = df['TNA Plazo Fijo']
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API de tasas de plazo fijo: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos de plazo fijo: {e}")
        return None

# --- Carga de Datos ---
with st.spinner('Cargando datos históricos desde las APIs...'):
    datos_dolar = cargar_datos_dolar()
    datos_pf = cargar_datos_plazo_fijo()

# Verificamos si ambos DataFrames se cargaron correctamente
if datos_dolar is not None and not datos_dolar.empty and datos_pf is not None and not datos_pf.empty:
    st.success("¡Datos del dólar y plazo fijo cargados correctamente!")

    # Combinamos ambos DataFrames
    # Usamos un join 'outer' y luego rellenamos hacia adelante para tener tasas en fines de semana
    df_completo = datos_dolar.join(datos_pf, how='outer').sort_index()
    df_completo['TNA Plazo Fijo'] = df_completo['TNA Plazo Fijo'].ffill()
    df_completo = df_completo.dropna(subset=datos_dolar.columns) # Eliminamos filas donde no hay datos de dolar

    # --- Gráfico de Cotizaciones Históricas ---
    st.header("📈 Gráfico de Cotizaciones Históricas (Valor de Venta)")
    opciones_disponibles = datos_dolar.columns.tolist()
    opciones_preferidas = ['Oficial', 'Blue', 'Mep', 'Ccl']
    opciones_por_defecto_hist = [opt for opt in opciones_preferidas if opt in opciones_disponibles]
    cotizaciones_seleccionadas = st.multiselect(
        'Selecciona las cotizaciones a visualizar:',
        options=opciones_disponibles,
        default=opciones_por_defecto_hist
    )
    if cotizaciones_seleccionadas:
        st.line_chart(datos_dolar[cotizaciones_seleccionadas])
    else:
        st.warning("Selecciona al menos una cotización.")

    # --- Gráfico del Spread ---
    st.header("📊 Spread vs. Dólar Oficial (%)")
    st.markdown("Diferencia porcentual entre cada cotización y el dólar oficial.")
    dolares_para_spread = [col for col in opciones_disponibles if col != 'Oficial']
    spreads_preferidos = ['Blue', 'Mep', 'Ccl']
    opciones_por_defecto_spread = [opt for opt in spreads_preferidos if opt in dolares_para_spread]
    spreads_seleccionados = st.multiselect(
        'Selecciona cotizaciones para ver su spread con el Oficial:',
        options=dolares_para_spread,
        default=opciones_por_defecto_spread
    )
    if spreads_seleccionados:
        df_spread = pd.DataFrame(index=datos_dolar.index)
        for dolar in spreads_seleccionados:
            df_spread[f'Brecha {dolar}'] = (datos_dolar[dolar] / datos_dolar['Oficial'] - 1) * 100
        st.line_chart(df_spread)
    else:
        st.warning("Selecciona al menos una cotización para ver el spread.")

    # --- SECCIÓN NUEVA: Comparativa Dólar vs. Plazo Fijo ---
    st.header("🔬 Comparativa: Dólar vs. Plazo Fijo")
    st.markdown("Análisis histórico para determinar qué inversión fue más rentable en un período determinado.")

    col1, col2 = st.columns(2)
    with col1:
        # Dejamos solo las opciones que nos interesan para la comparación
        opciones_dolar_comparativa = [d for d in ['Blue', 'Mep', 'Ccl'] if d in df_completo.columns]
        dolar_a_comparar = st.selectbox(
            "Selecciona el tipo de dólar a comparar:",
            options=opciones_dolar_comparativa
        )

    with col2:
        periodo_dias = st.number_input(
            "Selecciona el período de análisis (días):",
            min_value=1,
            max_value=365,
            value=30
        )

    if dolar_a_comparar and periodo_dias:
        df_comparativa = df_completo[[dolar_a_comparar, 'TNA Plazo Fijo']].copy().dropna()
        df_comparativa = df_comparativa.sort_index(ascending=False)

        # Cálculos
        df_comparativa[f'{dolar_a_comparar} Final'] = df_comparativa[dolar_a_comparar]
        # Usamos shift para obtener el valor de 'hace N dias'
        df_comparativa[f'{dolar_a_comparar} Inicial'] = df_comparativa[dolar_a_comparar].shift(-periodo_dias)
        
        # Obtenemos la fecha inicial correspondiente
        df_comparativa['Fecha Inicial'] = df_comparativa.index.to_series().shift(-periodo_dias)
        df_comparativa['Fecha Final'] = df_comparativa.index

        # Cálculo de la variación del dólar
        df_comparativa['Variación Dólar %'] = (
            (df_comparativa[f'{dolar_a_comparar} Final'] / df_comparativa[f'{dolar_a_comparar} Inicial']) - 1
        ) * 100

        # Rendimiento del plazo fijo para el período seleccionado
        # TNA / 365 * período_dias
        df_comparativa['Rendimiento PF %'] = (df_comparativa['TNA Plazo Fijo'] / 365) * periodo_dias
        
        # Limpiamos filas sin datos para el período completo
        df_comparativa = df_comparativa.dropna(
            subset=[f'{dolar_a_comparar} Inicial', 'Fecha Inicial']
        )

        # Aplicamos la lógica de comparación
        def determinar_ganador(row):
            variacion_dolar = row['Variación Dólar %']
            rendimiento_pf = row['Rendimiento PF %']
            # Tu lógica: si el dólar sube más de un 1%, ya es mejor
            if variacion_dolar > 1.0 and variacion_dolar > rendimiento_pf:
                return "🟢 Dólar"
            elif rendimiento_pf > variacion_dolar:
                return "🔵 Plazo Fijo"
            else:
                return "⚪ Empate / Dólar < 1%"

        df_comparativa['Conclusión'] = df_comparativa.apply(determinar_ganador, axis=1)

        # Seleccionamos y renombramos las columnas para mostrar
        columnas_a_mostrar = [
            'Fecha Inicial', 'Fecha Final',
            f'{dolar_a_comparar} Inicial', f'{dolar_a_comparar} Final',
            'Variación Dólar %', 'TNA Plazo Fijo', 'Rendimiento PF %', 'Conclusión'
        ]

        df_display = df_comparativa[columnas_a_mostrar].copy()
        df_display['TNA Plazo Fijo'] = df_display['TNA Plazo Fijo'].map('{:,.2f}%'.format)
        df_display['Rendimiento PF %'] = df_display['Rendimiento PF %'].map('{:,.2f}%'.format)
        df_display['Variación Dólar %'] = df_display['Variación Dólar %'].map('{:,.2f}%'.format)

        st.dataframe(df_display.head(20)) # Mostramos los 20 períodos más recientes

    # --- Mostrar Datos Crudos en una Tabla ---
    st.header("📋 Tabla de Datos Históricos")
    if st.checkbox('Mostrar la tabla con los últimos 10 datos'):
        st.dataframe(df_completo.sort_index(ascending=False).head(10).round(2))

else:
    st.error("No se pudieron cargar todos los datos. Intenta refrescar la página más tarde.")```
