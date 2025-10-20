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
        df = pd.DataFrame(data, columns=['fecha', 'valor'])
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.set_index('fecha')
        df = df.rename(columns={'valor': 'TNA Plazo Fijo'})
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

    df_completo = datos_dolar.join(datos_pf, how='outer').sort_index()
    df_completo['TNA Plazo Fijo'] = df_completo['TNA Plazo Fijo'].ffill()
    df_completo = df_completo.dropna(subset=datos_dolar.columns)

    # --- Gráfico de Cotizaciones Históricas ---
    st.header("📈 Gráfico de Cotizaciones Históricas (Valor de Venta)")
    opciones_disponibles = datos_dolar.columns.tolist()
    opciones_preferidas = ['Oficial', 'Blue', 'Mep', 'Ccl']
    opciones_por_defecto_hist = [opt for opt in opciones_preferidas if opt in opciones_disponibles]
    cotizaciones_seleccionadas = st.multiselect('Selecciona las cotizaciones a visualizar:', options=opciones_disponibles, default=opciones_por_defecto_hist)
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
    spreads_seleccionados = st.multiselect('Selecciona cotizaciones para ver su spread con el Oficial:', options=dolares_para_spread, default=opciones_por_defecto_spread)
    if spreads_seleccionados:
        df_spread = pd.DataFrame(index=datos_dolar.index)
        for dolar in spreads_seleccionados:
            df_spread[f'Brecha {dolar}'] = (datos_dolar[dolar] / datos_dolar['Oficial'] - 1) * 100
        st.line_chart(df_spread)
    else:
        st.warning("Selecciona al menos una cotización para ver el spread.")

    # --- SECCIÓN COMPARATIVA (CORREGIDA Y MEJORADA) ---
    st.header("🔬 Comparativa: Dólar vs. Plazo Fijo")
    st.markdown("Análisis histórico para determinar qué inversión fue más rentable en un período determinado.")

    col1, col2 = st.columns(2)
    with col1:
        opciones_dolar_comparativa = [d for d in ['Blue', 'Mep', 'Ccl'] if d in df_completo.columns]
        dolar_a_comparar = st.selectbox("Selecciona el tipo de dólar a comparar:", options=opciones_dolar_comparativa)
    with col2:
        periodo_dias = st.number_input("Selecciona el período de análisis (días):", min_value=1, max_value=365, value=30)

    if dolar_a_comparar and periodo_dias:
        # Usamos df_calculo para todos los pasos intermedios
        df_calculo = df_completo[[dolar_a_comparar, 'TNA Plazo Fijo']].copy().dropna()
        df_calculo = df_calculo.sort_index(ascending=False)

        # 1. Crear columnas con valores iniciales
        df_calculo[f'{dolar_a_comparar} Inicial'] = df_calculo[dolar_a_comparar].shift(-periodo_dias)
        df_calculo['Fecha Inicial'] = df_calculo.index.to_series().shift(-periodo_dias)

        # 2. Renombrar columnas finales para claridad
        df_calculo = df_calculo.rename(columns={dolar_a_comparar: f'{dolar_a_comparar} Final'})
        df_calculo['Fecha Final'] = df_calculo.index

        # 3. Eliminar filas que no tienen un período completo para calcular
        df_calculo = df_calculo.dropna(subset=['Fecha Inicial', f'{dolar_a_comparar} Inicial'])
        
        # 4. Calcular variaciones
        df_calculo['Variación Dólar %'] = ((df_calculo[f'{dolar_a_comparar} Final'] / df_calculo[f'{dolar_a_comparar} Inicial']) - 1) * 100
        df_calculo['Rendimiento PF %'] = (df_calculo['TNA Plazo Fijo'] / 365) * periodo_dias

        # 5. Determinar ganador
        def determinar_ganador(row):
            if row['Variación Dólar %'] > 1.0 and row['Variación Dólar %'] > row['Rendimiento PF %']:
                return "🟢 Dólar"
            elif row['Rendimiento PF %'] > row['Variación Dólar %']:
                return "🔵 Plazo Fijo"
            else:
                return "⚪ Empate / Dólar < 1%"
        df_calculo['Conclusión'] = df_calculo.apply(determinar_ganador, axis=1)

        # 6. Preparar DataFrame final para mostrar
        columnas_finales = [
            'Fecha Inicial', 'Fecha Final', f'{dolar_a_comparar} Inicial', f'{dolar_a_comparar} Final',
            'Variación Dólar %', 'Rendimiento PF %', 'Conclusión'
        ]
        df_display = df_calculo[columnas_finales].head(20)

        # 7. Formatear para una mejor visualización
        st.dataframe(df_display.style.format({
            f'{dolar_a_comparar} Inicial': '${:,.2f}',
            f'{dolar_a_comparar} Final': '${:,.2f}',
            'Variación Dólar %': '{:,.2f}%',
            'Rendimiento PF %': '{:,.2f}%',
            'Fecha Inicial': '{:%Y-%m-%d}',
            'Fecha Final': '{:%Y-%m-%d}'
        }), use_container_width=True)

    # --- Tabla de Datos Históricos ---
    st.header("📋 Tabla de Datos Históricos")
    if st.checkbox('Mostrar la tabla con los últimos 10 datos'):
        st.dataframe(df_completo.sort_index(ascending=False).head(10).round(2))

else:
    st.error("No se pudieron cargar todos los datos. Intenta refrescar la página más tarde.")
