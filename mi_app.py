import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Análisis Dólar vs. Plazo Fijo en Argentina",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Monitor y Comparador: Dólar vs. Plazo Fijo")
st.markdown("Herramienta para analizar cotizaciones históricas y comparar el rendimiento del dólar contra un plazo fijo.")

# --- Funciones de Carga y Procesamiento de Datos ---
@st.cache_data(ttl=3600)
def cargar_datos_dolar():
    url = 'https://api.argentinadatos.com/v1/cotizaciones/dolares'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df_pivote = df.pivot_table(index='fecha', columns='casa', values='venta')
        df_pivote.columns = [str(col).capitalize() for col in df_pivote.columns]
        return df_pivote.dropna(subset=['Oficial'])
    except Exception as e:
        st.error(f"Error al cargar datos del dólar: {e}")
        return None

@st.cache_data(ttl=3600)
def cargar_datos_plazo_fijo():
    url = 'https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['fecha', 'valor'])
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.set_index('fecha')
        return df.rename(columns={'valor': 'TNA Plazo Fijo'})
    except Exception as e:
        st.error(f"Error al cargar datos de Plazo Fijo: {e}")
        return None

# --- Carga de Datos ---
datos_dolar = cargar_datos_dolar()
datos_pf = cargar_datos_plazo_fijo()

