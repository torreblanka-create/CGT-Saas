# core/reports/templates.py

TEMPLATE_CONFIG = {
    "generico": {
        "nombre": "Informe de Calidad Estándar",
        "descripcion": "Plantilla general con descripción y hasta 10 fotos.",
        "secciones": [] # Se maneja con la lógica existente
    },
    "mufa": {
        "nombre": "Plantilla: Mufas y Terminaciones (Media Tensión)",
        "descripcion": "Protocolo completo para confección de mufas y armado de enchufes mineros.",
        "secciones": [
            {
                "id": "trazabilidad",
                "titulo": "1. Datos Generales y Trazabilidad",
                "campos": [
                    {"id": "cliente", "label": "Cliente", "type": "text"},
                    {"id": "faena", "label": "Cliente / Faena", "type": "text"},
                    {"id": "proyecto", "label": "Proyecto / Contrato", "type": "text"},
                    {"id": "fecha_ejecucion", "label": "Fecha de ejecución", "type": "date"},
                    {"id": "inspeccion", "label": "Inspector / Revisor calidad", "type": "text"},
                    {"id": "oc", "label": "N° OC", "type": "text"},
                    {"id": "tipo_intervencion", "label": "Tipo de intervención", "type": "multiselect", "options": ["Mufa", "Enchufe", "Mufa + Enchufe"]}
                ]
            },
            {
                "id": "cable",
                "titulo": "2. Identificación del Cable",
                "campos": [
                    {"id": "cable_desc", "label": "Descripción (Ej: SHD-GC)", "type": "text"},
                    {"id": "n_carrete", "label": "N° Carrete", "type": "text"},
                    {"id": "of", "label": "OF", "type": "text"},
                    {"id": "longitud", "label": "Longitud (m)", "type": "text"}
                ]
            },
            {
                "id": "mufa_data",
                "titulo": "3. Datos de la Mufa / Terminación",
                "campos": [
                    {"id": "mufa_tipo", "label": "Tipo de Mufa", "type": "text"},
                    {"id": "mufa_tech", "label": "Tecnología", "type": "text"},
                    {"id": "mufa_fab", "label": "Fabricante y Modelo", "type": "text"},
                    {"id": "mufa_serie", "label": "N° Serie / Lote", "type": "text"}
                ]
            },
            {
                "id": "enchufe_data",
                "titulo": "4. Datos del Enchufe (Si aplica)",
                "campos": [
                    {"id": "enchufe_tipo", "label": "Tipo de Enchufe", "type": "text"},
                    {"id": "enchufe_tension", "label": "Tensión Nominal", "type": "text"},
                    {"id": "enchufe_fab", "label": "Fabricante y Modelo", "type": "text"},
                    {"id": "enchufe_serie", "label": "N° Serie", "type": "text"}
                ]
            },
            {
                "id": "pasos_preliminares",
                "titulo": "5. Registro Fotográfico Obligatorio (Pasos Preliminares)",
                "type": "checklist",
                "items": [
                    "Corte inicial del cable acorde al enchufe",
                    "Retiro de cubierta exterior",
                    "Preparación Semiconductora",
                    "Exposición de aislamiento",
                    "Instalación de pin o terminal",
                    "Limpieza Previa"
                ]
            },
            {
                "id": "confeccion_mufa",
                "titulo": "6. Confección de la Mufa",
                "type": "checklist",
                "items": [
                    "Limpieza y Lijado",
                    "Instalación de Mastic alivio tensión [Amarillo]",
                    "Instalación tubo control de campos [Negro]",
                    "Instalación de mastic de sellado en terminal [Rojo]",
                    "Instalación de tubo termo contraíble HV [Rojo]",
                    "Instalación de mufa terminada [Una imagen las 3 fases]"
                ]
            },
            {
                "id": "armado_enchufe",
                "titulo": "7. Armado de Enchufe",
                "type": "checklist",
                "items": [
                    "Preparación del conductor",
                    "Instalación del pin",
                    "Control de alineación",
                    "Montaje cuerpo enchufe",
                    "Cierre terminación",
                    "Torque"
                ]
            },
            {
                "id": "presentacion_final",
                "titulo": "8. Presentación Final",
                "type": "checklist",
                "items": [
                    "Vista General",
                    "Vista Aislador interno",
                    "Vista sello hermético",
                    "Vista prensa estopa",
                    "Vista montada en carrete"
                ]
            }
        ]
    }
}
