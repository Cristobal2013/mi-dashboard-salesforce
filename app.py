import streamlit as st
import pandas as pd
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
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
    # .strip() elimina espacios accidentales al inicio/final
    sf_user = st.text_input("Usuario (Email)", placeholder="usuario@empresa.com").strip()
    sf_pass = st.text_input("Contraseña", type="password").strip()
    sf_token = st.text_input("Security Token", type="password").strip()
    
    domain_type = st.sidebar.selectbox(
        "Entorno / Dominio",
        ["Personalizado", "login", "test"],
        index=0
    )
    
    if domain_type == "Personalizado":
        sf_domain = st.sidebar.text_input("Subdominio", value="sovos-compliance.my").strip()
    elif domain_type == "test":
        sf_domain = "test"
    else:
        sf_domain = "login"

    report_id = st.text_input("ID del Reporte", value="00OPr000002rd0TMAQ").strip()

st.sidebar.divider()

@st.cache_resource(show_spinner=False)
def get_sf_connection(user, password, token, domain):
    """Establece la conexión con la API de Salesforce con manejo de errores mejorado."""
    if not all([user, password, token]):
        return None
    try:
        return Salesforce(
            username=user, 
            password=password, 
            security_token=token, 
            domain=domain
        )
    except SalesforceAuthenticationFailed as auth_error:
        st.sidebar.error(f"❌ Error de Credenciales: {auth_error}")
        st.sidebar.info("""
        **Guía de solución:**
        1. **Token:** Asegúrate de que el Token sea el más reciente enviado a tu correo.
        2. **Mayúsculas:** La contraseña y el token distinguen entre mayúsculas y minúsculas.
        3. **Bloqueo:** Si intentaste muchas veces, tu usuario podría estar bloqueado en Salesforce (espera 15 min).
        """)
        return None
    except Exception as e:
        st.sidebar.error(f"Error inesperado: {e}")
        return None

def parse_sf_report(report_results):
    """Limpia el JSON complejo de Salesforce y lo convierte en DataFrame."""
    try:
        columns = []
        col_info = report_results['reportExtendedMetadata']['detailColumnInfo']
        for col_key in col_info:
            columns.append(col_info[col_key]['label'])
        
        rows_data = []
        rows = report_results['factMap']['T!T']['rows']
        for row in rows:
            current_row = [cell.get('value') if cell.get('value') is not None else cell.get('label') for cell in row['dataCells']]
            rows_data.append(current_row)
        
        df = pd.DataFrame(rows_data, columns=columns)
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        return df
    except Exception:
        st.error("Error al procesar la estructura del reporte.")
        return pd.DataFrame()

# --- CUERPO PRINCIPAL ---
st.title("🚀 Salesforce Insights Dashboard")
st.caption(f"Conectando a: {sf_domain}.salesforce.com")

if sf_user and sf_pass and sf_token:
    sf = get_sf_connection(sf_user, sf_pass, sf_token, sf_domain)
    
    if sf:
        with st.spinner('⏳ Sincronizando datos de Sovos...'):
            try:
                report_data = sf.restful(f'analytics/reports/{report_id}')
                df = parse_sf_report(report_data)
                
                if not df.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Registros Totales", f"{len(df):,}")
                    m2.metric("Columnas", len(df.columns))
                    m3.metric("Estado", "Conectado ✅")

                    st.divider()

                    tab1, tab2 = st.tabs(["📈 Análisis Visual", "📋 Datos"])

                    with tab1:
                        col_left, col_right = st.columns([1, 2])
                        with col_left:
                            eje_x = st.selectbox("Categoría", df.columns, index=0)
                            eje_y = st.selectbox("Valor", df.columns, index=min(1, len(df.columns)-1))
                            tipo = st.radio("Gráfico", ["Barras", "Líneas"])
                        
                        with col_right:
                            fig = px.bar(df, x=eje_x, y=eje_y, template="plotly_white", color_discrete_sequence=['#00a1e0']) if tipo == "Barras" else px.line(df, x=eje_x, y=eje_y, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.dataframe(df, use_container_width=True, height=500)
                        st.download_button("📥 Descargar CSV", df.to_csv(index=False), "reporte.csv")
            except Exception as e:
                st.error(f"Error al obtener reporte: {e}")
    else:
        st.warning("A la espera de credenciales válidas...")
else:
    st.info("👈 Ingresa tus credenciales para comenzar. El Security Token es obligatorio.")
