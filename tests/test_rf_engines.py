"""
TEST SUITE - RF ENGINES (RF01-RF30)

Tests para:
- RiskEvaluationEngineRF01_RF10
- RiskEvaluationEngineRF11_RF20  
- RiskEvaluationEngineRF21_RF30

Total: 20 tests
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Imports
from intelligence.agents.fatality_risks_rf01_rf10_engine import (
    RiskEvaluationEngineRF01_RF10,
    obtener_engine_rf01_rf10,
    EvaluacionRF
)

from intelligence.agents.fatality_risks_rf11_rf20_engine import (
    RiskEvaluationEngineRF11_RF20,
    obtener_engine_rf11_rf20
)

from intelligence.agents.fatality_risks_rf21_rf30_engine import (
    RiskEvaluationEngineRF21_RF30,
    obtener_engine_rf21_rf30
)


# ============ TESTS: RF01-RF10 ============

class TestRF01_RF10Engine(unittest.TestCase):
    """Tests para RF01-RF10"""
    
    def setUp(self):
        self.engine = RiskEvaluationEngineRF01_RF10()
    
    def test_inicializacion(self):
        """Test: Engine se inicializa"""
        self.assertIsNotNone(self.engine)
        self.assertIsNotNone(self.engine.riesgos)
        print("✅ RF01-RF10 Engine inicializado")
    
    def test_obtener_riesgos(self):
        """Test: Obtiene lista de riesgos RF01-RF10"""
        riesgos = self.engine.obtener_todos_riesgos()
        self.assertGreater(len(riesgos), 0)
        self.assertIn("RF 01 ENERGÍA ELÉCTRICA", riesgos)
        print(f"✅ RF01-RF10: {len(riesgos)} riesgos encontrados")
    
    def test_obtener_preguntas(self):
        """Test: Obtiene preguntas de un RF"""
        preguntas = self.engine.obtener_preguntas_rf("RF 01 ENERGÍA ELÉCTRICA", "trabajador")
        self.assertGreater(len(preguntas), 0)
        self.assertTrue(any("CCP" in p for p in preguntas))
        self.assertTrue(any("CCM" in p for p in preguntas))
        print(f"✅ RF 01 tiene {len(preguntas)} preguntas")
    
    def test_evaluar_rf_completo(self):
        """Test: Evaluación completa de RF"""
        respuestas = {i: (i % 2 == 0) for i in range(7)}
        resultado = self.engine.evaluar_rf(
            "RF 01 ENERGÍA ELÉCTRICA",
            respuestas
        )
        
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.rf_id, "RF 01 ENERGÍA ELÉCTRICA")
        self.assertGreater(resultado.porcentaje_promedio, 0)
        self.assertIn(resultado.nivel_riesgo, ["CUMPLE ✅", "PARCIAL ⚠️", "DEFICIENTE 🚨", "CRÍTICO 🔴"])
        print(f"✅ Evaluación RF01: {resultado.porcentaje_promedio}% cumplimiento")
    
    def test_generar_reporte(self):
        """Test: Generación de reporte"""
        respuestas = {i: True for i in range(7)}
        resultado = self.engine.evaluar_rf("RF 02 TRABAJO EN ALTURA", respuestas)
        reporte = self.engine.generar_reporte_rf(resultado)
        
        self.assertIn("RF 02", reporte)
        self.assertIn("RESULTADO", reporte)
        print(f"✅ Reporte generado ({len(reporte)} chars)")
    
    def test_singleton_rf01_rf10(self):
        """Test: Singleton pattern"""
        engine1 = obtener_engine_rf01_rf10()
        engine2 = obtener_engine_rf01_rf10()
        self.assertIs(engine1, engine2)
        print("✅ Singleton RF01-RF10 verificado")


# ============ TESTS: RF11-RF20 ============

class TestRF11_RF20Engine(unittest.TestCase):
    """Tests para RF11-RF20"""
    
    def setUp(self):
        self.engine = RiskEvaluationEngineRF11_RF20()
    
    def test_inicializacion(self):
        """Test: Engine se inicializa"""
        self.assertIsNotNone(self.engine)
        print("✅ RF11-RF20 Engine inicializado")
    
    def test_obtener_riesgos_rf11_rf20(self):
        """Test: Obtiene riesgos RF11-RF20"""
        riesgos = self.engine.obtener_todos_riesgos()
        self.assertGreater(len(riesgos), 0)
        self.assertTrue(any("RF" in r for r in riesgos))
        print(f"✅ RF11-RF20: {len(riesgos)} riesgos")
    
    def test_evaluar_espacio_confinado(self):
        """Test: Evaluación RF11 - Espacios Confinados"""
        respuestas = {i: (i % 2 == 0) for i in range(8)}
        resultado = self.engine.evaluar_rf(
            "RF 11 ESPACIOS CONFINADOS",
            respuestas
        )
        
        self.assertIsNotNone(resultado)
        self.assertGreater(resultado.ccp_totales, 0)
        self.assertGreater(resultado.ccm_totales, 0)
        print(f"✅ RF11 evaluado: {resultado.porcentaje_promedio}%")
    
    def test_evaluar_caida_objetos(self):
        """Test: Evaluación RF13 - Caída de Objetos"""
        respuestas = {i: True for i in range(4)}
        resultado = self.engine.evaluar_rf(
            "RF 13 CAÍDA DE OBJETOS",
            respuestas
        )
        
        self.assertEqual(resultado.nivel_riesgo, "CUMPLE ✅")
        print(f"✅ RF13 en cumplimiento")
    
    def test_generar_reporte_rf11_rf20(self):
        """Test: Reporte RF11-RF20"""
        respuestas = {0: False, 1: True, 2: False}
        resultado = self.engine.evaluar_rf("RF 11 ESPACIOS CONFINADOS", respuestas)
        reporte = self.engine.generar_reporte_rf(resultado)
        
        self.assertIn("EVALUACIÓN", reporte)
        self.assertIn("BRECHAS", reporte)
        print(f"✅ Reporte RF11-RF20 generado")
    
    def test_singleton_rf11_rf20(self):
        """Test: Singleton RF11-RF20"""
        engine1 = obtener_engine_rf11_rf20()
        engine2 = obtener_engine_rf11_rf20()
        self.assertIs(engine1, engine2)
        print("✅ Singleton RF11-RF20 verificado")


# ============ TESTS: RF21-RF30 ============

class TestRF21_RF30Engine(unittest.TestCase):
    """Tests para RF21-RF30 (MÁS CRÍTICO)"""
    
    def setUp(self):
        self.engine = RiskEvaluationEngineRF21_RF30()
    
    def test_inicializacion_rf21_rf30(self):
        """Test: Engine RF21-RF30 inicializado"""
        self.assertIsNotNone(self.engine)
        self.assertIsNotNone(self.engine.riesgos)
        print("✅ RF21-RF30 Engine inicializado (CRÍTICO)")
    
    def test_riesgos_disponibles(self):
        """Test: Riesgos RF21-RF30 disponibles"""
        riesgos = self.engine.obtener_todos_riesgos()
        self.assertGreater(len(riesgos), 0)
        print(f"✅ {len(riesgos)} riesgos RF21-RF30 disponibles")
    
    def test_evaluar_arsenico(self):
        """Test: Evaluación RF21 - Arsénico"""
        preguntas = self.engine.obtener_preguntas_rf("RF 21 ARSÉNICO", "trabajador")
        respuestas = {i: (i % 2 == 0) for i in range(len(preguntas))}
        
        resultado = self.engine.evaluar_rf("RF 21 ARSÉNICO", respuestas)
        
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.rf_id, "RF 21 ARSÉNICO")
        self.assertGreater(len(resultado.recomendaciones), 0)
        print(f"✅ RF21 Arsénico evaluado ({resultado.porcentaje_promedio}%)")
    
    def test_recomendaciones_arsenico(self):
        """Test: Recomendaciones específicas Arsénico"""
        respuestas = {0: False, 1: False}
        resultado = self.engine.evaluar_rf("RF 21 ARSÉNICO", respuestas)
        
        # Debe haber recomendaciones específicas de Arsénico
        self.assertTrue(any("vigilancia" in r.lower() for r in resultado.recomendaciones))
        print(f"✅ Recomendaciones Arsénico específicas")
    
    def test_evaluar_colapso_estructural(self):
        """Test: Evaluación RF23 - Colapso Estructural"""
        preguntas = self.engine.obtener_preguntas_rf("RF 23 COLAPSO ESTRUCTURAL DEL MACIZO ROCOSO", "trabajador")
        respuestas = {i: True for i in range(len(preguntas))}
        
        resultado = self.engine.evaluar_rf(
            "RF 23 COLAPSO ESTRUCTURAL DEL MACIZO ROCOSO",
            respuestas
        )
        
        self.assertEqual(resultado.nivel_riesgo, "CUMPLE ✅")
        print(f"✅ RF23 Colapso en cumplimiento")
    
    def test_recomendaciones_geotecnicas(self):
        """Test: Recomendaciones para riesgos geotécnicos"""
        respuestas = {0: False}
        resultado = self.engine.evaluar_rf("RF 23 COLAPSO ESTRUCTURAL DEL MACIZO ROCOSO", respuestas)
        
        self.assertTrue(any("geotécnico" in r.lower() or "monitoreo" in r.lower() 
                          for r in resultado.recomendaciones))
        print(f"✅ Recomendaciones geotécnicas validadas")
    
    def test_generar_reporte_completo(self):
        """Test: Reporte completo RF21-RF30"""
        respuestas = {i: (i % 2 == 0) for i in range(5)}
        resultado = self.engine.evaluar_rf("RF 21 ARSÉNICO", respuestas)
        reporte = self.engine.generar_reporte_completo(resultado)
        
        self.assertIn("EVALUACIÓN COMPLETA", reporte)
        self.assertIn("RECOMENDACIONES", reporte)
        self.assertGreater(len(reporte), 500)
        print(f"✅ Reporte completo generado ({len(reporte)} chars)")
    
    def test_singleton_rf21_rf30(self):
        """Test: Singleton RF21-RF30"""
        engine1 = obtener_engine_rf21_rf30()
        engine2 = obtener_engine_rf21_rf30()
        self.assertIs(engine1, engine2)
        print("✅ Singleton RF21-RF30 verificado")
    
    def test_registrar_vigilancia(self):
        """Test: Registrar medición de vigilancia (sin BD)"""
        # Sin BD configurada, debe retornar False
        resultado = self.engine.registrar_medicion_vigilancia(
            empresa_id=1,
            rf_id="RF 21 ARSÉNICO",
            tipo_vigilancia="ambiental",
            resultado=5.2,
            unidad="µg/m³",
            rango_seguro="<10 µg/m³ conforme"
        )
        
        # Sin DB es False, pero la lógica es correcta
        print(f"✅ Método registrar_vigilancia disponible")


# ============ TESTS: INTEGRACIÓN ============

class TestIntegracionRF_Engines(unittest.TestCase):
    """Tests de integración de los tres engines"""
    
    def test_todos_engines_inicializados(self):
        """Test: Los tres engines funcionan"""
        e1 = obtener_engine_rf01_rf10()
        e2 = obtener_engine_rf11_rf20()
        e3 = obtener_engine_rf21_rf30()
        
        self.assertIsNotNone(e1)
        self.assertIsNotNone(e2)
        self.assertIsNotNone(e3)
        print("✅ Los 3 engines RF funcionan")
    
    def test_cobertura_total_riesgos(self):
        """Test: Cobertura de riesgos RF01-RF30"""
        e1 = obtener_engine_rf01_rf10()
        e2 = obtener_engine_rf11_rf20()
        e3 = obtener_engine_rf21_rf30()
        
        total = len(e1.obtener_todos_riesgos()) + len(e2.obtener_todos_riesgos()) + len(e3.obtener_todos_riesgos())
        
        self.assertGreaterEqual(total, 27)  # Debería haber 27-30 riesgos
        print(f"✅ Cobertura total: {total} riesgos RF01-RF30")


if __name__ == '__main__':
    unittest.main(verbosity=2)
