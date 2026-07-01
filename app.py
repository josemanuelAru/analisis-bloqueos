import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página en formato ancho
st.set_page_config(page_title="Insights Hub Dashboard", layout="wide", page_icon="📊")

st.title("📊 Dashboard Interactivo de Insights Hub")
st.write("Sube tu archivo CSV para visualizar la tabla, aplicar filtros avanzados y generar gráficas interactivas dinámicas.")

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
            # Controlar que se seleccionen ambas fechas (inicio y fin) antes de filtrar
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df['Date_Parsed'].dt.date >= start_date) & (df['Date_Parsed'].dt.date <= end_date)]

        # --- SECCIÓN 1: TARJETAS DE MÉTRICAS CLAVE ---
        st.subheader("📈 Resumen de Métricas (Datos Filtrados)")
        col1, col2, col3 = st.columns(3)
        
        total_imps = df['Aftrad IMPs'].sum() if 'Aftrad IMPs' in df.columns else 0
        total_blocked = df['AF Blocked IMPs'].sum() if 'AF Blocked IMPs' in df.columns else 0
        
        # Calcular el porcentaje global bloqueado de la selección actual
        avg_blocked_pct = (total_blocked / total_imps) * 100 if total_imps > 0 else 0.0
            
        col1.metric("Total Aftrad IMPs", f"{total_imps:,}")
        col2.metric("Total AF Blocked IMPs", f"{total_blocked:,}")
        col3.metric("Blocked % Global", f"{avg_blocked_pct:.2f}%")
        
        # --- SECCIÓN 2: VISTA DE LA TABLA ---
        st.subheader("📋 Tabla de Datos General")
        # Quitamos la columna técnica de fecha antes de mostrar la tabla limpia
        display_df = df.drop(columns=['Date_Parsed']) if 'Date_Parsed' in df.columns else df
        st.dataframe(display_df, use_container_width=True)
        
        # --- SECCIÓN 3: GENERADOR DINÁMICO DE GRÁFICAS ---
        st.subheader("📊 Generador Dinámico de Gráficas")
        st.write("Configura las variables que deseas cruzar para analizar los datos visualmente:")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        
        columnas_disponibles = [c for c in display_df.columns]
        columnas_numericas = [c for c in columnas_disponibles if df[c].dtype in ['int64', 'float64']]
        
        with col_g1:
            eje_x = st.selectbox("Eje X (Variable categórica o temporal):", options=columnas_disponibles, index=0)
        with col_g2:
            eje_y = st.selectbox("Eje Y (Métrica numérica acumulativa):", options=columnas_numericas, index=0 if columnas_numericas else None)
        with col_g3:
            tipo_grafico = st.selectbox("Tipo de representación gráfica:", options=["Barras (Agrupado por Total)", "Líneas (Tendencia Temporal)", "Dispersión (Puntos Scatter)"])
            
        if eje_x and eje_y:
            if tipo_grafico == "Barras (Agrupado por Total)":
                # Agrupar y ordenar para que las barras salgan ordenadas por volumen de mayor a menor
                df_grouped = df.groupby(eje_x, as_index=False)[eje_y].sum().sort_values(by=eje_y, ascending=False)
                fig = px.bar(df_grouped, x=eje_x, y=eje_y, title=f"Total de {eje_y} distribuido por {eje_x}", text_auto='.2s', color=eje_x)
                st.plotly_chart(fig, use_container_width=True)
                
            elif tipo_grafico == "Líneas (Tendencia Temporal)":
                df_grouped = df.groupby(eje_x, as_index=False)[eje_y].sum()
                if eje_x == 'Date' and 'Date_Parsed' in df.columns:
                    df_grouped['Date_Sort'] = pd.to_datetime(df_grouped['Date'], errors='coerce')
                    df_grouped = df_grouped.sort_values(by='Date_Sort')
                fig = px.line(df_grouped, x=eje_x, y=eje_y, title=f"Evolución de {eje_y} a lo largo de {eje_x}", markers=True)
                st.plotly_chart(fig, use_container_width=True)
                
            elif tipo_grafico == "Dispersión (Puntos Scatter)":
                fig = px.scatter(df, x=eje_x, y=eje_y, color='AM' if 'AM' in df.columns else None, hover_data=columnas_disponibles, title=f"Correlación/Dispersión entre {eje_y} y {eje_x}")
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Se ha producido un error al procesar la estructura del CSV: {e}")
else:
    st.info("💡 Sube tu archivo CSV desde el panel central para activar los filtros y las gráficas automáticas.")
