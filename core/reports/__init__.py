from .base import (
    ReporteCGT,
    generar_excel_gerencial,
    generar_qr,
    obtener_columnas_seguras,
    texto_seguro,
    truncar,
)
from .gestion import (
    generar_pdf_confiabilidad,
    generar_pdf_informe_calidad,
    generar_pdf_plan_accion,
)
from .ingenieria import generar_pdf_rigging_plan
from .legal import generar_pdf_art, generar_pdf_irl
from .operatividad import (
    generar_pdf_bloqueados,
    generar_pdf_completo,
    generar_pdf_fallas,
    generar_pdf_historico_fallas,
    generar_pdf_verdes,
)
