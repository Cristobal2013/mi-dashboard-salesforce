import streamlit as st
import pandas as pd
from simple_salesforce import Salesforce
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Salesforce Real-Time Dashboard",
    page_icon="📊",
    layout="wide"
)

# Estilo personalizado para mejorar la estética
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("🔑 Configuración de Conexión")
with st.sidebar.expander("Credenciales de Salesforce", expanded=True):
    sf_user = st.text_input("Usuario (Email)", placeholder="usuario@empresa.com")
    sf_pass = st.text_input("Contraseña", type="password")
    sf_token = st.text_input("Security Token", type="password", help="El token que recibes por email al resetearlo.")
    report_id = st.text_input("ID del Reporte", value="00OPr000002rd0TMAQ")

st.sidebar.divider()
st.sidebar.info("""
**Instrucciones:**
1. Ingresa tus credenciales en la izquierda.
2. La app extraerá automáticamente los datos del reporte.
3. Puedes descargar la data limpia al final.
""")

@st.cache_resource(show_spinner=False)
def get_sf_connection(user, password, token):
    """Establece la conexión con la API de Salesforce."""
    if not all([user, password, token]):
        return None
    try:
        return Salesforce(username=user, password=password, security_token=token)
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return None

def parse_sf_report(report_results):
    """
    Limpia el JSON complejo de Salesforce (factMap) 
    y lo convierte en un DataFrame de Pandas.
    """
    # 1. Extraer nombres de columnas y metadatos
    columns = []
    col_info = report_results['reportExtendedMetadata']['detailColumnInfo']
    for col_key in col_info:
        columns.append(col_info[col_key]['label'])
    
    # 2. Extraer datos de las filas
    rows_data = []
    rows = report_results['factMap']['T!T']['rows']
    
    for row in rows:
        current_row = []
        for cell in row['dataCells']:
            # Priorizar el valor numérico para cálculos, si no existe usar la etiqueta
            val = cell.get('value')
            if val is None:
                val = cell.get('label')
            current_row.append(val)
        rows_data.append(current_row)
    
    df = pd.DataFrame(rows_data, columns=columns)
    
    # Intentar convertir columnas numéricas automáticamente
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='ignore')
        
    return df

# --- CUERPO PRINCIPAL ---
st.title("🚀 Salesforce Insights Dashboard")
st.caption("Conexión directa vía API para reportes tabulares.")

if sf_user and sf_pass and sf_token:
    sf = get_sf_connection(sf_user, sf_pass, sf_token)
    
    if sf:
        with st.spinner('⏳ Sincronizando con Salesforce...'):
            try:
                # Llamada a la API de Analytics
                report_data = sf.restful(f'analytics/reports/{report_id}')
                df = parse_sf_report(report_data)
                
                # --- KPI SECTION ---
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Registros", f"{len(df):,}")
                m2.metric("Columnas Activas", len(df.columns))
                m3.metric("Última Sincronización", "Ahora", delta="Online")

                st.divider()

                # --- CONTENIDO ---
                tab1, tab2 = st.tabs(["📈 Análisis Visual", "📋 Datos Crudos"])

                with tab1:
                    col_left, col_right = st.columns([1, 2])
                    
                    with col_left:
                        st.subheader("Configurar Gráfico")
                        eje_x = st.selectbox("Selecciona Eje X (Categoría)", df.columns, index=0)
                        eje_y = st.selectbox("Selecciona Eje Y (Valor)", df.columns, index=min(1, len(df.columns)-1))
                        tipo_grafico = st.radio("Tipo de visualización", ["Barras", "Líneas", "Dispersión"])

                    with col_right:
                        if tipo_grafico == "Barras":
                            fig = px.bar(df, x=eje_x, y=eje_y, template="plotly_white", color_discrete_sequence=['#00a1e0'])
                        elif tipo_grafico == "Líneas":
                            fig = px.line(df, x=eje_x, y=eje_y, template="plotly_white")
                        else:
                            fig = px.scatter(df, x=eje_x, y=eje_y, template="plotly_white")
                        
                        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Explorador de Tabla")
                    st.dataframe(df, use_container_width=True, height=500)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Reporte Completo (CSV)",
                        data=csv,
                        file_name=f"reporte_sf_{report_id}.csv",
                        mime="text/csv",
                    )

            except Exception as e:
                st.error(f"Error al procesar el reporte: {e}")
                st.info("💡 Tip: Verifica que el ID del reporte sea correcto y que el reporte en Salesforce tenga filas de detalle activadas.")
    else:
        st.error("No se pudo establecer la conexión. Verifica tus credenciales.")
else:
    st.info("👈 Por favor, ingresa tus credenciales de Salesforce en la barra lateral para comenzar.")
    
    # Imagen de marcador de posición para la interfaz inicial
    st.image("https://www.salesforce.com/content/dam/web/en_us/www/images/home/php-hero-bg.jpg", opacity=0.1)