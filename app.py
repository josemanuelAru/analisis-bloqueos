import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de la página en formato ancho
st.set_page_config(page_title="Insights Hub Dashboard", layout="wide", page_icon="📊")

st.title("📊 Dashboard Interactivo de Insights Hub")
st.write("Sube tu archivo CSV para visualizar la tabla, aplicar filtros avanzados y comparar variables con escalas independientes (Doble Eje Y).")

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
        
        # --- SECCIÓN 3: GENERADOR DINÁMICO DE GRÁFICAS (CON DOBLE EJE Y) ---
        st.subheader("📊 Generador Dinámico de Gráficas")
        st.write("💡 **Tip Pro:** Selecciona **exactamente 2 métricas** en el Eje Y (por ejemplo, `Aftrad IMPs` y `AF Blocked IMPs` o `Blocked %`) para activar automáticamente el **doble eje Y**. La primera variable irá a la izquierda y la segunda a la derecha escalada de forma independiente.")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        
        columnas_disponibles = [c for c in display_df.columns]
        # Dejamos todas las numéricas disponibles (incluyendo el porcentaje por si quieren cruzar volumen vs porcentaje)
        columnas_numericas = [c for c in columnas_disponibles if df[c].dtype in ['int64', 'float64']]
        
        with col_g1:
            eje_x = st.selectbox("Eje X (Variable categórica o temporal):", options=columnas_disponibles, index=0)
        with col_g2:
            # Ponemos por defecto las dos métricas de impresión y bloqueo para comparar
            valores_defecto = [c for c in ['Aftrad IMPs', 'AF Blocked IMPs'] if c in columnas_numericas]
            ejes_y = st.multiselect("Eje Y (Métricas numéricas a comparar):", options=columnas_numericas, default=valores_defecto)
        with col_g3:
            tipo_grafico = st.selectbox("Tipo de representación gráfica:", options=["Líneas de Tendencia", "Barras Comparativas"])
            
        if eje_x and ejes_y:
            # Agrupar los datos acumulando las métricas numéricas seleccionadas
            # Si se selecciona 'Blocked %', usamos la media (mean), si son impresiones absolutas usamos la suma (sum)
            # Para simplificar la consistencia del cuadro de mandos, calculamos agregaciones apropiadas:
            agg_dict = {metrica: ('mean' if 'percent' in metrica.lower() or '%' in metrica else 'sum') for metrica in ejes_y}
            df_grouped = df.groupby(eje_x, as_index=False).agg(agg_dict)
            
            # Ordenación cronológica si el eje X es la Fecha
            if eje_x == 'Date' and 'Date_Parsed' in df.columns:
                df_grouped['Date_Sort'] = pd.to_datetime(df_grouped['Date'], errors='coerce')
                df_grouped = df_grouped.sort_values(by='Date_Sort').drop(columns=['Date_Sort'])
            else:
                df_grouped = df_grouped.sort_values(by=ejes_y[0], ascending=False)
            
            # CONTROL LÓGICO: ¿Activamos el Doble Eje Y? (Si hay exactamente 2 variables seleccionadas)
            if len(ejes_y) == 2:
                # Crear figura con eje Y secundario nativo de Plotly
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                var_izquierda = ejes_y[0]
                var_derecha = ejes_y[1]
                
                if tipo_grafico == "Líneas de Tendencia":
                    # Línea 1 (Izquierda)
                    fig.add_trace(
                        go.Scatter(x=df_grouped[eje_x], y=df_grouped[var_izquierda], name=var_izquierda, mode='lines+markers'),
                        secondary_y=False
                    )
                    # Línea 2 (Derecha - Escalada independiente)
                    fig.add_trace(
                        go.Scatter(x=df_grouped[eje_x], y=df_grouped[var_derecha], name=var_derecha, mode='lines+markers', line=dict(dash='dash')),
                        secondary_y=True
                    )
                else:  # Barras Comparativas
                    # Barra 1 (Izquierda)
                    fig.add_trace(
                        go.Bar(x=df_grouped[eje_x], y=df_grouped[var_izquierda], name=var_izquierda, opacity=0.75),
                        secondary_y=False
                    )
                    # Barra 2 (Derecha - Escalada independiente)
                    fig.add_trace(
                        go.Bar(x=df_grouped[eje_x], y=df_grouped[var_derecha], name=var_derecha, opacity=0.75),
                        secondary_y=True
                    )
                
                # Configurar títulos y etiquetas de los ejes correspondientes
                fig.update_layout(
                    title_text=f"Análisis Avanzado: {var_izquierda} (Eje Izquierdo) vs {var_derecha} (Eje Derecho - Escalado) por {eje_x}",
                    hovermode="x unified"
                )
                fig.update_yaxes(title_text=f"<b>{var_izquierda}</b> (Escala Principal)", secondary_y=False)
                fig.update_yaxes(title_text=f"<b>{var_derecha}</b> (Escala Secundaria Derecha)", secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                # COMPORTAMIENTO ESTÁNDAR: Si eligen 1 o más de 2 métricas (Eje Y único compartido)
                if tipo_grafico == "Barras Comparativas":
                    fig = px.bar(df_grouped, x=eje_x, y=ejes_y, barmode='group', title=f"Distribución de métricas por {eje_x}", labels={"value": "Cantidad", "variable": "Métrica"})
                else:
                    fig = px.line(df_grouped, x=eje_x, y=ejes_y, markers=True, title=f"Tendencias de métricas a lo largo de {eje_x}", labels={"value": "Cantidad", "variable": "Métrica"})
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Selecciona al menos una métrica en el menú del Eje Y para poder generar la gráfica.")
                
    except Exception as e:
        st.error(f"Se ha producido un error al procesar la estructura del CSV: {e}")
else:
    st.info("💡 Sube tu archivo CSV desde el panel central para activar los filtros y las gráficas automáticas.")
