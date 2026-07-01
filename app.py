import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página en formato ancho
st.set_page_config(page_title="Insights Hub Dashboard", layout="wide", page_icon="📊")

st.title("📊 Dashboard Interactivo de Insights Hub")
st.write("Sube tu archivo CSV para visualizar la tabla, aplicar filtros avanzados y comparar múltiples variables en las gráficas.")

# Contenedor para subir el archivo CSV
uploaded_file = st.file_uploader("Elige tu archivo CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Leer el CSV cargado por el usuario
        df = pd.read_csv(uploaded_file)
        
        # Intentar transformar la columna Date para permitir filtros cronológicos ordenados
        if 'Date' in df.columns:
            df['Date_Parsed'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date_Parsed', ascending=True)
        
        st.success("¡Archivo CSV cargado e interpretado con éxito!")
        
        # --- SIDEBAR / BARRA LATERAL DE FILTROS ---
        st.sidebar.header("🔍 Filtros de Datos")
        
        # Filtro por Account Manager (AM)
        if 'AM' in df.columns:
            lista_am = df['AM'].dropna().unique().tolist()
            selected_am = st.sidebar.multiselect("Filtrar por AM:", options=lista_am, default=lista_am)
            df = df[df['AM'].isin(selected_am)]
            
        # Filtro por Anunciante (ADV)
        if 'ADV' in df.columns:
            lista_adv = df['ADV'].dropna().unique().tolist()
            selected_adv = st.sidebar.multiselect("Filtrar por ADV (Anunciante):", options=lista_adv, default=lista_adv)
            df = df[df['ADV'].isin(selected_adv)]
            
        # Filtro por Agencia (Agency)
        if 'Agency' in df.columns:
            lista_agency = df['Agency'].dropna().unique().tolist()
            selected_agency = st.sidebar.multiselect("Filtrar por Agencia:", options=lista_agency, default=lista_agency)
            df = df[df['Agency'].isin(selected_agency)]
            
        # Filtro por Rango de Fechas
        if 'Date' in df.columns and not df['Date_Parsed'].isnull().all():
            min_date = df['Date_Parsed'].min().date()
            max_date = df['Date_Parsed'].max().date()
            date_range = st.sidebar.date_input("Rango de fechas:", [min_date, max_date], min_value=min_date, max_value=max_date)
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df['Date_Parsed'].dt.date >= start_date) & (df['Date_Parsed'].dt.date <= end_date)]

        # --- SECCIÓN 1: TARJETAS DE MÉTRICAS CLAVE ---
        st.subheader("📈 Resumen de Métricas (Datos Filtrados)")
        col1, col2, col3 = st.columns(3)
        
        total_imps = df['Aftrad IMPs'].sum() if 'Aftrad IMPs' in df.columns else 0
        total_blocked = df['AF Blocked IMPs'].sum() if 'AF Blocked IMPs' in df.columns else 0
        avg_blocked_pct = (total_blocked / total_imps) * 100 if total_imps > 0 else 0.0
            
        col1.metric("Total Aftrad IMPs", f"{total_imps:,}")
        col2.metric("Total AF Blocked IMPs", f"{total_blocked:,}")
        col3.metric("Blocked % Global", f"{avg_blocked_pct:.2f}%")
        
        # --- SECCIÓN 2: VISTA DE LA TABLA ---
        st.subheader("📋 Tabla de Datos General")
        display_df = df.drop(columns=['Date_Parsed']) if 'Date_Parsed' in df.columns else df
        st.dataframe(display_df, use_container_width=True)
        
        # --- SECCIÓN 3: GENERADOR DINÁMICO DE GRÁFICAS (MULTIVARIABLE) ---
        st.subheader("📊 Generador Dinámico de Gráficas")
        st.write("Configura las variables. ¡Ahora puedes seleccionar una o varias métricas en el eje Y para compararlas!")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        
        columnas_disponibles = [c for c in display_df.columns]
        # Identificar columnas numéricas aptas para sumar (excluyendo el porcentaje si se desea comparar volúmenes absolutos)
        columnas_numericas = [c for c in columnas_disponibles if df[c].dtype in ['int64', 'float64'] and c != 'Blocked %']
        
        with col_g1:
            eje_x = st.selectbox("Eje X (Variable categórica o temporal):", options=columnas_disponibles, index=0)
        with col_g2:
            # Cambiado a multiselect para permitir múltiples métricas en el eje Y
            valores_defecto = [columnas_numericas[0]] if columnas_numericas else []
            if len(columnas_numericas) > 1:
                # Si existen ambas columnas, las ponemos por defecto para facilitar la comparación inmediata
                valores_defecto = [c for c in ['Aftrad IMPs', 'AF Blocked IMPs'] if c in columnas_numericas]
            
            ejes_y = st.multiselect("Eje Y (Métricas numéricas a comparar):", options=columnas_numericas, default=valores_defecto)
        with col_g3:
            tipo_grafico = st.selectbox("Tipo de representación gráfica:", options=["Barras Comparativas", "Líneas de Tendencia"])
            
        if eje_x and ejes_y:
            # Agrupar los datos sumando las métricas seleccionadas para el eje X elegido
            df_grouped = df.groupby(eje_x, as_index=False)[ejes_y].sum()
            
            # Si el eje X es la fecha, nos aseguramos de ordenarlo cronológicamente
            if eje_x == 'Date' and 'Date_Parsed' in df.columns:
                df_grouped['Date_Sort'] = pd.to_datetime(df_grouped['Date'], errors='coerce')
                df_grouped = df_grouped.sort_values(by='Date_Sort').drop(columns=['Date_Sort'])
            else:
                # Si es categórico (ADV, AM, etc.), lo ordenamos por la primera métrica seleccionada para que se vea limpio
                df_grouped = df_grouped.sort_values(by=ejes_y[0], ascending=False)
            
            if tipo_grafico == "Barras Comparativas":
                # barmode='group' coloca las barras de las distintas métricas una al lado de la otra por cada elemento del eje X
                fig = px.bar(
                    df_grouped, 
                    x=eje_x, 
                    y=ejes_y, 
                    title=f"Comparativa de métricas distribuidas por {eje_x}",
                    barmode='group',
                    labels={"value": "Cantidad Total", "variable": "Métrica"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif tipo_grafico == "Líneas de Tendencia":
                fig = px.line(
                    df_grouped, 
                    x=eje_x, 
                    y=ejes_y, 
                    title=f"Evolución y comparativa de métricas a lo largo de {eje_x}", 
                    markers=True,
                    labels={"value": "Cantidad Total", "variable": "Métrica"}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Selecciona al menos una métrica en el menú del Eje Y para poder generar la gráfica.")
                
    except Exception as e:
        st.error(f"Se ha producido un error al procesar la estructura del CSV: {e}")
else:
    st.info("💡 Sube tu archivo CSV desde el panel central para activar los filtros y las gráficas automáticas.")
