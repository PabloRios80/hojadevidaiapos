import streamlit as st
from datetime import datetime
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build  # Importación añadida
from googleapiclient.http import MediaIoBaseUpload  # Importación añadida
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de Google Sheets y Drive
creds_info = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
}

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_info, scopes=scope)
client = gspread.authorize(creds)

try:
    sheet_pacientes = client.open("HistorialesMedicos").worksheet("Pacientes")
    sheet_resultados = client.open("HistorialesMedicos").worksheet("Resultados")
except gspread.exceptions.SpreadsheetNotFound:
    st.error("No se encontró la hoja de cálculo. Verifica el nombre y los permisos.")
    st.stop()
    
def calcular_imc(peso, altura):
    if altura == 0:
        return 0, ("Error", "", "red")
    imc = peso / ((altura/100) ** 2)
    
    categorias = [
        (18.5, "Bajo peso", "🟦", "blue"),
        (25, "Peso normal", "🟩", "green"),
        (30, "Sobrepeso", "🟨", "orange"),
        (35, "Obesidad Grado I", "🟥", "red"),
        (40, "Obesidad Grado II", "🔥", "red"),
        (float('inf'), "Obesidad Grado III", "💀", "red")
    ]
    
    for limite, cat, icono, color in categorias:
        if imc < limite:
            return imc, (cat, icono, color)
        
        
# Función para obtener intervenciones
def obtener_intervenciones(datos_personales, respuestas_medicas):
    try:
        sheet = client.open("HistorialesMedicos").worksheet("Intervenciones")
        registros = sheet.get_all_records()
        
        intervenciones = []
        for registro in registros:
            if evaluar_criterios(registro['CRITERIO_APLICACION'], datos_personales, respuestas_medicas):
                intervenciones.append({
                    'nombre': registro['INTERVENCIÓN'],
                    'categoria': registro['CATEGORIA'],
                    'explicacion': registro['INFORMACION_RESPUESTA'],
                    'tipo_estudio': registro['INTERVENCIÓN']
                })
        return intervenciones
    except Exception as e:
        st.error(f"Error cargando intervenciones: {str(e)}")
        return []

# Función para evaluar criterios
def evaluar_criterios(criterio_str, datos, respuestas):
    try:
        # Variables disponibles
        edad = respuestas.get('edad', 0)
        sexo = datos.get('Sexo_Biologico', '')
        condiciones = respuestas.get('condiciones', {})
        
        # Mapeo de variables
        variables = {
            'edad': edad,
            'sexo': f"'{sexo}'",
            'IMC': respuestas.get('imc_val', 0),
            'fumador': f"'{condiciones.get('fumador', 'No')}'",
            'antecedentes_mama': f"'{condiciones.get('antecedentes_mama', 'No')}'",
            'diabetes': f"'{condiciones.get('diabetes', 'No')}'",
            'hipertension': f"'{condiciones.get('hipertension', 'No')}'"
        }
        
        # Reemplazar variables en el criterio
        criterio_eval = criterio_str
        for var, valor in variables.items():
            criterio_eval = criterio_eval.replace(var, str(valor))
        
        return eval(criterio_eval)
    except Exception as e:
        st.error(f"Error evaluando criterio: {criterio_str} - {str(e)}")
        return False
    #Función para mostrar recomendaciones
