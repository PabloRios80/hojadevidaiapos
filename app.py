import streamlit as st
from datetime import datetime

def calcular_imc(peso, altura):
    """Calcula el IMC y devuelve categoría con estilo"""
    if altura == 0:
        return 0, "Error"
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

def generar_recomendaciones_paciente(nombre, condiciones, imc):
    """Genera recomendaciones personalizadas para el paciente"""
    recomendaciones = []
    
    # Recomendaciones basadas en IMC
    if imc >= 30:
        recomendaciones.append(f"📉 **Control de peso:** {nombre}, tu IMC indica que podrías beneficiarte con un plan de manejo de peso")
    elif imc >= 25:
        recomendaciones.append(f"⚖️ **Peso saludable:** {nombre}, te recomendamos mantener un balance nutricional")
    
    # Recomendaciones por condiciones médicas
    if condiciones['hipertension']:
        recomendaciones.append("❤️ **Presión arterial:** Control médico regular y reducción de sodio en la dieta")
    if condiciones['diabetes']:
        recomendaciones.append("🩸 **Glucosa en sangre:** Monitoreo periódico y plan alimentario personalizado")
    if condiciones['colesterol']:
        recomendaciones.append("🧪 **Colesterol:** Perfil lipídico anual y reducción de grasas saturadas")
    if condiciones['sedentarismo']:
        recomendaciones.append("🏃 **Actividad física:** Iniciar con 30 minutos diarios de caminata")
    if condiciones['tiempo_sentado']:
        recomendaciones.append("🪑 **Postura y movimiento:** Pausas activas cada 45 minutos")
    if condiciones['fumador']:
        recomendaciones.append("🚭 **Dejar de fumar:** Te recomendamos buscar ayuda profesional para dejar el tabaco")
        if condiciones['fumador_20_anios']:
            recomendaciones.append("⚠️ **Fumador crónico:** Es importante realizar estudios de detección temprana de enfermedades pulmonares")
    if condiciones['embarazo_planeado']:
        recomendaciones.append("🤰 **Ácido fólico:** Si planeas embarazo, comienza con suplementos de ácido fólico")
    
    return recomendaciones

def generar_recomendaciones_equipo_salud(datos, respuestas):
    """Genera recomendaciones para el equipo de salud"""
    recomendaciones = []
    
    # Prevención de cáncer de mama
    if datos['sexo_biologico'] == "Femenino":
        if respuestas['edad'] >= 50:
            recomendaciones.append("🩺 **Prevención de cáncer de mama:** Solicitar mamografía bilateral")
            if respuestas['condiciones']['antecedentes_mama']:
                recomendaciones.append("🩺 **Prevención de cáncer de mama (antecedentes):** Indicar ecografía mamaria + mamografía bilateral a partir de los 40 años")
    
    # Prevención de cáncer colorrectal
    if respuestas['edad'] >= 50:
        recomendaciones.append("🩺 **Prevención de cáncer colorrectal:** Indicar sangre oculta en materia fecal y/o videocolonoscopia")
    
    # Prevención de cáncer de cuello uterino
    if datos['sexo_biologico'] == "Femenino" and respuestas['edad'] >= 18:
        recomendaciones.append("🩺 **Prevención de cáncer de cuello uterino:** Indicar test de HPV")
    
    # Prevención cardiovascular
    if respuestas['edad'] >= 18:
        recomendaciones.append("🩺 **Prevención cardiovascular:** Tomar presión arterial en ambos brazos, medir peso y altura, indicar colesterol total y HDL")
    
    return recomendaciones