if datos_dolar is not None and not datos_dolar.empty and datos_pf is not None and not datos_pf.empty:
    df_completo = datos_dolar.join(datos_pf, how='left')
    df_completo['TNA Plazo Fijo'] = pd.to_numeric(df_completo['TNA Plazo Fijo'], errors='coerce').ffill()
    df_completo.dropna(subset=datos_dolar.columns, inplace=True)

    # --- SECCIÓN COMPARATIVA ---
    st.header("🔬 Comparativa Histórica: Dólar vs. Plazo Fijo")

    st.subheader("Configuración del Análisis")
    col1, col2 = st.columns(2)
    with col1:
        opciones_dolar = [d for d in ['Blue', 'Mep', 'Ccl'] if d in df_completo.columns]
        dolar_a_comparar = st.selectbox("1. Selecciona el tipo de dólar:", options=opciones_dolar)
    with col2:
        periodo_dias = st.number_input("2. Período de inversión (días):", min_value=1, max_value=365, value=30)
    
    st.subheader("Filtro de Fechas")
    col_f1, col_f2 = st.columns(2)
    
    # --- BLOQUE DE CÓDIGO CORREGIDO ---
    fecha_minima_disponible = df_completo.index.min().date()
    fecha_maxima_disponible = df_completo.index.max().date()

    # Calculamos un valor por defecto seguro para la fecha de inicio.
    valor_defecto_inicio = max(fecha_minima_disponible, fecha_maxima_disponible - timedelta(days=365))

    with col_f1:
        fecha_inicio = st.date_input(
            "Mostrar resultados DESDE:", 
            value=valor_defecto_inicio, 
            min_value=fecha_minima_disponible, 
            max_value=fecha_maxima_disponible
        )
    with col_f2:
        fecha_fin = st.date_input(
            "Mostrar resultados HASTA:", 
            value=fecha_maxima_disponible, 
            min_value=fecha_minima_disponible, 
            max_value=fecha_maxima_disponible
        )
    
    # --- FIN DEL BLOQUE CORREGIDO ---

    if dolar_a_comparar and periodo_dias and fecha_inicio <= fecha_fin:
        df_daily = df_completo.resample('D').ffill()
        df_daily[f'{dolar_a_comparar} Inicial'] = df_daily[dolar_a_comparar].shift(periodo_dias)
        
        df_calculo = df_daily.loc[df_completo.index].copy().sort_index(ascending=False)
        df_calculo.dropna(subset=[f'{dolar_a_comparar} Inicial', 'TNA Plazo Fijo'], inplace=True)
        
        df_calculo['Fecha Inicial'] = df_calculo.index - pd.to_timedelta(periodo_dias, unit='d')
        df_calculo = df_calculo.rename(columns={dolar_a_comparar: f'{dolar_a_comparar} Final'})
        
        df_calculo['Variación Dólar %'] = ((df_calculo[f'{dolar_a_comparar} Final'] / df_calculo[f'{dolar_a_comparar} Inicial']) - 1) * 100
        df_calculo['Rendimiento PF %'] = (df_calculo['TNA Plazo Fijo'] / 365) * periodo_dias
        df_calculo['Tasa Mensual (Equiv.) %'] = df_calculo['TNA Plazo Fijo'] / 12

        df_calculo['Conclusión'] = df_calculo.apply(lambda row: "🟢 Dólar" if row['Variación Dólar %'] > row['Rendimiento PF %'] else "🔵 Plazo Fijo", axis=1)

        df_display = df_calculo.reset_index().rename(columns={'fecha': 'Fecha Final'})
        
        start_date_ts = pd.Timestamp(fecha_inicio)
        end_date_ts = pd.Timestamp(fecha_fin)
        df_display = df_display[(df_display['Fecha Final'] >= start_date_ts) & (df_display['Fecha Final'] <= end_date_ts)]

        columnas_ordenadas = [
            'Fecha Inicial', 'Fecha Final', f'{dolar_a_comparar} Inicial', 
            f'{dolar_a_comparar} Final', 'Variación Dólar %',
            'Tasa Mensual (Equiv.) %', 'Rendimiento PF %', 'Conclusión'
        ]
        
        if not df_display.empty:
            st.dataframe(df_display[columnas_ordenadas].style.format({
                f'{dolar_a_comparar} Inicial': '${:,.2f}',
                f'{dolar_a_comparar} Final': '${:,.2f}',
                'Variación Dólar %': '{:,.2f}%',
                'Rendimiento PF %': '{:,.2f}%',
                'Tasa Mensual (Equiv.) %': '{:,.2f}%',
                'Fecha Inicial': '{:%Y-%m-%d}',
                'Fecha Final': '{:%Y-%m-%d}'
            }), use_container_width=True)
        else:
            st.warning("No hay datos para mostrar en el rango de fechas seleccionado. Por favor, elige un rango más amplio.")

    with st.expander("Ver Gráficos y Datos Históricos Adicionales"):
        st.header("📈 Gráfico de Cotizaciones Históricas")
        opciones_disponibles = datos_dolar.columns.tolist()
        opciones_preferidas = ['Oficial', 'Blue', 'Mep', 'Ccl']
        opciones_por_defecto_hist = [opt for opt in opciones_preferidas if opt in opciones_disponibles]
        cotizaciones_seleccionadas = st.multiselect('Selecciona cotizaciones a visualizar:', options=opciones_disponibles, default=opciones_por_defecto_hist, key='multiselect_cotizaciones')
        if cotizaciones_seleccionadas:
            st.line_chart(datos_dolar[cotizaciones_seleccionadas])
        
        st.header("📊 Spread vs. Dólar Oficial (%)")
        dolares_para_spread = [col for col in opciones_disponibles if col != 'Oficial']
        spreads_preferidos = ['Blue', 'Mep', 'Ccl']
        opciones_por_defecto_spread = [opt for opt in spreads_preferidos if opt in dolares_para_spread]
        spreads_seleccionados = st.multiselect('Selecciona cotizaciones para ver su spread:', options=dolares_para_spread, default=opciones_por_defecto_spread, key='multiselect_spread')
        if spreads_seleccionados:
            df_spread = pd.DataFrame(index=datos_dolar.index)
            for dolar in spreads_seleccionados:
                df_spread[f'Brecha {dolar}'] = (datos_dolar[dolar] / datos_dolar['Oficial'] - 1) * 100
            st.line_chart(df_spread)

        st.header("📋 Tabla de Datos Completos")
        st.dataframe(df_completo.sort_index(ascending=False).head(50).round(2))

else:
    st.error("No se pudieron cargar los datos de una o ambas APIs. Intenta refrescar la página más tarde.")
