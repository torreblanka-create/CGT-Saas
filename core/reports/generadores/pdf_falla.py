import os

from core.reports.base_pdf import ReporteBase, texto_seguro


class GeneradorPdfFalla(ReporteBase):
    def __init__(self, datos, logo_app, logo_cliente, db_path):
        super().__init__(f"REPORTE TÉCNICO DE FALLA: {datos['identificador']}", logo_app, logo_cliente, db_path)
        self.datos = datos

    def generar(self):
        self.alias_nb_pages()
        self.add_page()

        # 1. Encabezado de Identificación
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(25, 58, 138)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, " DETALLES DEL EQUIPO Y EVENTO", 1, 1, 'L', fill=True)

        # Buscar datos del equipo en el maestro usando relacionalidad
        equipo_maestro = self.obtener_entidad_maestro(self.datos['identificador'], self.datos.get('empresa_id', 0), self.datos.get('contrato_id', 0))
        nombre_equipo = equipo_maestro['nombre'] if equipo_maestro else "Desconocido"

        self.set_font("Helvetica", "B", 10)
        self.set_text_color(0, 0, 0)
        col_w1, col_w2 = 45, 145

        datos_malla = [
            ("Sistema / TAG:", f"{self.datos['identificador']} - {nombre_equipo}"),
            ("Tipo de Evento / Falla:", self.datos['tipo_falla']),
            ("Fecha del Evento:", str(self.datos['fecha'])),
            ("Impacto Op. (Minutos):", f"{self.datos['duracion_min']} min"),
            ("Estado Final:", self.datos.get('estado', 'Cerrado'))
        ]

        for label, valor in datos_malla:
            self.set_font("Helvetica", "B", 10)
            self.cell(col_w1, 8, f" {label}", 1)
            self.set_font("Helvetica", "", 10)
            self.cell(col_w2, 8, f" {valor}", 1, 1)

        self.ln(5)

        # 2. Descripción Técnica
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.set_text_color(25, 58, 138)
        self.cell(0, 10, " DESCRIPCIÓN TÉCNICA DEL EVENTO", 1, 1, 'L', fill=True)

        self.set_font("Helvetica", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 8, f" {texto_seguro(self.datos['descripcion'])}", border=1)

        self.ln(10)

        # 3. Evidencia Fotográfica
        foto_path = self.datos.get('foto_path')
        if foto_path and os.path.exists(foto_path):
            self.ln(5)
            self.set_font("Helvetica", "B", 12)
            self.set_fill_color(245, 245, 245)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, " EVIDENCIA FOTOGRÁFICA DEL EVENTO", 1, 1, 'L', fill=True)

            try:
                self.image(foto_path, x=45, y=self.get_y() + 5, w=120)
                self.set_y(self.get_y() + 90)
            except Exception as e:
                self.set_font("Helvetica", "I", 10)
                self.set_text_color(200, 0, 0)
                self.cell(0, 10, f" [Error al cargar imagen: {str(e)}]", 1, 1, 'C')

        self.ln(10)

        # Nota técnica al final
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, "\n*Este informe es generado automáticamente por la base de datos relacional de CGT Confiabilidad. La información contenida es vital para el análisis de tendencias y mejora continua del mantenimiento preventivo.", align='C')

        # Firmas al pie
        self.dibujar_seccion_firmas(['Reportado por (Técnico)', 'Validado por (Mantenimiento)'])

        return bytes(self.output())