def main():
    st.title("Hoja de Vida Preventiva")
    
    # Inicializar session_state
    if 'paso_actual' not in st.session_state:
        st.session_state.update({
            'paso_actual': 1,
            'datos_personales': {},
            'respuestas_medicas': {}
        })
    
    # Paso 1: Datos personales (sin cambios)
    if st.session_state.paso_actual == 1:
        with st.form("form_datos_personales"):
            st.header("📝 Datos Personales")
            
            # Nombre y apellido
            col_nombre, col_apellido = st.columns(2)
            with col_nombre:
                nombre = st.text_input("Nombre", max_chars=50, key="nombre").strip().title()
            with col_apellido:
                apellido = st.text_input("Apellido", max_chars=50, key="apellido").strip().title()
            
            # Fecha nacimiento y sexo
            col_fecha, col_sexo = st.columns(2)
            with col_fecha:
                fecha_nacimiento = st.date_input(
                    "Fecha de Nacimiento*",
                    min_value=datetime(1900, 1, 1),
                    max_value=datetime.today(),
                    key="fecha_nac"
                )
            with col_sexo:
                sexo_biologico = st.selectbox(
                    "Sexo biológico al nacer*",
                    options=["Masculino", "Femenino"],
                    key="sexo_biologico"
                )
                genero_autopercibido = st.selectbox(
                    "Género autopercibido",
                    options=["Mujer", "Hombre", "No binario", "Otro", "Prefiero no responder"],
                    key="genero_auto"
                )
            
            # Contacto
            email = st.text_input("Correo Electrónico*", key="email").strip().lower()
            telefono = st.text_input("Teléfono (Ej: +5491112345678)", key="tel").strip()
            
            # Validación y navegación
            if st.form_submit_button("Continuar →"):
                errores = []
                if not nombre or not apellido: errores.append("Nombre y apellido son obligatorios")
                if "@" not in email: errores.append("Email inválido")
                
                if errores:
                    for error in errores: st.error(error)
                else:
                    st.session_state.datos_personales = {
                        'nombre': nombre,
                        'apellido': apellido,
                        'fecha_nacimiento': fecha_nacimiento.strftime("%Y-%m-%d"),
                        'sexo_biologico': sexo_biologico,
                        'genero_autopercibido': genero_autopercibido,
                        'email': email,
                        'telefono': telefono
                    }
                    st.session_state.paso_actual = 2
                    st.rerun()

    # Paso 2: Factores de riesgo (actualizado)
    elif st.session_state.paso_actual == 2:
        st.header("🔍 Factores de Riesgo")
        datos = st.session_state.datos_personales
        nombre = datos['nombre']
        
        # Calcula edad
        fecha_nac = datetime.strptime(datos['fecha_nacimiento'], "%Y-%m-%d")
        edad = datetime.now().year - fecha_nac.year
        
        # Sección IMC
        st.subheader("Índice de Masa Corporal (IMC)")
        col_peso, col_altura = st.columns(2)
        with col_peso:
            peso = st.number_input("Peso (kg)*", min_value=30.0, max_value=300.0, step=0.1, key="peso")
        with col_altura:
            altura = st.number_input("Altura (cm)*", min_value=100, max_value=250, step=1, key="altura")
        
        # Validación IMC
        imc_error = None
        if peso <= 0 or altura <= 0:
            imc_error = "Ingrese valores válidos para peso y altura"
        
        if imc_error:
            st.error(imc_error)
        else:
            imc_val, (imc_cat, imc_icon, imc_color) = calcular_imc(peso, altura)
            st.markdown(
                f"**Resultado IMC:** {imc_val:.1f} - {imc_icon} "
                f"<span style='color:{imc_color};font-weight:bold;'>{imc_cat}</span>",
                unsafe_allow_html=True
            )
        
        # Nuevas preguntas
        st.subheader(f"👩⚕️ {nombre}, ¿cuál es tu situación actual?")
        
        # Definir condiciones iniciales
        condiciones = {
            'hipertension': st.checkbox("Tengo hipertensión arterial (presión alta)"),
            'diabetes': st.checkbox("Tengo diabetes (azúcar alta en sangre)"),
            'colesterol': st.checkbox("Tengo colesterol alto en sangre)"),
            'sedentarismo': st.checkbox("Realizo poca actividad física)"),
            'tiempo_sentado': st.checkbox("Pasó más de 6 horas diarias sentado/a)"),
            'fumador': st.checkbox("Soy fumador/a"),
            'alcohol_drogas': st.checkbox("Abuso de alcohol y/o drogas)"),
            'violencia_familiar': st.checkbox("Convivo con violencia familiar)"),
            'depresion': st.checkbox("Tengo depresión, falta de deseo o ganas de vivir)"),
            'antecedentes_colon': st.checkbox("Antecedentes familiares de cáncer de colon)"),
            'antecedentes_mama': st.checkbox("Antecedentes familiares de cáncer de mama)"),
            'antecedentes_cuello_utero': st.checkbox("Antecedentes familiares de cáncer de cuello de útero)"),
            'otro_cancer': st.text_input("Otro tipo de cáncer (especificar)"),
            'otra_condicion': st.text_area("Escriba otra condición que crea importante que conozcamos sobre su salud)")
        }
        
        # Pregunta condicional para fumadores
        if condiciones['fumador']:
            condiciones['fumador_20_anios'] = st.checkbox("Fumo durante 20 años o más")
        else:
            condiciones['fumador_20_anios'] = False
        
        # Pregunta condicional para mujeres que planean embarazo
        if datos['sexo_biologico'] == "Femenino":
            condiciones['embarazo_planeado'] = st.checkbox("Planeo embarazo en los próximos 6 meses")
        else:
            condiciones['embarazo_planeado'] = False
        
        # Botones de navegación
        col_botones = st.columns([1, 1, 1])
        with col_botones[0]:
            if st.button("← Atrás"):
                st.session_state.paso_actual = 1
                st.rerun()
        with col_botones[2]:
            if st.button("Siguiente →"):
                if peso > 0 and altura > 0:
                    st.session_state.respuestas_medicas = {
                        'edad': edad,
                        'imc_val': imc_val,
                        'imc_cat': imc_cat,
                        'condiciones': condiciones,
                        'peso': peso,
                        'altura': altura
                    }
                    st.session_state.paso_actual = 3
                    st.rerun()
                else:
                    st.error("Complete todos los campos obligatorios")

    # Paso 3: Recomendaciones para el paciente
    elif st.session_state.paso_actual == 3:
        st.header("📋 Recomendaciones Personalizadas")
        datos = st.session_state.datos_personales
        respuestas = st.session_state.respuestas_medicas
        nombre = datos['nombre']
        
        # Resumen del paciente
        st.subheader(f"👤 Resumen de {nombre}")
        st.markdown(f"""
        - **Edad:** {respuestas['edad']} años
        - **IMC:** {respuestas['imc_val']:.1f} ({respuestas['imc_cat']})
        - **Contacto:** {datos['email']} | {datos['telefono']}
        """)
        
        # Generar recomendaciones
        st.subheader("🩺 Recomendaciones Preventivas")
        recomendaciones = generar_recomendaciones_paciente(
            nombre, 
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
        
        # Navegación final
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
            if st.button("📤 Ver recomendaciones para el equipo de salud"):
                st.session_state.paso_actual = 4
                st.rerun()

    # Paso 4: Recomendaciones para el equipo de salud
    elif st.session_state.paso_actual == 4:
        st.header("🩺 Recomendaciones para el Equipo de Salud")
        datos = st.session_state.datos_personales
        respuestas = st.session_state.respuestas_medicas
        
        recomendaciones = generar_recomendaciones_equipo_salud(datos, respuestas)
        
        for rec in recomendaciones:
            st.info(rec)
        
        if st.button("← Volver a recomendaciones personales"):
            st.session_state.paso_actual = 3
            st.rerun()

if __name__ == "__main__":
    main()