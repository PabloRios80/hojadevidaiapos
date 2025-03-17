import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Crear credenciales desde las variables de entorno
creds_dict = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),  # Asegúrate de manejar los saltos de línea
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("UNIVERSE_DOMAIN")
}

# Crear credenciales
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Abrir las hojas de cálculo
try:
    sheet_pacientes = client.open("HistorialesMedicos").worksheet("Pacientes")
    sheet_resultados = client.open("HistorialesMedicos").worksheet("Resultados")
except gspread.exceptions.SpreadsheetNotFound:
    st.error("No se encontró la hoja de cálculo. Verifica el nombre y los permisos.")
    st.stop()
except Exception as e:
    st.error(f"Error al acceder a Google Sheets: {e}")
    st.stop()
def calcular_imc(peso, altura):
    """Calcula el IMC y devuelve categoría con estilo"""
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

def verificar_dni_existente(dni):
    """Verifica si el DNI ya existe en la base de datos"""
    try:
        registros = sheet_pacientes.get_all_records()
        for paciente in registros:
            if str(paciente['DNI']) == str(dni):
                return True
        return False
    except Exception as e:
        st.error(f"Error al acceder a la base de datos: {e}")
        return False
def generar_recomendaciones_paciente(nombre, condiciones, imc):
    """Genera recomendaciones personalizadas para el paciente"""
    recomendaciones = []
    
    if imc >= 30:
        recomendaciones.append(f"📉 **Control de peso:** {nombre}, tu IMC indica que podrías beneficiarte con un plan de manejo de peso")
    elif imc >= 25:
        recomendaciones.append(f"⚖️ **Peso saludable:** {nombre}, te recomendamos mantener un balance nutricional")
    
    if condiciones.get('hipertension', 'No') == "Sí":
        recomendaciones.append("❤️ **Presión arterial:** Control médico regular y reducción de sodio en la dieta")
    
    if condiciones.get('diabetes', 'No') == "Sí":
        recomendaciones.append("🩸 **Glucosa en sangre:** Monitoreo periódico y plan alimentario personalizado")
    
    if condiciones.get('colesterol', 'No') == "Sí":
        recomendaciones.append("🧪 **Colesterol:** Perfil lipídico anual y reducción de grasas saturadas")
    
    if condiciones.get('sedentarismo', 'No') == "Sí":
        recomendaciones.append("🏃 **Actividad física:** Iniciar con 30 minutos diarios de caminata")
    
    if condiciones.get('tiempo_sentado', 'No') == "Sí":
        recomendaciones.append("🪑 **Postura y movimiento:** Pausas activas cada 45 minutos")
    
    if condiciones.get('fumador', 'No') == "Sí":
        recomendaciones.append("🚭 **Dejar de fumar:** Te recomendamos buscar ayuda profesional para dejar el tabaco")
        if condiciones.get('fumador_20_anios', 'No') == "Sí":
            recomendaciones.append("⚠️ **Fumador crónico:** Es importante realizar estudios de detección temprana de enfermedades pulmonares")
    
    if condiciones.get('embarazo_planeado', 'No') == "Sí":  # <--- Corrección aplicada
        recomendaciones.append("🤰 **Ácido fólico:** Si planeas embarazo, comienza con suplementos de ácido fólico")
    
    return recomendaciones

def generar_recomendaciones_equipo_salud(datos, respuestas):
    """Genera recomendaciones para el equipo de salud"""
    recomendaciones = []
    
    if datos['sexo_biologico'] == "Femenino":
        if respuestas['edad'] >= 50:
            recomendaciones.append("🩺 **Prevención de cáncer de mama:** Solicitar mamografía bilateral")
            if respuestas['condiciones']['antecedentes_mama'] == "Sí":
                recomendaciones.append("🩺 **Prevención de cáncer de mama (antecedentes):** Indicar ecografía mamaria + mamografía bilateral a partir de los 40 años")
    
    if respuestas['edad'] >= 50:
        recomendaciones.append("🩺 **Prevención de cáncer colorrectal:** Indicar sangre oculta en materia fecal y/o videocolonoscopia")
    
    if datos['sexo_biologico'] == "Femenino" and respuestas['edad'] >= 18:
        recomendaciones.append("🩺 **Prevención de cáncer de cuello uterino:** Indicar test de HPV")
    
    if respuestas['edad'] >= 18:
        recomendaciones.append("🩺 **Prevención cardiovascular:** Tomar presión arterial en ambos brazos, medir peso y altura, indicar colesterol total y HDL")
    
    return recomendaciones
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

def main():
    st.title("Sistema Integrado de Salud")
    
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

    # Paso 3: Recomendaciones paciente
    elif st.session_state.paso_actual == 3:
        st.header("📋 Recomendaciones Personalizadas")
        datos = st.session_state.datos_personales
        respuestas = st.session_state.respuestas_medicas
        nombre_completo = f"{datos['Nombre']} {datos.get('Apellido', '')}".strip()
        
        st.subheader(f"👤 Resumen de {nombre_completo}")
        st.markdown(f"""
        - **Edad:** {respuestas['edad']} años
        - **IMC:** {respuestas['imc_val']:.1f} ({respuestas['imc_cat']})
        - **Contacto:** {datos['Email']} | {datos['Telefono']}
        """)
        
        st.subheader("🩺 Recomendaciones Preventivas")
        recomendaciones = generar_recomendaciones_paciente(
            nombre_completo, 
            respuestas['condiciones'],
            respuestas['imc_val']
        )
        
        for rec in recomendaciones:
            if "Obesidad" in rec or "🔥" in rec:
                st.error(rec)
            elif "Sobrepeso" in rec:
                st.warning(rec)
            else:
                st.success(rec)
        
        col_botones = st.columns([1, 1, 1])
        with col_botones[0]:
            if st.button("← Volver al cuestionario"):
                st.session_state.paso_actual = 2
                st.rerun()
        with col_botones[1]:
            if st.button("🔄 Nueva evaluación"):
                st.session_state.clear()
                st.rerun()
        with col_botones[2]:
            if st.button("📤 Ver recomendaciones equipo"):
                st.session_state.paso_actual = 4
                st.rerun()

    # Paso 4: Recomendaciones equipo
    elif st.session_state.paso_actual == 4:
        st.header("🩺 Recomendaciones para el Equipo de Salud")
        datos = {'sexo_biologico': st.session_state.datos_personales['Sexo_Biologico']}
        respuestas = st.session_state.respuestas_medicas
        
        recomendaciones = generar_recomendaciones_equipo_salud(datos, respuestas)
        
        for rec in recomendaciones:
            st.info(rec)
        
        if st.button("← Volver a recomendaciones personales"):
            st.session_state.paso_actual = 3
            st.rerun()

if __name__ == "__main__":
    main()