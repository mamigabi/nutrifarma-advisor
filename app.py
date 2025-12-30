import streamlit as st
import os
from datetime import datetime, date
import google.generativeai as genai
import requests
from PIL import Image
import io
import json

# Configuración de la página
st.set_page_config(
    page_title="NutriFarma Advisor Pro",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para interfaz atractiva
st.markdown("""
<style>
    /* Estilos generales */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Tarjetas */
    .stCard {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    /* Encabezados */
    h1 {
        color: #2c3e50;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    h2 {
        color: #34495e;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
    }
    
    /* Botones */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 25px;
        font-weight: 600;
        transition: transform 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Inputs */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Obtener API key de Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

if not GEMINI_API_KEY:
    st.error("⚠️ Error: No se ha configurado GEMINI_API_KEY")
    st.info("Configura la variable de entorno GEMINI_API_KEY en Streamlit Cloud")
    st.stop()

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Inicializar session_state
if 'paciente' not in st.session_state:
    st.session_state.paciente = {
        'nombre': '',
        'edad': 30,
        'sexo': 'Mujer',
        'peso': 70.0,
        'altura': 165,
        'analiticas': {},
        'enfermedades': [],
        'medicacion': [],
        'alergias': [],
        'objetivo': ''
    }

if 'registro_alimentos' not in st.session_state:
    st.session_state.registro_alimentos = []

if 'registro_actividad' not in st.session_state:
    st.session_state.registro_actividad = []

if 'diagnostico' not in st.session_state:
    st.session_state.diagnostico = None

# Valores de referencia para analíticas
VALORES_REFERENCIA = {
    'Glucosa': {'min': 70, 'max': 100, 'unidad': 'mg/dL'},
    'Colesterol Total': {'min': 0, 'max': 200, 'unidad': 'mg/dL'},
    'HDL': {'min': 40, 'max': 999, 'unidad': 'mg/dL'},
    'LDL': {'min': 0, 'max': 100, 'unidad': 'mg/dL'},
    'Triglicéridos': {'min': 0, 'max': 150, 'unidad': 'mg/dL'},
    'HbA1c': {'min': 4.0, 'max': 5.6, 'unidad': '%'},
    'Vitamina D': {'min': 30, 'max': 100, 'unidad': 'ng/mL'},
    'Vitamina B12': {'min': 200, 'max': 900, 'unidad': 'pg/mL'},
    'Hierro': {'min': 60, 'max': 170, 'unidad': 'µg/dL'},
    'Ferritina': {'min': 20, 'max': 200, 'unidad': 'ng/mL'},
}

ENFERMEDADES_COMUNES = [
    'Diabetes Tipo 1', 'Diabetes Tipo 2', 'Prediabetes',
    'Hipertensión', 'Hipercolesterolemia', 'Obesidad',
    'Enfermedad Celíaca', 'Intolerancia a la Lactosa',
    'Síndrome de Intestino Irritable', 'Reflujo Gastroesofágico',
    'Hipotiroidismo', 'Hipertiroidismo', 'Anemia',
    'Osteoporosis', 'Artritis', 'Enfermedad Renal Crónica',
    'Hígado Graso', 'Gota', 'Ninguna'
]

# Funciones auxiliares
def calcular_imc(peso, altura):
    altura_m = altura / 100
    imc = peso / (altura_m ** 2)
    return round(imc, 1)

def clasificacion_imc(imc):
    if imc < 18.5:
        return "Bajo peso", "🟡"
    elif 18.5 <= imc < 25:
        return "Peso normal", "🟢"
    elif 25 <= imc < 30:
        return "Sobrepeso", "🟠"
    else:
        return "Obesidad", "🔴"

def verificar_analitica(parametro, valor):
    if parametro in VALORES_REFERENCIA:
        ref = VALORES_REFERENCIA[parametro]
        if ref['min'] <= valor <= ref['max']:
            return "Normal 🟢"
        elif valor < ref['min']:
            return "Bajo 🟡"
        else:
            return "Alto 🔴"
    return "Sin referencia"

def consultar_gemini(prompt, contexto_paciente):
    try:
        # Crear modelo con búsqueda web
        model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            tools='google_search_retrieval'
        )
        
        # Generar respuesta
        response = model.generate_content(prompt + "\n\n" + contexto_paciente)
        return response.text
    except Exception as e:
        return f"Error al consultar: {str(e)}"

def buscar_cima_aemps(medicamento):
    try:
        url = f"https://cima.aemps.es/cima/rest/medicamentos?nombre={medicamento}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None
        
# Título principal
st.markdown("<h1>🍎 NutriFarma Advisor Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7f8c8d; font-size: 18px;'>Asesoramiento Nutricional Integral para Farmacias</p>", unsafe_allow_html=True)

# Sidebar - Información del paciente
with st.sidebar:
    st.markdown("### 👤 Perfil del Paciente")
    
    if st.session_state.paciente['nombre']:
        st.success(f"👋 Hola, {st.session_state.paciente['nombre']}")
        imc = calcular_imc(st.session_state.paciente['peso'], st.session_state.paciente['altura'])
        clasificacion, emoji = clasificacion_imc(imc)
        st.metric("IMC", f"{imc}", f"{clasificacion} {emoji}")
    else:
        st.info("ℹ️ Complete el perfil del paciente en la pestaña 'Perfil'")
    
    st.markdown("---")
    st.markdown("### 📊 Recursos")
    st.markdown("- [CIMA AEMPS](https://cima.aemps.es)")
    st.markdown("- [Medynut](https://www.medynut.com)")
    st.markdown("- [AESAN](https://www.aesan.gob.es)")
    
    st.markdown("---")
    st.markdown("### 🔒 Privacidad")
    st.caption("No se almacenan datos personales. Toda la información se mantiene en esta sesión.")
    
    if st.button("🗑️ Limpiar Todo"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# Tabs principales
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👤 Perfil",
    "🍽️ Alimentación",
    "🏋️ Actividad",
    "💊 Medicación",
    "🩺 Diagnóstico",
    "🧠 Coaching"
])

# TAB 1: PERFIL DEL PACIENTE
with tab1:
    st.header("👤 Perfil del Paciente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Datos Personales")
        nombre = st.text_input("🏷️ Nombre Completo", value=st.session_state.paciente['nombre'])
        edad = st.number_input("🎂 Edad", min_value=1, max_value=120, value=st.session_state.paciente['edad'])
        sexo = st.selectbox("⚧️ Sexo", ["Mujer", "Hombre", "Otro"], index=["Mujer", "Hombre", "Otro"].index(st.session_state.paciente['sexo']))
        
        st.markdown("---")
        st.subheader("📊 Medidas Antropométricas")
        peso = st.number_input("⚖️ Peso (kg)", min_value=20.0, max_value=300.0, value=st.session_state.paciente['peso'], step=0.1)
        altura = st.number_input("📏 Altura (cm)", min_value=50, max_value=250, value=st.session_state.paciente['altura'])
        
        if st.button("💾 Guardar Perfil"):
            st.session_state.paciente.update({
                'nombre': nombre,
                'edad': edad,
                'sexo': sexo,
                'peso': peso,
                'altura': altura
            })
            st.success("✅ Perfil guardado exitosamente")
            st.rerun()
    
    with col2:
        st.subheader("🧩 Condiciones de Salud")
        enfermedades = st.multiselect(
            "🏫 Enfermedades Crónicas",
            ENFERMEDADES_COMUNES,
            default=st.session_state.paciente['enfermedades']
        )
        
        alergias = st.text_area(
            "⚠️ Alergias e Intolerancias",
            value="\n".join(st.session_state.paciente['alergias']),
            help="Una alergia por línea"
        )
        
        objetivo = st.text_area(
            "🎯 Objetivo Nutricional",
            value=st.session_state.paciente['objetivo'],
            placeholder="Ej: Perder peso, mejorar control glucémico, ganar masa muscular..."
        )
        
        if st.button("💾 Guardar Condiciones"):
            st.session_state.paciente['enfermedades'] = enfermedades
            st.session_state.paciente['alergias'] = alergias.split('\n') if alergias else []
            st.session_state.paciente['objetivo'] = objetivo
            st.success("✅ Condiciones guardadas")
    
    # Sección de Analíticas
    st.markdown("---")
    st.subheader("🧪 Analíticas Recientes")
    
    col_analitica1, col_analitica2 = st.columns(2)
    
    with col_analitica1:
        st.markdown("**🔴 Perfil Metabólico**")
        glucosa = st.number_input("Glucosa (mg/dL)", min_value=0.0, max_value=500.0, step=1.0, key="glucosa")
        hba1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=20.0, step=0.1, key="hba1c")
        
        st.markdown("**💛 Perfil Lipídico**")
        colesterol = st.number_input("Colesterol Total (mg/dL)", min_value=0.0, max_value=500.0, step=1.0, key="colesterol")
        hdl = st.number_input("HDL (mg/dL)", min_value=0.0, max_value=200.0, step=1.0, key="hdl")
        ldl = st.number_input("LDL (mg/dL)", min_value=0.0, max_value=300.0, step=1.0, key="ldl")
        trigliceridos = st.number_input("Triglicéridos (mg/dL)", min_value=0.0, max_value=1000.0, step=1.0, key="trig")
    
    with col_analitica2:
        st.markdown("**🔆 Vitaminas y Minerales**")
        vit_d = st.number_input("Vitamina D (ng/mL)", min_value=0.0, max_value=200.0, step=1.0, key="vitd")
        vit_b12 = st.number_input("Vitamina B12 (pg/mL)", min_value=0.0, max_value=2000.0, step=1.0, key="vitb12")
        hierro = st.number_input("Hierro (µg/dL)", min_value=0.0, max_value=500.0, step=1.0, key="hierro")
        ferritina = st.number_input("Ferritina (ng/mL)", min_value=0.0, max_value=1000.0, step=1.0, key="ferritina")
    
    if st.button("📊 Guardar y Analizar"):
        analiticas = {
            'Glucosa': glucosa if glucosa > 0 else None,
            'HbA1c': hba1c if hba1c > 0 else None,
            'Colesterol Total': colesterol if colesterol > 0 else None,
            'HDL': hdl if hdl > 0 else None,
            'LDL': ldl if ldl > 0 else None,
            'Triglicéridos': trigliceridos if trigliceridos > 0 else None,
            'Vitamina D': vit_d if vit_d > 0 else None,
            'Vitamina B12': vit_b12 if vit_b12 > 0 else None,
            'Hierro': hierro if hierro > 0 else None,
            'Ferritina': ferritina if ferritina > 0 else None,
        }
        
        # Filtrar valores nulos
        analiticas = {k: v for k, v in analiticas.items() if v is not None}
        st.session_state.paciente['analiticas'] = analiticas
        
        # Mostrar resultados
        st.success("✅ Analíticas guardadas")
        st.markdown("### 📊 Resultados")
        
        for param, valor in analiticas.items():
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                st.write(f"**{param}**")
            with col_b:
                st.write(f"{valor} {VALORES_REFERENCIA[param]['unidad']}")
            with col_c:
                estado = verificar_analitica(param, valor)
                st.write(estado)
    
    # Subida de imágenes/documentos
    st.markdown("---")
    st.subheader("📷 Subir Documentos o Imágenes")
    st.info("🚧 Funcionalidad de OCR próximamente disponible. Por ahora, puede subir imágenes para referencia visual.")
    
    uploaded_file = st.file_uploader(
        "Subir analíticas, informes médicos o fotos",
        type=['jpg', 'jpeg', 'png', 'pdf'],
        help="Los documentos se usarán solo como referencia visual en esta sesión"
    )
    
    if uploaded_file:
        if uploaded_file.type.startswith('image'):
            image = Image.open(uploaded_file)
            st.image(image, caption="Documento subido", use_container_width=True)
            st.success("✅ Imagen cargada. Puede usarla como referencia visual.")
        else:
            st.success(f"✅ Archivo {uploaded_file.name} cargado")
            
# TAB 2: ALIMENTACIÓN
with tab2:
    st.header("🍽️ Registro de Alimentación")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Agregar Alimento")
        fecha_alimento = st.date_input("📅 Fecha", value=date.today())
        hora_alimento = st.time_input("⏰ Hora")
        comida = st.selectbox("🍴 Tipo de Comida", ["Desayuno", "Media Mañana", "Almuerzo", "Merienda", "Cena", "Otro"])
        alimento = st.text_input("🍎 Alimento/Plato")
        cantidad = st.text_input("📏 Cantidad", placeholder="Ej: 1 taza, 150g, 1 unidad")
        
        if st.button("➕ Agregar al Registro"):
            if alimento:
                nuevo_alimento = {
                    'fecha': fecha_alimento.strftime("%Y-%m-%d"),
                    'hora': hora_alimento.strftime("%H:%M"),
                    'comida': comida,
                    'alimento': alimento,
                    'cantidad': cantidad
                }
                st.session_state.registro_alimentos.append(nuevo_alimento)
                st.success(f"✅ {alimento} agregado al registro")
                st.rerun()
            else:
                st.warning("⚠️ Por favor ingrese el nombre del alimento")
    
    with col2:
        st.subheader("📝 Historial de Alimentos")
        
        if st.session_state.registro_alimentos:
            # Agrupar por fecha
            registros_por_fecha = {}
            for reg in st.session_state.registro_alimentos:
                fecha = reg['fecha']
                if fecha not in registros_por_fecha:
                    registros_por_fecha[fecha] = []
                registros_por_fecha[fecha].append(reg)
            
            # Mostrar por fecha (más reciente primero)
            for fecha in sorted(registros_por_fecha.keys(), reverse=True):
                with st.expander(f"📅 {fecha}", expanded=(fecha == date.today().strftime("%Y-%m-%d"))):
                    registros_dia = registros_por_fecha[fecha]
                    for i, reg in enumerate(registros_dia):
                        col_a, col_b, col_c = st.columns([2, 3, 1])
                        with col_a:
                            st.write(f"**{reg['hora']} - {reg['comida']}**")
                        with col_b:
                            st.write(f"{reg['alimento']} ({reg['cantidad']})")
                        with col_c:
                            if st.button("🗑️", key=f"del_alim_{i}_{fecha}"):
                                st.session_state.registro_alimentos.remove(reg)
                                st.rerun()
        else:
            st.info("🍽️ No hay alimentos registrados aún. Agregue su primer alimento.")

# TAB 3: ACTIVIDAD FÍSICA
with tab3:
    st.header("🏋️ Registro de Actividad Física")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Agregar Actividad")
        fecha_act = st.date_input("📅 Fecha", value=date.today(), key="fecha_act")
        tipo_act = st.selectbox(
            "🏋️ Tipo de Actividad",
            ["Caminata", "Correr", "Ciclismo", "Natación", "Gimnasio", "Yoga", "Deporte en equipo", "Otro"]
        )
        duracion = st.number_input("⏱️ Duración (minutos)", min_value=1, max_value=300, value=30)
        intensidad = st.select_slider(
            "💥 Intensidad",
            options=["Ligera", "Moderada", "Intensa", "Muy Intensa"]
        )
        notas_act = st.text_area("📝 Notas", placeholder="Ej: Me sentí bien, tuve dolor en rodilla...")
        
        if st.button("➕ Agregar Actividad"):
            nueva_actividad = {
                'fecha': fecha_act.strftime("%Y-%m-%d"),
                'tipo': tipo_act,
                'duracion': duracion,
                'intensidad': intensidad,
                'notas': notas_act
            }
            st.session_state.registro_actividad.append(nueva_actividad)
            st.success(f"✅ Actividad agregada: {tipo_act} - {duracion} min")
            st.rerun()
    
    with col2:
        st.subheader("📊 Historial de Actividad")
        
        if st.session_state.registro_actividad:
            # Calcular estadísticas
            total_min = sum([act['duracion'] for act in st.session_state.registro_actividad])
            total_sesiones = len(st.session_state.registro_actividad)
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("🔥 Total Sesiones", total_sesiones)
            with col_stat2:
                st.metric("⏱️ Total Minutos", total_min)
            with col_stat3:
                promedio = total_min // total_sesiones if total_sesiones > 0 else 0
                st.metric("📊 Promedio/Sesión", f"{promedio} min")
            
            st.markdown("---")
            
            # Mostrar actividades
            for i, act in enumerate(reversed(st.session_state.registro_actividad)):
                with st.expander(f"🏋️ {act['fecha']} - {act['tipo']}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Duración:** {act['duracion']} minutos")
                        st.write(f"**Intensidad:** {act['intensidad']}")
                    with col_b:
                        if act['notas']:
                            st.write(f"**Notas:** {act['notas']}")
                    if st.button("🗑️ Eliminar", key=f"del_act_{i}"):
                        st.session_state.registro_actividad.remove(act)
                        st.rerun()
        else:
            st.info("🏋️ No hay actividades registradas. ¡Comience a registrar su actividad física!")

# TAB 4: MEDICACIÓN
with tab4:
    st.header("💊 Medicación Actual")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Agregar Medicamento")
        medicamento_nombre = st.text_input("💊 Nombre del Medicamento")
        dosis = st.text_input("📏 Dosis", placeholder="Ej: 500mg, 1 comprimido")
        frecuencia = st.text_input("⏰ Frecuencia", placeholder="Ej: 2 veces al día, cada 12h")
        motivo = st.text_input("🎯 Motivo", placeholder="Para qué se toma")
        
        if st.button("➕ Agregar Medicamento"):
            if medicamento_nombre:
                nuevo_med = {
                    'nombre': medicamento_nombre,
                    'dosis': dosis,
                    'frecuencia': frecuencia,
                    'motivo': motivo
                }
                if 'medicacion' not in st.session_state.paciente:
                    st.session_state.paciente['medicacion'] = []
                st.session_state.paciente['medicacion'].append(nuevo_med)
                st.success(f"✅ {medicamento_nombre} agregado")
                
                # Buscar en CIMA AEMPS
                with st.spinner("Buscando en CIMA AEMPS..."):
                    resultado_cima = buscar_cima_aemps(medicamento_nombre)
                    if resultado_cima:
                        st.info("📊 Información encontrada en CIMA AEMPS")
                        st.caption("Puede consultar más detalles en https://cima.aemps.es")
                
                st.rerun()
            else:
                st.warning("⚠️ Ingrese el nombre del medicamento")
    
    with col2:
        st.subheader("📝 Medicación Actual")
        
        if st.session_state.paciente.get('medicacion'):
            for i, med in enumerate(st.session_state.paciente['medicacion']):
                with st.expander(f"💊 {med['nombre']}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Dosis:** {med['dosis']}")
                        st.write(f"**Frecuencia:** {med['frecuencia']}")
                    with col_b:
                        if med['motivo']:
                            st.write(f"**Motivo:** {med['motivo']}")
                    if st.button("🗑️ Eliminar", key=f"del_med_{i}"):
                        st.session_state.paciente['medicacion'].remove(med)
                        st.rerun()
        else:
            st.info("💊 No hay medicamentos registrados.")
            
# TAB 5: DIAGNÓSTICO NUTRICIONAL
with tab5:
    st.header("🩺 Diagnóstico Nutricional")
    
    if not st.session_state.paciente['nombre']:
        st.warning("⚠️ Complete primero el perfil del paciente en la pestaña 'Perfil'")
    else:
                if st.button("🔍 Generar Diagnóstico"):
                        with st.spinner('Analizando información del paciente...'):
                                                # Preparar contexto del paciente
                                                                contexto = f"""\nPACIENTE:\n- Nombre: {st.session_state.paciente['nombre']}\n- Edad: {st.session_state.paciente['edad']} años\n- Peso: {st.session_state.paciente.get('peso', 'N/A')} kg\n- Altura: {st.session_state.paciente.get('altura', 'N/A')} cm\n- Medicamentos: {', '.join(st.session_state.paciente.get('medicamentos', []))}\n\nSOLICITUD: Como farmacéutico nutricionista, realiza un diagnóstico nutricional completo basado en:
                                {contexto}
                                Incluye: 1) Valoración nutricional 2) Problemas detectados 3) Barreras potenciales 4) Recomendaciones generales (sin dietas específicas)
                                """
                                prompt = f"""Como farmacéutico nutricionista, realiza un diagnóstico nutricional completo basado en:
                                {contexto}
                                Incluye: 1) Valoración nutricional 2) Problemas detectados 3) Barreras potenciales 4) Recomendaciones generales (sin dietas específicas)"""
                                respuesta = consultar_gemini(prompt, contexto)
                                st.session_state.diagnostico = respuesta
st.success("✅ Diagnóstico generado")
        
                if st.session_state.diagnostico:
                        st.markdown("### 📊 Diagnóstico")
                        st.markdown(st.session_state.diagnostico)

# TAB 6: COACHING NUTRICIONAL
with tab6:
    st.header("🧠 Coaching Nutricional")
    
    if not st.session_state.paciente['nombre']:
        st.warning("⚠️ Complete primero el perfil del paciente")
    else:
        st.subheader("💬 Generador de Preguntas de Coaching")
        st.info("💡 Estas preguntas le ayudarán a guiar una consulta nutricional efectiva")
        
        if st.button("✨ Generar Preguntas de Coaching"):
            with st.spinner('Generando preguntas personalizadas...'):
                prompt = f"""Como coach nutricional, genera 10 preguntas abiertas y efectivas para:
