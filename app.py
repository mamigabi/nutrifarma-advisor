import streamlit as st
import os
from datetime import datetime
import google.generativeai as genai

# Configuración de la página
st.set_page_config(
    page_title="NutriFarma Advisor",
    page_icon="🏥",
    layout="wide"
)

# Obtener API key de Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

if not GEMINI_API_KEY:
    st.error("⚠️ Error: No se ha configurado GEMINI_API_KEY")
    st.info("Configura la variable de entorno GEMINI_API_KEY en Streamlit Cloud")
    st.stop()

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Prompt del sistema
SYSTEM_PROMPT = """
Eres **NutriFarma Advisor**, un asistente de IA especializado en consejo nutricional 
para farmacéuticos en oficinas de farmacia de España.

# REGLAS FUNDAMENTALES:
1. NUNCA sustituyas el criterio profesional del farmacéutico
2. Proporciona información basada en evidencia científica actualizada
3. SIEMPRE incluye advertencias sobre cuándo derivar al médico o dietista-nutricionista
4. Responde en español de España, lenguaje claro y profesional

# LÍMITES ÉTICOS - NO RESPONDAS SOBRE:
- Dietas para cáncer, enfermedades renales/hepáticas graves
- Planes de pérdida de peso extremos
- Sustitución de tratamientos médicos
- Nutrición para menores de 2 años
- Trastornos de conducta alimentaria

# FORMATO DE RESPUESTA:

**🎯 Recomendación Principal:**
[Consejo directo y accionable en 2-3 líneas]

**✅ Alimentos Recomendados:**
• [Opción 1 con razón]
• [Opción 2 con razón]

**⚠️ Alimentos a Evitar/Moderar:**
• [Alimento 1 + motivo]
• [Alimento 2 + motivo]

**💊 Interacciones Medicamento-Nutriente:**
[Solo si aplica. Si hay medicación, SIEMPRE verifica interacciones]

**📌 Nota Profesional:**
"Este es un consejo nutricional general. Para un plan personalizado completo, 
recomiende derivar a dietista-nutricionista colegiado. Si los síntomas persisten 
más de 3-5 días o empeoran, derivar a consulta médica."
"""

# Título y descripción
st.title("🏥 NutriFarma Advisor")
st.markdown("**Asistente de IA para consejo nutricional en farmacias**")
st.markdown("---")

# Información importante
with st.expander("⚠️ Advertencia Legal - Leer antes de usar"):
    st.warning("""
    **IMPORTANTE:**
    - Esta herramienta ASISTE al criterio del farmacéutico, NO lo sustituye
    - La responsabilidad última del consejo recae en el profesional
    - NO es un diagnóstico ni un tratamiento médico
    - Consultar siempre fuentes oficiales y guías actualizadas
    """)

# Entrada de consulta
st.subheader("📝 Introduce la consulta")

col1, col2 = st.columns([1, 1])

with col1:
    edad = st.number_input("Edad del paciente", min_value=0, max_value=120, value=45)
    sexo = st.selectbox("Sexo", ["Mujer", "Hombre", "No especificado"])
    
with col2:
    condicion = st.multiselect(
        "Condiciones de salud",
        ["Diabetes tipo 2", "Hipertensión", "Colesterol alto", 
         "Estreñimiento", "Osteoporosis", "Sobrepeso", "Otra"]
    )
    medicacion = st.text_input("Medicación actual (separada por comas)", 
                                placeholder="Ej: metformina, enalapril")

consulta = st.text_area(
    "Pregunta del paciente",
    placeholder="Ej: ¿Qué puede desayunar que no le suba el azúcar?",
    height=100
)

if st.button("🔍 Consultar", type="primary", use_container_width=True):
    if not consulta:
        st.warning("⚠️ Por favor, introduce una consulta")
    else:
        with st.spinner("🤖 Procesando consulta con Gemini 2.0 Flash..."):
            try:
                # Construir contexto completo
                contexto = f"""
Datos del paciente:
- Edad: {edad} años
- Sexo: {sexo}
- Condiciones: {', '.join(condicion) if condicion else 'Ninguna especificada'}
- Medicación: {medicacion if medicacion else 'Ninguna especificada'}

Consulta del farmacéutico: {consulta}
"""
                
                # Crear modelo con búsqueda web
                model = genai.GenerativeModel(
                    'gemini-2.0-flash-exp',
                    tools='google_search_retrieval'
                )
                
                # Generar respuesta
                response = model.generate_content(SYSTEM_PROMPT + "\n\n" + contexto)
                
                # Mostrar respuesta
                st.markdown("### 📊 Respuesta de NutriFarma Advisor:")
                st.markdown(response.text)
                
                # Información adicional
                st.markdown("---")
                st.caption(f"🕒 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                st.caption("🌐 Con búsqueda web en tiempo real (Gemini 2.0 Flash)")
                
            except Exception as e:
                st.error(f"❌ Error al procesar la consulta: {str(e)}")
                st.info("💡 Verifica que la API key de Gemini esté configurada correctamente")

# Sidebar con información
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/pharmacy-shop.png", width=80)
    st.markdown("### 📊 Información")
    st.info("""
    **Versión:** 1.0.0  
    **Modelo:** Gemini 2.0 Flash  
    **Base de datos:** CIMA AEMPS  
    **Actualización:** Diaria
    """)
    
    st.markdown("### 📚 Recursos")
    st.markdown("""
    - [CIMA AEMPS](https://cima.aemps.es)
    - [Medynut](https://www.medynut.com)
    - [AESAN](https://www.aesan.gob.es)
    """)
    
    st.markdown("### 🛡️ Privacidad")
    st.success("No se almacenan datos personales")
