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

# Estilo personalizado para una apariencia profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
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
    sf_token = st.text_input("Security Token", type="password")
    
    # Configuración de Dominio para Sovos Compliance
    domain_type = st.sidebar.selectbox(
        "Entorno / Dominio",
        ["Personalizado", "login", "test"],
        index=0,
        help="Para Sovos, usa 'Personalizado' con el subdominio de la empresa."
    )
    
    if domain_type == "Personalizado":
        # Los dominios personalizados de Salesforce requieren el formato 'subdominio.my.salesforce.com'
        sf_domain = st.sidebar.text_input("Subdominio", value="sovos-compliance.my", help="Ej: sovos-compliance.my")
    elif domain_type == "test":
        sf_domain = "test"
    else:
        sf_domain = "login"

    # ID del reporte actualizado del nuevo link: 00OPr000002rd0TMAQ
    report_id = st.text_input("ID del Reporte", value="00OPr000002rd0TMAQ")

st.sidebar.divider()
st.sidebar.info("""
**Instrucciones para Sovos:**
1. El subdominio predeterminado es `sovos-compliance.my`.
2. El ID del reporte ya está actualizado según tu último enlace.
3. Asegúrate de ingresar tu contraseña y token correctamente.
""")

@st.cache_resource(show_spinner=False)
def get_sf_connection(user, password, token, domain):
    """Establece la conexión con la API de Salesforce."""
    if not all([user, password, token]):
        return None
    try:
        # La librería añade automáticamente .salesforce.com al final del domain
        return Salesforce(
            username=user, 
            password=password, 
            security_token=token, 
            domain=domain
        )
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return None

def parse_sf_report(report_results):
    """Limpia el JSON complejo de Salesforce y lo convierte en DataFrame."""
    try:
        columns = []
        col_info = report_results['reportExtendedMetadata']['detailColumnInfo']
        for col_key in col_info:
            columns.append(col_info[col_key]['label'])
        
        rows_data = []
        # T!T es la clave para reportes tabulares (listas)
        rows = report_results['factMap']['T!T']['rows']
        for row in rows:
            current_row = [cell.get('value') if cell.get('value') is not None else cell.get('label') for cell in row['dataCells']]
            rows_data.append(current_row)
        
        df = pd.DataFrame(rows_data, columns=columns)
        # Intentamos convertir columnas a números para graficar
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        return df
    except KeyError:
        st.error("El formato del reporte no parece ser tabular o no tiene filas de detalle.")
        return pd.DataFrame()

# --- CUERPO PRINCIPAL ---
st.title("🚀 Salesforce Insights Dashboard")
st.caption(f"Conectando a: {sf_domain}.salesforce.com")

if sf_user and sf_pass and sf_token:
    sf = get_sf_connection(sf_user, sf_pass, sf_token, sf_domain)
    
    if sf:
        with st.spinner('⏳ Sincronizando datos de Sovos...'):
            try:
                # Llamada a la API de Analytics para obtener la data del reporte
                report_data = sf.restful(f'analytics/reports/{report_id}')
                df = parse_sf_report(report_data)
                
                if not df.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Registros Totales", f"{len(df):,}")
                    m2.metric("Columnas", len(df.columns))
                    m3.metric("Entorno", domain_type, delta="Activo")

                    st.divider()

                    tab1, tab2 = st.tabs(["📈 Análisis Visual", "📋 Explorador de Datos"])

                    with tab1:
                        col_left, col_right = st.columns([1, 2])
                        with col_left:
                            st.subheader("Configuración")
                            eje_x = st.selectbox("Eje X (Categoría)", df.columns, index=0)
                            eje_y = st.selectbox("Eje Y (Valor)", df.columns, index=min(1, len(df.columns)-1))
                            tipo = st.radio("Gráfico", ["Barras", "Líneas"])
                        
                        with col_right:
                            if tipo == "Barras":
                                fig = px.bar(df, x=eje_x, y=eje_y, template="plotly_white", color_discrete_sequence=['#00a1e0'])
                            else:
                                fig = px.line(df, x=eje_x, y=eje_y, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.dataframe(df, use_container_width=True, height=500)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Descargar Tabla (CSV)", csv, "reporte_sovos.csv", "text/csv")
                else:
                    st.warning("El reporte no devolvió datos. Asegúrate de que el reporte tenga registros visibles en Salesforce.")

            except Exception as e:
                st.error(f"Error al procesar el reporte: {e}")
    else:
        st.error("Error de autenticación. Verifica credenciales y subdominio.")
else:
    st.info("👈 Por favor, ingresa tus credenciales en la barra lateral para visualizar el dashboard.")