- Evaluar hábitos alimentarios
- Identificar barreras y motivaciones
- Explorar conocimientos nutricionales
- Entender contexto sociocultural
Paciente: {st.session_state.paciente['nombre']}, {st.session_state.paciente['edad']} años, Objetivo: {st.session_state.paciente['objetivo']}"""
                respuesta = consultar_gemini(prompt, json.dumps(st.session_state.paciente, indent=2))
                st.markdown(respuesta)
        
        st.markdown("---")
        st.subheader("🎯 Recomendaciones Basadas en Guías")
        
        if st.button("📖 Generar Recomendaciones"):
            with st.spinner('Consultando guías nutricionales...'):
                prompt = f"""Basado en las guías nutricionales españolas y la pirámide alimentaria, proporciona recomendaciones específicas (NO dietas estrictas) para:
Paciente: {st.session_state.paciente}

Incluye:
1. Sugerencias de cambios alimentarios según pirámide nutricional
2. Frecuencia de consumo de grupos de alimentos
3. Suplementos nutricionales si necesarios
4. Hábitos saludables
5. Referencias a Medynut.com para recetas saludables"""
                respuesta = consultar_gemini(prompt, json.dumps(st.session_state.paciente, indent=2))
                st.markdown(respuesta)

# Pie de página
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer1:
    st.caption("💻 **NutriFarma Advisor Pro v2.0**")
with col_footer2:
    st.caption("🔒 Datos seguros - No se almacenan")
with col_footer3:
    st.caption("📞 Actualización: " + datetime.now().strftime("%Y-%m-%d"))
        

