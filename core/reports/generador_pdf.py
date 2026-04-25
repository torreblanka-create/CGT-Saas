"""
Módulo Centralizado de Reportabilidad PDF
Proporciona la interfaz unificada para la generación de cualquier documento de la aplicación.
"""
import traceback

from core.reports.gestion import (
    generar_pdf_confiabilidad,
    generar_pdf_incidente,
    generar_pdf_informe_calidad,
    generar_pdf_libro_aprendizaje,
    generar_pdf_plan_accion,
    generar_pdf_sgi,
)
from core.reports.ingenieria import generar_pdf_rigging_plan
from core.reports.legal import generar_pdf_art, generar_pdf_compliance, generar_pdf_irl
from core.reports.operatividad import (
    generar_pdf_bloqueados,
    generar_pdf_completo,
    generar_pdf_fallas,
    generar_pdf_historico_fallas,
    generar_pdf_verdes,
)
from core.reports.trazabilidad import generar_pdf_trazabilidad


class GeneradorPDFCentralizado:
    """
    Servicio centralizado que orquesta la generación de PDFs.
    Actúa como Facade para aislar a las vistas de la lógica de librerías PDF.
    """

    @staticmethod
    def generar(tipo_reporte, *args, **kwargs):
        """
        Punto de entrada único para la creación de reportes.
        """
        mapa_generadores = {
            # Preventiva y Legal
            'ART': generar_pdf_art,
            'IRL': generar_pdf_irl,
            'INCIDENTE': generar_pdf_incidente,
            'LIBRO_APRENDIZAJE': generar_pdf_libro_aprendizaje,
            'COMPLIANCE': generar_pdf_compliance,

            # Ingeniería, Calidad y Mantenimiento
            'RIGGING_PLAN': generar_pdf_rigging_plan,
            'CALIDAD': generar_pdf_informe_calidad,
            'FALLA_CONFIABILIDAD': generar_pdf_confiabilidad,

            # Trazabilidad, Planes y Operatividad
            'PLAN_ACCION': generar_pdf_plan_accion,
            'TARJETA': generar_pdf_trazabilidad,
            'BLOQUEADOS': generar_pdf_bloqueados,
            'VERDES': generar_pdf_verdes,
            'FALLAS_RESUMEN': generar_pdf_fallas,
            'HISTORICO_FALLAS': generar_pdf_historico_fallas,
            'COMPLETO': generar_pdf_completo,
            'SGI': generar_pdf_sgi
        }

        generador = mapa_generadores.get(str(tipo_reporte).upper())

        if not generador:
            raise ValueError(f"🚨 Tipo de reporte '{tipo_reporte}' no soportado por el motor central.")

        try:
            return generador(*args, **kwargs)
        except Exception as e:
            print(f"Error en GeneradorPDFCentralizado ({tipo_reporte}): {traceback.format_exc()}")
            raise e

# Proveemos un Singleton pre-instanciado
pdf_engine = GeneradorPDFCentralizado()
