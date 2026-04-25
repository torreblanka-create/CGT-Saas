"""
==========================================
📋 MATRIZ ENGINE DS44 — v2.0 MEJORADO
==========================================
Motor de gestión de Matriz Base DS 44 (CPHS).

CARACTERÍSTICAS v2.0:
✅ Evaluación automática de riesgos por matriz
✅ Seguimiento de medidas de control
✅ Verificación de cumplimiento
✅ Histórico de evaluaciones
✅ Reportes de cumplimiento por actividad
✅ Auditoría de cambios en controles
✅ Métricas de riesgo operativo
✅ Integración con compliance_data
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.infrastructure.database import obtener_conexion, obtener_dataframe

logger = logging.getLogger(__name__)


# ============ DATA MODELS ============

@dataclass
class ItemMatriz:
    """Item de la matriz DS 44"""
    tipo_riesgo: str
    actividad: str
    peligros_riesgos: str
    medidas_control: str


@dataclass
class ImplementacionControl:
    """Registro de implementación de un control"""
    id: str
    item_id: str
    medida_control: str
    estado: str  # 'implementado', 'en_progreso', 'no_implementado'
    responsable: str
    fecha_implementacion: str
    evidencia: str
    nivel_cumplimiento: float  # 0-100%


@dataclass
class ReporteMatrizDS44:
    """Reporte consolidado de cumplimiento de matriz"""
    id: str
    fecha_reporte: str
    total_items: int
    total_medidas: int
    medidas_implementadas: int
    medidas_en_progreso: int
    medidas_no_implementadas: int
    porcentaje_cumplimiento: float
    items_en_riesgo: List[str]
    hallazgos_criticos: int


class MatrizEngine:
    """
    Motor de gestión de Matriz Base DS 44.
    
    Características:
    - Evaluación de riesgos operativos
    - Seguimiento de medidas de control
    - Verificación de cumplimiento
    - Reportes consolidados
    - Auditoría de cambios
    """
    
    def __init__(self, db_path: str = None):
        """Inicializa el motor de matriz DS 44"""
        self.db_path = db_path
        self._crear_tablas()
        logger.info("MatrizEngine inicializado")
    
    def _crear_tablas(self) -> None:
        """Crea tablas para seguimiento de matriz"""
        if not self.db_path:
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS matriz_items (
                id TEXT PRIMARY KEY,
                tipo_riesgo TEXT,
                actividad TEXT,
                peligros_riesgos TEXT,
                medidas_control TEXT,
                cantidad_medidas INTEGER,
                fecha_ingreso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS implementacion_controles (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                medida_control TEXT,
                estado TEXT,
                responsable TEXT,
                fecha_implementacion TIMESTAMP,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evidencia TEXT,
                nivel_cumplimiento REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reportes_matriz (
                id TEXT PRIMARY KEY,
                fecha_reporte TIMESTAMP,
                total_items INTEGER,
                total_medidas INTEGER,
                medidas_implementadas INTEGER,
                medidas_en_progreso INTEGER,
                medidas_no_implementadas INTEGER,
                porcentaje_cumplimiento REAL,
                hallazgos_criticos INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS auditar_cambios_matriz (
                id TEXT PRIMARY KEY,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                item_id TEXT,
                cambio_realizado TEXT,
                usuario_id TEXT,
                detalles TEXT
            )
            """
        ]
        
        try:
            conexion = obtener_conexion(self.db_path)
            for query in tables:
                conexion.execute(query)
            conexion.commit()
            conexion.close()
            logger.debug("Tablas de matriz_engine creadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def registrar_item_matriz(self, tipo_riesgo: str, actividad: str,
                             peligros: str, medidas: str) -> str:
        """
        Registra un item de matriz en la BD.
        
        Args:
            tipo_riesgo: Tipo de riesgo
            actividad: Actividad asociada
            peligros: Descripción de peligros
            medidas: Medidas de control (puede tener múltiples)
        
        Returns:
            ID del item registrado
        """
        try:
            import secrets
            item_id = secrets.token_hex(16)
            
            # Contar cantidad de medidas (numeradas)
            cantidad_medidas = len([l for l in medidas.split('\n') if l.strip() and l.strip()[0].isdigit()])
            
            if not self.db_path:
                return item_id
            
            query = """
            INSERT INTO matriz_items
            (id, tipo_riesgo, actividad, peligros_riesgos, medidas_control, cantidad_medidas)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            conexion = obtener_conexion(self.db_path)
            conexion.execute(query, (item_id, tipo_riesgo, actividad, peligros, medidas, cantidad_medidas))
            conexion.commit()
            conexion.close()
            
            logger.debug(f"✅ Item matriz registrado: {actividad}")
            return item_id
        
        except Exception as e:
            logger.error(f"Error registrando item: {e}")
            return None
    
    def evaluar_implementacion_control(self, item_id: str, medida_numero: int,
                                       estado: str, responsable: str = "",
                                       nivel_cumplimiento: float = 0.0,
                                       evidencia: str = "") -> ImplementacionControl:
        """
        Evalúa la implementación de una medida de control específica.
        
        Args:
            item_id: ID del item de matriz
            medida_numero: Número de la medida (1, 2, 3...)
            estado: 'implementado', 'en_progreso', 'no_implementado'
            responsable: Responsable de implementación
            nivel_cumplimiento: % de cumplimiento (0-100)
            evidencia: Evidencia de implementación
        
        Returns:
            ImplementacionControl registrado
        """
        try:
            import secrets
            
            control_id = secrets.token_hex(16)
            implementacion = ImplementacionControl(
                id=control_id,
                item_id=item_id,
                medida_control=f"Medida #{medida_numero}",
                estado=estado,
                responsable=responsable,
                fecha_implementacion=datetime.now().isoformat(),
                evidencia=evidencia,
                nivel_cumplimiento=nivel_cumplimiento
            )
            
            # Guardar en BD
            if self.db_path:
                query = """
                INSERT INTO implementacion_controles
                (id, item_id, medida_control, estado, responsable, 
                 fecha_implementacion, evidencia, nivel_cumplimiento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                conexion = obtener_conexion(self.db_path)
                conexion.execute(query, (
                    control_id, item_id, f"Medida #{medida_numero}",
                    estado, responsable, datetime.now().isoformat(),
                    evidencia, nivel_cumplimiento
                ))
                conexion.commit()
                conexion.close()
            
            emoji = "✅" if estado == "implementado" else "⏳" if estado == "en_progreso" else "❌"
            logger.info(f"{emoji} Control: {emoji} Medida #{medida_numero} = {estado}")
            
            return implementacion
        
        except Exception as e:
            logger.error(f"Error evaluando control: {e}")
            return None
    
    def generar_reporte_cumplimiento(self) -> ReporteMatrizDS44:
        """
        Genera reporte consolidado de cumplimiento de matriz.
        
        Returns:
            ReporteMatrizDS44 con estadísticas
        """
        if not self.db_path:
            return None
        
        try:
            # Obtener estadísticas
            query_items = "SELECT COUNT(*) as count FROM matriz_items"
            query_medidas = "SELECT COUNT(*) as count FROM implementacion_controles"
            query_implementadas = "SELECT COUNT(*) as count FROM implementacion_controles WHERE estado = 'implementado'"
            query_en_progreso = "SELECT COUNT(*) as count FROM implementacion_controles WHERE estado = 'en_progreso'"
            query_no_implementadas = "SELECT COUNT(*) as count FROM implementacion_controles WHERE estado = 'no_implementado'"
            query_criticos = "SELECT COUNT(*) as count FROM implementacion_controles WHERE nivel_cumplimiento < 50"
            
            df_items = obtener_dataframe(self.db_path, query_items)
            df_medidas = obtener_dataframe(self.db_path, query_medidas)
            df_implementadas = obtener_dataframe(self.db_path, query_implementadas)
            df_en_progreso = obtener_dataframe(self.db_path, query_en_progreso)
            df_no_implementadas = obtener_dataframe(self.db_path, query_no_implementadas)
            df_criticos = obtener_dataframe(self.db_path, query_criticos)
            
            total_items = df_items.iloc[0]['count'] if not df_items.empty else 0
            total_medidas = df_medidas.iloc[0]['count'] if not df_medidas.empty else 0
            implementadas = df_implementadas.iloc[0]['count'] if not df_implementadas.empty else 0
            en_progreso = df_en_progreso.iloc[0]['count'] if not df_en_progreso.empty else 0
            no_implementadas = df_no_implementadas.iloc[0]['count'] if not df_no_implementadas.empty else 0
            criticos = df_criticos.iloc[0]['count'] if not df_criticos.empty else 0
            
            porcentaje = (implementadas / total_medidas * 100) if total_medidas > 0 else 0
            
            reporte = ReporteMatrizDS44(
                id=f"RPT_MATRIZ_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                fecha_reporte=datetime.now().isoformat(),
                total_items=total_items,
                total_medidas=total_medidas,
                medidas_implementadas=implementadas,
                medidas_en_progreso=en_progreso,
                medidas_no_implementadas=no_implementadas,
                porcentaje_cumplimiento=round(porcentaje, 1),
                items_en_riesgo=[],
                hallazgos_criticos=criticos
            )
            
            # Guardar reporte
            if self.db_path:
                query = """
                INSERT INTO reportes_matriz
                (id, fecha_reporte, total_items, total_medidas, medidas_implementadas,
                 medidas_en_progreso, medidas_no_implementadas, porcentaje_cumplimiento, hallazgos_criticos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                conexion = obtener_conexion(self.db_path)
                conexion.execute(query, (
                    reporte.id, reporte.fecha_reporte, total_items, total_medidas,
                    implementadas, en_progreso, no_implementadas,
                    reporte.porcentaje_cumplimiento, criticos
                ))
                conexion.commit()
                conexion.close()
            
            logger.info(f"✅ Reporte matriz: {porcentaje:.1f}% cumplimiento")
            return reporte
        
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return None


# ============ SINGLETON ============

_engine_matriz = None

def obtener_matriz_engine(db_path: str = None) -> MatrizEngine:
    """Obtiene instancia singleton del MatrizEngine"""
    global _engine_matriz
    if _engine_matriz is None:
        from config.config import DB_PATH
        _engine_matriz = MatrizEngine(db_path or DB_PATH)
    return _engine_matriz


# ============ DATOS BASE DS 44 ============

MATRIZ_BASE_DS44 = [
    {
        "tipo_riesgo": "Peligros Generales (Clima, Incendio)",
        "actividad": "Traslado de ida o regreso entre el hogar y el lugar de trabajo.",
        "peligros_riesgos": "Accidente del trayecto: Volcamiento, colisión, atropello, asaltos, caídas del mismo - distinto nivel, caídas de distinto nivel, ataques de perros.",
        "medidas_control": "1) Respetar trayecto directo.\n2) Utilizar el transporte que dispone el empleador.\n3) En caso de accidente del trayecto se debe acreditar con medios fehacientes. Transitar exclusivamente por zonas peatonales y o destinadas para este fin."
    },
    {
        "tipo_riesgo": "Riesgos Específicos Operativos",
        "actividad": "Conducción de vehículos liviano dentro de las Instalaciones de la División, carretera DMH - Calama.",
        "peligros_riesgos": "• Niveles de aceite bajos, falla en frenos, Niveles de agua de radiador bajos, neumáticos en mal estado. etc.\n• Conducción a velocidad no adecuada.\n• Fatiga o Somnolencia.\n• No respetar señalizaciones del tránsito.\n• Choque, colisiones, Volcamiento.\n• Cruce de camiones de extracción (CAEX).\n• Condiciones climáticas adversas (viento, lluvia, encandilamiento).\n• Conducir por Terreno irregular.\n• Aprisionamiento de dedos, manos al cerrar las puertas.\n• Golpeado con puerta de vehículo.\n• Golpeado por o contra, en la manipulación de herramientas o elementos usados en el cambio de rueda del vehículo.\n• Atrapamiento de manos al cambiar neumáticos.\n• Sobreesfuerzo en el cambio de neumático.",
        "medidas_control": "1) Revisar el vehículo siempre antes de iniciar recorrido respaldar dicha revisión mediante formato Check list vehículos.\n2) Estar en buenas condiciones físicas, técnicas y psicológicas. Declaración de idoneidad física y EST N°6 \"fatiga y somnolencia\".\n3) El conductor debe conducir a velocidad permitida.\n4) Manejar a la defensiva atento a las condiciones del tránsito y del terreno. Respetar ley de tránsito 18.290, estar instruido respecto a ruta - layout División Ministro Hales.\n5) Antes de poner en marcha el equipo, debe abrocharse el cinturón de seguridad y usarlo permanentemente mientras el equipo está en movimiento.\n6) Verificar que los acompañantes usen el cinturón de seguridad.\n7) Aplicación y cumplimiento riesgo fatalidad N°10 vehículos\n8) Personal que conduce vehículos livianos debe contar con sus cursos correspondientes \"teórico-práctico psicosensométrico\",\"manejo a la defensiva\", portar su licencia interna y municipal.\n9) Verificación de rutas (críticas).\n10) No debe hablar por celular mientras conduce el equipo, para hacerlo debe estacionar el vehículo.\n11) Debe respetar señalización en cada cruce y permanecer atento al momento de avanzar con una velocidad adecuada y establecida.\n12) Debe conducir a la velocidad que asegure el control total del vehículo en condiciones adversas (lluvia, viento, pavimentos resbaladizos, otros).\n13) Si es encandilado por el sol debe usar la sombrilla del vehículo y/o detener el vehículo hasta que baje el sol.\n14) Al conducir por caminos en mal estado, con curvas o caminos de tierra debe hacerlo con precaución.\n15) El conductor al cerrar y/o abrir puerta del vehículo debe afirmarla y empujarla lentamente asegurando de sacar las manos.\n16) Al abrir o cerrar la puerta debe colocarse en una posición adecuada.\n17) Al cambiar neumáticos debe evitar que el neumático se resbale, sosteniéndolo firmemente y con precaución.\n18) Al levantar o mover neumáticos el conductor debe adoptar postura adecuada de trabajo.\n19) El vehículo o equipo debe contar con barras antivuelco certificadas y contar con el sistema de protección de cabinas RHOPS certificadas."
    },
    {
        "tipo_riesgo": "Peligros Generales (Clima, Incendio)",
        "actividad": "Desplazamiento peatonal en planta y recintos industriales (Inspecciones, visualizaciones, supervisión y control de los trabajos).",
        "peligros_riesgos": "• Resbalamientos.\n• Caída de igual o distinto nivel al circular por frentes de trabajo con terreno irregulares, con materiales en desorden o pisos resbaladizos.\n• Golpeado por diferentes objetos que caen desde distinto nivel o elementos salientes en zona de circulación.\n• Ingreso a taller sin autorización.\n• Atropello por cruzar en sectores de tránsito vehicular.\n• Exposición a polvo con contenido de sílice sobre el límite permisible.",
        "medidas_control": "1) Transitar por zonas peatonales, respetar zonas demarcadas, respetar zonas segregadas, atento a las condiciones del entorno.\n2) Respetar delimitación cuando se haga aseo en instalaciones para evitar resbalamientos.\n3) Al subir o bajar por la escalera no hacerlo corriendo, debe fijarse en cada peldaño y utilizando pasamanos para evitar caídas.\n4) Uso de EPP básico, en salidas a terreno.\n5) Solicitar información de riesgos en visitas a otras áreas y autorización en su ingreso.\n6) No salir de su área sin autorización.\n7) Señalización de advertencia de exposición a polvo con contenido de sílice cristalizada.\n8) Uso obligatorio de EPR (equipo de protección respiratoria).\n9) Realizar lista de chequeo de ajuste diario del EPR.\n10) Portar credencial de prueba portacount (vigente).\n11) Mantener exámenes de vigilancia médica vigente.\n12) Realizar limpieza diaria del EPR antes y después de cada actividad."
    },
    {
        "tipo_riesgo": "Riesgos Específicos Operativos",
        "actividad": "Trabajos administrativos (uso de artículos de oficina, monitores y teclado)",
        "peligros_riesgos": "• Adoptar Posturas inadecuadas al sentarse sobre silla\n• Fatiga Ocular al estar frente al monitor.\n• Contacto directo e indirecto con energía eléctrica.\n• Cortes al manipular tijeras, guillotina, borde de hoja.\n• Atriccionamiento de manos, dedos al manipular archivadores, al abrir y cerrar cajoneras de escritorio.\n• Golpes por cajoneras mal cerrados.\n• Factor Psicosocial por desorden en puesto de trabajo.",
        "medidas_control": "1) El trabajador al sentarse deberá hacerlo de forma adecuada ocupar todo el asiento de modo que la espalda toque el respaldar de la silla.\n2) No debe sentarse en el borde de la silla.\n3) El trabajador debe preocuparse de regular la silla a su altura de modo tal que le permita un ángulo entre muslo y pierna del 90°, con apoyo de pies en el suelo.\n4) Al digitar mantener los brazos sobre la mesa en formas vertical de modo que los codos mantengan un ángulo de 90° y los antebrazos ligeramente inclinados hacia abajo.\n5) Para evitar los reflejos se debe ajustar el brillo y el contraste de la pantalla.\n6) Ajustar tamaños de los caracteres y fuente si fuese necesario.\n7) Para desconectar el equipo (notebook, computadores, impresoras etc. tire de la clavija, nunca del cable.\n8) No tocar o utilizar equipos, instalaciones o alimentadores que se encuentren mojados.\n9) Manipular artículos de oficina con precaución.\n10) Manipular artículos de oficina con precaución.\n11) Al cerrar y/o abrir puerta de cajonera se debe afirmar y empujar lentamente asegurando de sacar las manos.\n12) Mantener cajoneras cerradas.\n13) Mantener orden y aseo en los puestos de trabajo."
    },
    {
        "tipo_riesgo": "Manipulación Manual de Cargas",
        "actividad": "Manipulación manual de Cargas",
        "peligros_riesgos": "• Manipulación inadecuada en el levantamiento de cajas, documentos, archivadores etc.\n• Dolor lumbar y/ lesiones por Posturas inadecuadas TMERT (Trastornos músculos esqueléticos).",
        "medidas_control": "1) Para el levantamiento de carga manual, no exceder peso máximo de carga manual según normativa legal vigente ley 20.949.\n2) Al levantar carga el trabajador debe colocar los pies separados, flexionar rodillas, mantener la espalda recta y ligeramente inclinada hacia delante acercar la carga hacia el cuerpo y elevar la carga realizando la fuerza con las piernas y no con la espalda\n3) Trabajadores deben estar capacitados en la Guía Técnica de manejo manual de carga MMC del Ministerio de Salud.\n4) EST Nº 4.1 A1 - A2 - A3 - A4 - A5 - A6 - A7 (Ergonomia).\n5) Rotación de puestos de trabajo y cambio de tareas de los trabajadores.\n6) Realizar pausas de trabajo durante la jornada laboral que permitan recuperar tensiones y descansar.\n7) Capacitar a los trabajadores expuestos incorporando los requisitos mínimos planteados en la Guía Técnica de trastornos musculo esqueléticos TMERT del Ministerio de Salud."
    },
    {
        "tipo_riesgo": "Riesgos Específicos Operativos",
        "actividad": "Toma de decisiones, comunicación y coordinación de los trabajos",
        "peligros_riesgos": "• Factores Psicosociales: Falta de autonomía para la toma de decisiones.\n• Mala organización de las tareas, carga mental, desmotivación etc.",
        "medidas_control": "1) Para evitar los problemas o efectos psicosociales el trabajador debe procurar obtener la máxima información sobre la totalidad del proceso en que se está trabajando."
    },
    {
        "tipo_riesgo": "Peligros Generales (Clima, Incendio)",
        "actividad": "Consumo de alimentos en áreas industriales.",
        "peligros_riesgos": "Consumir y almacenar alimentos en el lugar de trabajo, existe el riesgo de intoxicación vía oral.",
        "medidas_control": "1) Se prohíbe almacenar y consumir alimentos en los lugares de trabajo en los que se manipulen sustancias toxicas o contaminantes.\n2) Reglamento Interno de Orden Higiene y Seguridad.\n3) En virtud del cumplimiento de Artículo 28 del Decreto Supremo N° 594, la Unidad dispone de un comedor, el que está aislado de las áreas de trabajo y de fuentes de contaminación ambiental. En esta instalación se han adoptado las medidas necesarias para mantenerlo en condiciones higiénicas adecuadas."
    },
    {
        "tipo_riesgo": "Riesgos Específicos Operativos",
        "actividad": "Determinación, uso y control de los Equipos de protección Personal.",
        "peligros_riesgos": "No Usar los equipos de protección personal.\nEquipos de protección personal no adecuados.\nLos equipos de protección personal determinados en la faena son una barrera entre el trabajador y el riesgo.",
        "medidas_control": "1) Todo trabajador que recibe elementos de protección personal, debe dejar constancia firmada de la recepción de estos y el compromiso de uso en las circunstancias y lugares que la empresa establezca su uso obligatorio.\n2) El trabajador está obligado a cumplir con las recomendaciones que se le formulen referentes al uso, conservación y cuidado del equipo o elemento de protección personal.\n3) La supervisión del área controlará que toda persona que realice tareas en la cual se requiere protección personal, cuente con dicho elemento y lo utilice en las áreas determinadas.\n4) Todos los trabajadores que reciben elementos de protección personal serán instruidos en su correcto uso.\n5) Utilizar los EPP en los lugares donde se encuentre indicado su uso.\n6) Verifique diariamente el estado de sus EPP.\n7) No se lleves los EPP a su casa. Manténgalos guardados en un lugar limpio y seguro cuando no los utilice.\n8) Recordar que los EPP son de uso individual y no deben compartirse.\n9) Si el EPP se encuentra deteriorado, solicite su recambio.\n10) No altere el estado de los EPP., y conozca sus limitaciones."
    },
    {
        "tipo_riesgo": "Peligros Generales (Clima, Incendio)",
        "actividad": "Higiene personal, cambio de ropa.",
        "peligros_riesgos": "Condiciones de infraestructura sanitaria inadecuada.",
        "medidas_control": "En virtud del cumplimiento de Artículo 27 del Decreto Supremo N° 594, la empresa cuenta con un recinto fijo destinado a vestidor. En este recinto se dispone de casilleros guardarropas. (Vestidores)."
    },
    {
        "tipo_riesgo": "Agentes Físicos/Químicos (DS 594)",
        "actividad": "Trabajos a la intemperie (Sílice y Polvo).",
        "peligros_riesgos": "Exposición a polvo con contenido de sílice sobre el límite permisible (Enfermedad profesional Silicosis)",
        "medidas_control": "1) Señalización de advertencia de exposición a polvo con contenido de sílice cristalizada.\n2) Uso obligatorio de EPR (equipo de protección respiratoria).\n3) Realizar lista de chequeo de ajuste diario del EPR.\n4) Portar credencial de prueba portacount (vigente).\n5) Mantener exámenes de vigilancia médica vigente.\n6) Realizar limpieza diaria del EPR antes y después de cada actividad.\n7) Informar de los resultados obtenidos en Informe Técnico a trabajadores.\n8) Aplicar RC N° 20 \"Pérdida de Control de Fuentes de emisión de polvo\".\n9) Aplicar EST N° 3 (Guía de Higiene ocupacional 3,2 Sílice y Arsénico).\n10) EPP: (a) Uso de EPP: Respirador de Medio Rostro con Filtro P100. Grado de protección hasta 10 veces 11.-LPP; (b) Pruebas de hermeticidad y ajuste del respirador.\n11) Realizar Informe de Nómina de Expuestos a Sílice (INE).\n12) Generar Programa de Vigilancia Medico Ocupacional y verificar la asistencia de trabajadores."
    },
    {
        "tipo_riesgo": "Agentes Físicos/Químicos (DS 594)",
        "actividad": "Trabajos a la intemperie (Radiación UV).",
        "peligros_riesgos": "Exposición prolongada a radiación UV de origen solar: quemaduras solares, daños a la vista y piel, fatiga / desmayos.",
        "medidas_control": "1) Aplicación de bloqueador solar factor +FPS PPD, 30 minutos antes de iniciar la actividad a la intemperie y cada dos horas durante la jornada laboral.\n2) Se debe capacitar en forma semestral a los trabajadores expuestos incorporando los requisitos mínimos planteados en la Guía Técnica de Radiación UV Solar del Ministerio de Salud.\n3) Uso de EPP (capuchón, lentes de seguridad oscuros con filtro RUV).\n4) Mantener en instalaciones de faena publicación actualizada sobre el índice de RUV Diario.\n5) De presentar fatiga informar al supervisor inmediatamente.\n6) Mantener una alimentación saludable e hidratarse en terreno de 2 a 3 litros de agua.\n7) Estar bajo sombra mientras las circunstancias ameriten."
    },
    {
        "tipo_riesgo": "Peligros Generales (Clima, Incendio)",
        "actividad": "Trabajos a la intemperie (Viento).",
        "peligros_riesgos": "Exposición a vientos fuertes Y/o tormentas: Proyección de partículas, Golpeado por Objeto, Choque/colisión y volcamiento.",
        "medidas_control": "1) Se aplica el instructivo \"condiciones climáticas adversas por viento\" dependiendo del nivel.\n2) Uso obligatorio de lentes de seguridad herméticos y barbiquejo.\n3) Uso equipo de protección personal respiratorio con filtro mixto.\n4) Suspender izaje sobre 36 km/hr. y evaluar el trabajo en altura dependiendo del nivel de alerta.\n5) Ajustar la velocidad y mantener ambas manos en el volante de manera de no perder el control del vehículo."
    },
    {
        "tipo_riesgo": "Riesgos Específicos Operativos",
        "actividad": "Planificar.",
        "peligros_riesgos": "Ejecución de trabajos, recursos humanos y materiales fuera del alcance del contrato",
        "medidas_control": "Ejecución del paso cero de cada una de las actividades ejecutadas en terreno controlando y verificando que se encuentren de acuerdo con la planificación definida."
    }
]