def mostrar_recomendaciones():
    datos = st.session_state.datos_personales
    respuestas = st.session_state.respuestas_medicas
    intervenciones = obtener_intervenciones(datos, respuestas)
    
    st.markdown(f"""
    ## {datos['Nombre']}, estas son tus recomendaciones preventivas 💡
    *Basadas en tu perfil de {respuestas['edad']} años y tus respuestas*
    """)
    
    # Agrupar por categoría
    categorias = sorted(set([i['categoria'] for i in intervenciones]), 
                    key=lambda x: ['Cáncer', 'Cardiovascular', 'Vacunas', 'Consejerías'].index(x) 
                    if x in ['Cáncer', 'Cardiovascular', 'Vacunas', 'Consejerías'] else 4)
    
    for categoria in categorias:
        with st.expander(f"### {categoria} ({len([i for i in intervenciones if i['categoria'] == categoria])})", 
                        expanded=True):
            for interv in [i for i in intervenciones if i['categoria'] == categoria]:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
                        **{interv['nombre']}**  
                        🩺 {interv['explicacion'][:120]}...
                        """)
                    with col2:
                        instituciones = obtener_instituciones(interv['tipo_estudio'])
                        if instituciones:
                            with st.popup("🏥 Centros disponibles"):
                                for inst in instituciones:
                                    st.write(f"- {inst}")
                            st.button("Sacar turno", key=f"turno_{interv['nombre']}")
                    st.divider()
    
    # Tabla resumen
    if intervenciones:
        st.subheader("📋 Resumen completo")
        df = pd.DataFrame([{
            'Recomendación': i['nombre'],
            'Categoría': i['categoria'],
            'Acciones': f"[Más info](#) | [Sacar turno](#)"
        } for i in intervenciones])
        
        st.markdown(df.style.hide(axis="index").to_html(), unsafe_allow_html=True)
    else:
        st.success("🎉 ¡Excelente! No hay recomendaciones urgentes en este momento")

# Función para obtener instituciones
def obtener_instituciones(tipo_estudio):
    try:
        sheet = client.open("HistorialesMedicos").worksheet("Configuraciones")
        registros = sheet.get_all_records()
        return [row['Instituciones'] for row in registros if row['TiposEstudios'] == tipo_estudio]
    except Exception as e:
        st.error(f"Error obteniendo instituciones: {str(e)}")
        return []


def verificar_dni_existente(dni):
    try:
        registros = sheet_pacientes.get_all_records()
        return any(str(paciente['DNI']) == str(dni) for paciente in registros)
    except Exception as e:
        st.error(f"Error al acceder a la base de datos: {e}")
        return False

def cargar_resultados():
    st.header("📤 Cargar Resultados de Estudios")
    
    if 'datos_personales' not in st.session_state or 'DNI' not in st.session_state.datos_personales:
        st.warning("Complete el registro del paciente primero.")
        return
    
    datos = st.session_state.datos_personales
    dni = datos['DNI']
    
    try:
        sheet_config = client.open("HistorialesMedicos").worksheet("Configuraciones")
        instituciones = sheet_config.col_values(1)[1:]
        tipos_estudio = sheet_config.col_values(2)[1:]
    except Exception as e:
        st.error(f"Error cargando configuraciones: {str(e)}")
        return
    
    with st.form(f"form_resultados_{dni}"):
        profesional = st.text_input("Nombre del Profesional*")
        institucion = st.selectbox("Institución*", instituciones)
        fecha_estudio = st.date_input("Fecha del Estudio*")
        tipo_estudio = st.selectbox("Tipo de Estudio*", tipos_estudio)
        archivo = st.file_uploader("Subir Archivo (PDF)*", type="pdf")
        comentarios = st.text_area("Comentarios Adicionales")
        
        if st.form_submit_button("Guardar Resultado"):
            if not all([profesional, institucion, tipo_estudio, archivo]):
                st.error("Complete todos los campos obligatorios")
            else:
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    
                    file_metadata = {
                        'name': f"{dni}_{tipo_estudio}_{fecha_estudio}.pdf",
                        'parents': [os.getenv("DRIVE_FOLDER_ID")]
                    }
                    media = MediaIoBaseUpload(archivo, 
                                        mimetype='application/pdf',
                                        resumable=True)
                    
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    
                    enlace_archivo = f"https://drive.google.com/file/d/{uploaded_file['id']}/preview"
                    
                    sheet_resultados.append_row([
                        dni,
                        profesional,
                        institucion,
                        fecha_estudio.strftime("%Y-%m-%d"),
                        tipo_estudio,
                        enlace_archivo,
                        comentarios
                    ])
                    
                    st.success("Resultado guardado exitosamente!")
                    st.session_state.mostrar_formulario_resultados = False
                except Exception as e:
                    st.error(f"Error guardando resultado: {str(e)}")

    if st.session_state.mostrar_formulario_resultados:
        if st.button("← Volver a recomendaciones personales", key="volver_recomendaciones"):
            st.session_state.mostrar_formulario_resultados = False
            st.rerun()

def update_record(sheet, row, datos_medicos):
    try:
        column_map = {
            'Edad': 'J',
            'Peso': 'K',
            'Altura': 'L',
            'IMC_val': 'M',
            'IMC_cat': 'N',
            'Hipertension': 'O',
            'Diabetes': 'P',
            'Colesterol': 'Q',
            'Sedentarismo': 'R',
            'Tiempo_sentado': 'S',
            'Fumador': 'T',
            'Alcohol_drogas': 'U',
            'Violencia_familiar': 'V',
            'Depresion': 'W',
            'Antecedentes_colon': 'X',
            'Antecedentes_mama': 'Y',
            'Antecedentes_cuello_utero': 'Z',
            'Otro_cancer': 'AA',
            'Otra_condicion': 'AB',
            'Fumador_20_anios': 'AC',
            'Embarazo_planeado': 'AD'
        }
        
        values = [str(datos_medicos.get(col, "")) for col in column_map.keys()]
        
        sheet.update(
            values=[values],
            range_name=f"J{row}:AD{row}",
            value_input_option="USER_ENTERED"
        )
        return True
    except Exception as e:
        st.error(f"Error actualizando registro: {str(e)}")
        return False

def find_dni_row(sheet, dni):
    """Busca DNI ignorando formatos y espacios"""
    try:
        records = sheet.get_all_records()
        for idx, record in enumerate(records, start=2):
            # Normalizar ambos DNIs (eliminar espacios y caracteres no numéricos)
            sheet_dni = str(record.get('DNI', '')).strip().replace(' ', '').replace('-', '')
            input_dni = str(dni).strip().replace(' ', '').replace('-', '')
            
            if sheet_dni == input_dni:
                return idx
        return None
    except Exception as e:
        st.error(f"Error buscando DNI: {str(e)}")
        return None
    
def update_record(sheet, row, datos_medicos):
    """Actualiza los datos médicos en la fila especificada"""
    try:
        # Mapeo de columnas CORREGIDO (nombres exactos)
        column_map = {
            'Edad': 'J',
            'Peso': 'K',
            'Altura': 'L',
            'IMC_val': 'M',
            'IMC_cat': 'N',
            'Hipertension': 'O',
            'Diabetes': 'P',
            'Colesterol': 'Q',
            'Sedentarismo': 'R',
            'Tiempo_sentado': 'S',
            'Fumador': 'T',
            'Alcohol_drogas': 'U',
            'Violencia_familiar': 'V',
            'Depresion': 'W',
            'Antecedentes_colon': 'X',
            'Antecedentes_mama': 'Y',
            'Antecedentes_cuello_utero': 'Z',  # Guión bajo
            'Otro_cancer': 'AA',
            'Otra_condicion': 'AB',
            'Fumador_20_anios': 'AC',
            'Embarazo_planeado': 'AD'
        }
    
        # Crear lista de valores en el orden correcto
        values = [str(datos_medicos.get(col, "")) for col in column_map.keys()]
        
        # Actualizar usando nueva sintaxis (values first)
        sheet.update(
            values=[values],  # Lista 2D requerida
            range_name=f"J{row}:AD{row}",  # Rango actualizado
            value_input_option="USER_ENTERED"
        )
        return True
        
    except Exception as e:
        st.error(f"Error actualizando registro: {str(e)}")
        return False
    
    
def mostrar_presentacion():
    st.title("Bienvenida/o y Felicitaciones")
    st.write("""
    Bienvenida/o y Felicitaciones por decidirse a hacer el Día Preventivo. 
    Esto es un programa de IAPOS la Obra Social de los empleados públicos de la Provincia de Santa Fe. 
    Este programa es TOTALMENTE sin costo alguno para los afiliados, se repite todos los años y consiste básicamente en explorar juntos las amenazas a su salud. 
    Va a conocer a nuestros equipos y lo vamos a ayudar a detectar o prevenir más de 30 potenciales peligros actuales o futuros de su salud o de su familia.
    """)
    
    # Nuevo botón para acceso directo
    if st.button("Vea sus pagina personal del Dia Preventivo", 
                use_container_width=True, 
                type="primary"):
        st.session_state.paso_actual = 7  # Nuevo paso para la página personal
        st.rerun()
    
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Afiliados para hacer el Día Preventivo"):
            st.session_state.paso_actual = 1
            st.rerun()
    with col2:
        if st.button("Profesionales"):
            st.session_state.paso_actual = 5  # Asumiendo que el paso 5 es para profesionales
            st.rerun()
    with col3:
        if st.button("Prestadores"):
            st.session_state.paso_actual = 6  # Asumiendo que el paso 6 es para prestadores
            st.rerun()
            
def buscar_paciente_por_dni(dni):
    """Busca un paciente por DNI y devuelve sus datos médicos"""
    try:
        registros = sheet_pacientes.get_all_records()
        for paciente in registros:
            if str(paciente['DNI']) == str(dni):
                return paciente
        return None
    except Exception as e:
        st.error(f"Error al buscar paciente: {e}")
        return None

def pagina_profesionales():
    st.header("👩‍⚕️ Página para Profesionales")
    
    # Buscar paciente por DNI
    dni = st.text_input("Ingrese el DNI del paciente para buscar su historial", max_chars=8, key="input_dni").strip()
    
    if st.button("Buscar Paciente", key="buscar_paciente_button"):
        if not dni.isdigit() or len(dni) != 8:
            st.error("DNI inválido. Debe tener 8 dígitos sin puntos.")
        else:
            paciente = buscar_paciente_por_dni(dni)
            if paciente:
                st.success("Paciente encontrado.")
                st.subheader(f"Resumen médico de {paciente.get('Nombre', '')}")
                                
                # Guardar el DNI en el estado de sesión para usarlo en otros botones
                st.session_state.dni_paciente = dni
            else:
                st.error("No se encontró un paciente con ese DNI.")
    
    # Botón para "Hacer Formulario de Cierre"
    if st.button("Hacer Formulario de Cierre", key="formulario_cierre_button"):
        st.write("Formulario de cierre (en desarrollo).")
    
    # Botón para "Ver Resultados"
    if st.button("Ver Resultados", key="ver_resultados_button"):
        if 'dni_paciente' not in st.session_state:
            st.warning("Primero busque un paciente por DNI.")
        else:
            resultados = buscar_resultados_paciente(st.session_state.dni_paciente)
            if resultados:
                st.subheader("Resultados del paciente")
                for resultado in resultados:
                    st.write(f"**Profesional:** {resultado['profesional']}")
                    st.write(f"**Institución:** {resultado['institucion']}")
                    st.write(f"**Fecha del estudio:** {resultado['fecha_estudio']}")
                    st.write(f"**Tipo de estudio:** {resultado['tipo_estudio']}")
                    st.write(f"**Archivo:** [Abrir PDF]({resultado['archivo']})")  # Mostrar enlace al PDF
                    st.write(f"**Comentarios:** {resultado['comentarios']}")
                    st.write("---")
            else:
                st.warning("No se encontraron resultados para este paciente.")                
def buscar_resultados_paciente(dni):
    """Busca los resultados del paciente en la hoja Resultados"""
    try:
        registros = sheet_resultados.get_all_records()
        resultados = []
        for registro in registros:
            if str(registro['DNI']) == str(dni):  # Buscar por DNI
                resultados.append({
                    'profesional': registro.get('Profesional', ''),
                    'institucion': registro.get('Institucion', ''),
                    'fecha_estudio': registro.get('Fecha_Estudio', ''),
                    'tipo_estudio': registro.get('Tipo_Estudio', ''),
                    'archivo': registro.get('Archivo', ''),
                    'comentarios': registro.get('Comentarios', '')
                })
        return resultados
    except Exception as e:
        st.error(f"Error al buscar resultados: {e}")
        return []
def pagina_personal():
    st.header("📋 Página Personal del Día Preventivo")
    
    if st.button("← Volver al inicio"):
        st.session_state.paso_actual = 0
        st.rerun()
    
    dni = st.text_input("Ingrese su DNI para ver sus recomendaciones", 
                       max_chars=8, 
                       help="El mismo DNI que usó para registrarse").strip()
    
    if st.button("Buscar recomendaciones", type="primary"):
        if not dni.isdigit() or len(dni) != 8:
            st.error("DNI inválido. Debe tener 8 dígitos sin puntos.")
        else:
            paciente = buscar_paciente_por_dni(dni)
            if paciente:
                # Obtener datos necesarios para las intervenciones
                datos_personales = {
                    'Sexo_Biologico': paciente.get('Sexo_Biologico', ''),
                    'Nombre': paciente.get('Nombre', ''),
                    'Apellido': paciente.get('Apellido', '')
                }
                
                respuestas_medicas = {
                    'edad': paciente.get('Edad', 0),
                    'imc_val': float(paciente.get('IMC_val', 0)),
                    'condiciones': {
                        'hipertension': paciente.get('Hipertension', 'No'),
                        'diabetes': paciente.get('Diabetes', 'No'),
                        'colesterol': paciente.get('Colesterol', 'No'),
                        'sedentarismo': paciente.get('Sedentarismo', 'No'),
                        'tiempo_sentado': paciente.get('Tiempo_sentado', 'No'),
                        'fumador': paciente.get('Fumador', 'No'),
                        'fumador_20_anios': paciente.get('Fumador_20_anios', 'No'),
                        'antecedentes_mama': paciente.get('Antecedentes_mama', 'No')
                    }
                }
                
                # Obtener intervenciones y mostrar recomendaciones
                intervenciones = obtener_intervenciones(datos_personales, respuestas_medicas)
                
                st.markdown(f"""
                ## {datos_personales['Nombre']}, estas son tus recomendaciones preventivas actualizadas 💡
                *Basadas en tu último registro de {datetime.now().strftime('%d/%m/%Y')}*
                """)
                
                # Mostrar recomendaciones en expansores
                categorias = sorted(set([i['categoria'] for i in intervenciones]), 
                                key=lambda x: ['Cáncer', 'Cardiovascular', 'Vacunas', 'Consejerías'].index(x) 
                                if x in ['Cáncer', 'Cardiovascular', 'Vacunas', 'Consejerías'] else 4)
                
                for categoria in categorias:
                    with st.expander(f"### {categoria} ({len([i for i in intervenciones if i['categoria'] == categoria])})", 
                                expanded=True):
                        for interv in [i for i in intervenciones if i['categoria'] == categoria]:
                            with st.container():
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.markdown(f"""
                                    **{interv['nombre']}**  
                                    🩺 {interv['explicacion'][:120]}...
                                    """)
                                with col2:
                                    instituciones = obtener_instituciones(interv['tipo_estudio'])
                                    if instituciones:
                                        with st.popup("🏥 Centros disponibles"):
                                            for inst in instituciones:
                                                st.write(f"- {inst}")
                                        st.button("Sacar turno", key=f"turno_{interv['nombre']}_{dni}")
                                st.divider()
                
                # Tabla resumen (igual que en mostrar_recomendaciones)
                if intervenciones:
                    st.subheader("📋 Resumen completo")
                    df = pd.DataFrame([{
                        'Recomendación': i['nombre'],
                        'Categoría': i['categoria'],
                        'Acciones': f"[Más info](#) | [Sacar turno](#)"
                    } for i in intervenciones])
                    
                    st.markdown(df.style.hide(axis="index").to_html(), unsafe_allow_html=True)
                else:
                    st.success("🎉 ¡Excelente! No hay recomendaciones urgentes en este momento")
                
                # Mostrar resultados igual que en profesionales
                resultados = buscar_resultados_paciente(dni)
                if resultados:
                    st.subheader("📁 Tus resultados cargados")
                    for resultado in resultados:
                        st.write(f"**Fecha del estudio:** {resultado['fecha_estudio']}")
                        st.write(f"**Tipo de estudio:** {resultado['tipo_estudio']}")
                        st.write(f"**Institución:** {resultado['institucion']}")
                        st.markdown(f"**Archivo:** [Abrir PDF]({resultado['archivo']})")
                        if resultado['comentarios']:
                            st.write(f"**Comentarios:** {resultado['comentarios']}")
                        st.write("---")
                else:
                    st.info("ℹ️ No se encontraron resultados cargados para tu DNI")

            else:
                st.error("No se encontró un registro con este DNI. ¿Ya completó su formulario preventivo?")
def main():
    if 'paso_actual' not in st.session_state:
        st.session_state.paso_actual = 0  # Cambiado a 0 para mostrar presentación inicial
        st.session_state.datos_personales = {}
        st.session_state.respuestas_medicas = {}
    
    # Manejar los diferentes pasos
    if st.session_state.paso_actual == 0:
        mostrar_presentacion()
    elif st.session_state.paso_actual == 5:
        pagina_profesionales()
    elif st.session_state.paso_actual == 7:  # Nuevo caso para página personal
        pagina_personal()
    else:
        st.title("Sistema Integrado de Salud")
    
    # Inicializar el estado de sesión si no existe
    if 'mostrar_formulario_resultados' not in st.session_state:
        st.session_state.mostrar_formulario_resultados = False
        
    if 'paso_actual' not in st.session_state:
        st.session_state.update({
            'paso_actual': 1,
            'datos_personales': {},
            'respuestas_medicas': {}
        })
    
    # Paso 1: Registro del paciente
    if st.session_state.paso_actual == 1:
        with st.form("form_registro"):
            st.header("📝 Registro del Paciente")
            
            col_dni, col_fecha = st.columns(2)
            with col_dni:
                dni = st.text_input("DNI* (8 dígitos sin puntos)", max_chars=8).strip()
            with col_fecha:
                fecha_nacimiento = st.date_input(
                    "Fecha de Nacimiento*",
                    min_value=datetime(1900, 1, 1),
                    max_value=datetime.today()
                )
            
            col_nombre, col_apellido = st.columns(2)
            with col_nombre:
                nombre = st.text_input("Nombre*").strip().title()
            with col_apellido:
                apellido = st.text_input("Apellido").strip().title()
            
            col_sexo, col_genero = st.columns(2)
            with col_sexo:
                sexo_biologico = st.selectbox(
                    "Sexo biológico al nacer*",
                    options=["Masculino", "Femenino"]
                )
            with col_genero:
                genero_autopercibido = st.selectbox(
                    "Género autopercibido",
                    options=["Mujer", "Hombre", "No binario", "Otro", "Prefiero no responder"]
                )
            
            email = st.text_input("Correo Electrónico*").strip().lower()
            telefono = st.text_input("Teléfono (Ej: +5491112345678)").strip()
            
            if st.form_submit_button("Registrar Paciente"):
                if not dni.isdigit() or len(dni) != 8:
                    st.error("DNI inválido. Debe tener 8 dígitos sin puntos")
                elif verificar_dni_existente(dni):
                    st.error("Este DNI ya está registrado")
                else:
                    datos = {
                        'DNI': dni,
                        'Nombre': nombre,
                        'Apellido': apellido,
                        'Fecha_Nacimiento': fecha_nacimiento.strftime("%Y-%m-%d"),
                        'Sexo_Biologico': sexo_biologico,
                        'Genero_Autopercibido': genero_autopercibido,
                        'Email': email,
                        'Telefono': telefono
                    }
                    try:
                        sheet_pacientes.append_row(list(datos.values()))
                        st.session_state.datos_personales = datos
                        st.session_state.paso_actual = 2
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar datos: {e}")

    # Paso 2: Cuestionario médico
    elif st.session_state.paso_actual == 2:
        if st.button("← Atrás"):
            st.session_state.paso_actual = 1
            st.rerun()
            
        with st.form("form_medico"):
            st.header("🔍 Cuestionario Médico")
            datos = st.session_state.datos_personales
            nombre_completo = f"{datos['Nombre']} {datos.get('Apellido', '')}".strip()
            
            fecha_nac = datetime.strptime(datos['Fecha_Nacimiento'], "%Y-%m-%d")
            edad = datetime.now().year - fecha_nac.year
            
            st.subheader("Índice de Masa Corporal (IMC)")
            col_peso, col_altura = st.columns(2)
            with col_peso:
                peso = st.number_input("Peso (kg)*", min_value=30.0, max_value=300.0, step=0.1)
            with col_altura:
                altura = st.number_input("Altura (cm)*", min_value=100, max_value=250, step=1)
            
            if peso > 0 and altura > 0:
                imc_val, (imc_cat, imc_icon, imc_color) = calcular_imc(peso, altura)
                st.markdown(
                    f"**Resultado IMC:** {imc_val:.1f} - {imc_icon} "
                    f"<span style='color:{imc_color};font-weight:bold;'>{imc_cat}</span>",
                    unsafe_allow_html=True
                )
            
            st.subheader(f"👩⚕️ {nombre_completo}, ¿cuál es tu situación actual?")
            
            condiciones = {
                'hipertension': st.radio("¿Tiene hipertensión arterial?", ["Sí", "No", "No lo sé"]),
                'diabetes': st.radio("¿Tiene diabetes?", ["Sí", "No", "No lo sé"]),
                'colesterol': st.radio("¿Tiene colesterol alto?", ["Sí", "No", "No lo sé"]),
                'sedentarismo': st.radio("¿Realiza poca actividad física?", ["Sí", "No"]),
                'tiempo_sentado': st.radio("¿Pasa >6h/día sentado?", ["Sí", "No"]),
                'fumador': st.radio("¿Es fumador/a?", ["Sí", "No"]),
                'alcohol_drogas': st.radio("¿Abusa de sustancias?", ["Sí", "No"]),
                'violencia_familiar': st.radio("¿Violencia familiar?", ["Sí", "No"]),
                'depresion': st.radio("¿Depresión?", ["Sí", "No"]),
                'antecedentes_colon': st.radio("Antecedentes cáncer colon", ["Sí", "No", "No lo sé"]),
                'antecedentes_mama': st.radio("Antecedentes cáncer mama", ["Sí", "No", "No lo sé"]),
                'antecedentes_cuello_utero': st.radio("Antecedentes cáncer cuello uterino", ["Sí", "No", "No lo sé"]),
                'otro_cancer': st.text_input("Otro cáncer (especificar)"),
                'otra_condicion': st.text_area("Otras condiciones relevantes")
            }
            
            if condiciones['fumador'] == "Sí":
                condiciones['fumador_20_anios'] = st.radio("¿Fuma hace +20 años?", ["Sí", "No", "No lo sé"])
            
            if datos['Sexo_Biologico'] == "Femenino":
                condiciones['embarazo_planeado'] = st.radio("¿Planifica embarazo?", ["Sí", "No", "No lo sé"])
            if st.form_submit_button("Continuar →"):
                if peso > 0 and altura > 0:
                    st.session_state.respuestas_medicas = {
                        'edad': edad,  # Clave crítica faltante
                        'imc_val': imc_val,
                        'imc_cat': imc_cat,
                        'condiciones': condiciones,
                        'peso': peso,
                        'altura': altura
                    }
        # CORRECCIÓN 1: Definir datos_medicos DENTRO del bloque condicional
                    datos_medicos = {
                        'Edad': edad,
                        'Peso': peso,
                        'Altura': altura,
                        'IMC_val': imc_val,
                        'IMC_cat': imc_cat.strip(),  # Eliminar espacios en blanco
                        'Hipertension': condiciones.get('hipertension', 'No'),  # Sin tilde
                        'Diabetes': condiciones.get('diabetes', 'No'),
                        'Colesterol': condiciones.get('colesterol', 'No'),
                        'Sedentarismo': condiciones.get('sedentarismo', 'No'),
                        'Tiempo_sentado': condiciones.get('tiempo_sentado', 'No'),
                        'Fumador': condiciones.get('fumador', 'No'),
                        'Alcohol_drogas': condiciones.get('alcohol_drogas', 'No'),
                        'Violencia_familiar': condiciones.get('violencia_familiar', 'No'),  # Con guión bajo
                        'Depresion': condiciones.get('depresion', 'No'),  # Sin tilde
                        'Antecedentes_colon': condiciones.get('antecedentes_colon', 'No'),
                        'Antecedentes_mama': condiciones.get('antecedentes_mama', 'No'),  # Sin tilde
                        'Antecedentes_cuello_utero': condiciones.get('antecedentes_cuello_utero', 'No'),
                        'Otro_cancer': condiciones.get('otro_cancer', 'No'),  # Sin tilde
                        'Otra_condicion': condiciones.get('otra_condicion', 'No'),
                        'Fumador_20_anios': condiciones.get('fumador_20_anios', 'No'),  # Sin tilde en "años"
                        'Embarazo_planeado': condiciones.get('embarazo_planeado', 'No')
                    }
                        
        # CORRECCIÓN 2: Todo este código DEBE estar DENTRO del if
                    dni = st.session_state.datos_personales['DNI']
                    st.write(f"DEBUG - Buscando DNI: {dni}")  # Para verificar en consola
                    row = find_dni_row(sheet_pacientes, dni)
                    if not row:
                        st.error("Error: Registro no encontrado. ¿Guardó correctamente el Paso 1?")
                    else:
                        st.write(f"DEBUG - Fila encontrada: {row}")  # Verificar fila correcta
                        if update_record(sheet_pacientes, row, datos_medicos):
                            st.session_state.paso_actual = 3
                            st.rerun()
                    
                    # Dentro del bloque st.form_submit_button("Continuar →"):
                    st.write("Datos a guardar:", datos_medicos)  # Debug visual
                    row = find_dni_row(sheet_pacientes, dni)
                if not row:
                    st.error("Error: Registro no encontrado")
                elif not update_record(sheet_pacientes, row, datos_medicos):
                    st.error("Error técnico al guardar. Intente nuevamente o contacte soporte")
        
                    if row:
                        if update_record(sheet_pacientes, row, datos_medicos):
                            st.session_state.paso_actual = 3
                            st.rerun()
                    else:
                        st.error("Error al guardar datos médicos")
                else:
                    st.error("No se encontró el registro del paciente")
            else:
                st.error("Complete todos los campos obligatorios")
        # Paso 3: Recomendaciones personalizadas
    elif st.session_state.paso_actual == 3:
        if st.button("← Volver al cuestionario"):
            st.session_state.paso_actual = 2
            st.rerun()
    
    # Mostrar nuevas recomendaciones
        mostrar_recomendaciones()  # <--- Nueva función
    
    # Botones adicionales
        col_botones = st.columns([1, 1, 1])
        with col_botones[1]:
            if st.button("🔄 Nueva evaluación"):
                st.session_state.clear()
                st.rerun()
        with col_botones[2]:
            if st.button("📄 Cargar Resultados de Estudios"):
                st.session_state.mostrar_formulario_resultados = True
                st.rerun()
    
    # Mostrar el formulario de carga de resultados si el estado es True
    if st.session_state.mostrar_formulario_resultados:
        cargar_resultados()
    elif st.session_state.paso_actual == 4:
        st.header("🩺 Recomendaciones para el Equipo de Salud")
        datos = {'sexo_biologico': st.session_state.datos_personales['Sexo_Biologico']}
        respuestas = st.session_state.respuestas_medicas
        # Botón para volver a recomendaciones personales
        if st.button("← Volver a recomendaciones personales", key="volver_recomendaciones_equipo"):
            st.session_state.paso_actual = 3
            st.rerun()    
            
        # Mostrar enlace a la página del paciente
        st.markdown("[Ver página del paciente](paginas_web/paciente.html)")

if __name__ == "__main__":
    if 'paso_actual' not in st.session_state:
        st.session_state.paso_actual = 0
        st.session_state.mostrar_formulario_resultados = False
        st.session_state.datos_personales = {}
        st.session_state.respuestas_medicas = {}
    
    main()
