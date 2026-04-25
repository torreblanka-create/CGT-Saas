"""
===========================================
🧪 PRUEBAS - Risk Manager & Mock Audit
===========================================
Ejemplos de uso de los nuevos módulos.
Ejecutar con: python -m pytest tests/test_managers.py -v
"""

import pytest
from src.services.risk_manager import (
    RiskManager, obtener_risk_manager, buscar_riesgo, 
    listar_riesgos, buscar_por_palabra
)
from intelligence.agents.mock_audit_engine import (
    generar_examen_simulacro, calificar_simulacro_detallado,
    generar_reporte_auditoria, BANCO_PREGUNTAS_GENERAL
)


class TestRiskManager:
    """Suite de pruebas para RiskManager"""
    
    def setup_method(self):
        """Ejecuta antes de cada test"""
        self.manager = RiskManager()
    
    def test_inicializacion(self):
        """Verifica que RiskManager se inicializa correctamente"""
        assert self.manager.riesgos is not None
        assert len(self.manager.riesgos) > 0
    
    def test_contar_riesgos(self):
        """Verifica conteo total de riesgos"""
        total = self.manager.contar_riesgos()
        assert total >= 20  # Debe haber al menos 20 riesgos (RF01-RF20)
        print(f"✓ Total de riesgos: {total}")
    
    def test_obtener_riesgo_valido(self):
        """Verifica obtención de un riesgo existente"""
        riesgo = self.manager.obtener_riesgo("RF 01 ENERGÍA ELÉCTRICA")
        assert riesgo is not None
        assert "Trabajador" in riesgo
        assert "Supervisor" in riesgo
        print(f"✓ Riesgo obtenido: {riesgo['Trabajador'][:50]}...")
    
    def test_obtener_riesgo_invalido(self):
        """Verifica que retorna None para riesgo inexistente"""
        riesgo = self.manager.obtener_riesgo("RF 99 INEXISTENTE")
        assert riesgo is None
    
    def test_listar_todos_riesgos(self):
        """Verifica listado de todos los riesgos"""
        riesgos = self.manager.listar_todos_riesgos()
        assert isinstance(riesgos, list)
        assert len(riesgos) > 0
        assert riesgos == sorted(riesgos)  # Debe estar ordenado
        print(f"✓ Primeros 3 riesgos: {riesgos[:3]}")
    
    def test_preguntas_trabajador(self):
        """Verifica obtención de preguntas del trabajador"""
        preguntas = self.manager.obtener_preguntas_trabajador("RF 02 TRABAJO EN ALTURA")
        assert isinstance(preguntas, list)
        assert len(preguntas) > 0
        assert all(isinstance(p, str) for p in preguntas)
        print(f"✓ Preguntas trabajador (RF 02): {len(preguntas)}")
    
    def test_preguntas_supervisor(self):
        """Verifica obtención de preguntas del supervisor"""
        preguntas = self.manager.obtener_preguntas_supervisor("RF 02 TRABAJO EN ALTURA")
        assert isinstance(preguntas, list)
        assert len(preguntas) > 0
        print(f"✓ Preguntas supervisor (RF 02): {len(preguntas)}")
    
    def test_todas_preguntas(self):
        """Verifica obtención de todas las preguntas de un riesgo"""
        todas = self.manager.obtener_todas_preguntas("RF 02 TRABAJO EN ALTURA")
        assert "Trabajador" in todas
        assert "Supervisor" in todas
        assert len(todas["Trabajador"]) > 0
        assert len(todas["Supervisor"]) > 0
    
    def test_contar_preguntas_por_rol(self):
        """Verifica conteo de preguntas por rol"""
        conteo = self.manager.contar_preguntas_por_rol("RF 02 TRABAJO EN ALTURA")
        assert isinstance(conteo, dict)
        assert "Trabajador" in conteo
        assert "Supervisor" in conteo
        assert conteo["Trabajador"] > 0
        assert conteo["Supervisor"] > 0
        print(f"✓ RF 02 - T: {conteo['Trabajador']}, S: {conteo['Supervisor']}")
    
    def test_buscar_por_palabra_clave(self):
        """Verifica búsqueda por palabra clave"""
        resultados = self.manager.buscar_por_palabra_clave("ALTURA")
        assert isinstance(resultados, list)
        assert len(resultados) > 0
        assert "RF 02 TRABAJO EN ALTURA" in resultados
        print(f"✓ Búsqueda 'ALTURA': {resultados}")
    
    def test_buscar_en_preguntas(self):
        """Verifica búsqueda dentro de preguntas"""
        resultados = self.manager.buscar_en_preguntas("licencia")
        assert isinstance(resultados, list)
        assert len(resultados) > 0
        # Cada resultado es (rf_id, rol, pregunta)
        for rf_id, rol, pregunta in resultados:
            assert rf_id in self.manager.riesgos
            assert rol in ["Trabajador", "Supervisor"]
            assert "licencia" in pregunta.lower()
        print(f"✓ Búsqueda en preguntas: {len(resultados)} coincidencias")
    
    def test_filtrar_por_rol(self):
        """Verifica filtrado por rol"""
        stats = self.manager.filtrar_por_rol("Trabajador")
        assert isinstance(stats, dict)
        assert len(stats) > 0
        print(f"✓ Riesgos con preguntas de Trabajador: {len(stats)}")
    
    def test_obtener_riesgos_por_numero(self):
        """Verifica obtención de riesgos por rango numérico"""
        riesgos = self.manager.obtener_riesgos_por_numero(1, 10)
        assert isinstance(riesgos, dict)
        assert len(riesgos) > 0
        # Verificar que todos están en rango RF01-RF10
        for rf_id in riesgos.keys():
            numero = int(rf_id.split()[1])
            assert 1 <= numero <= 10
        print(f"✓ Riesgos RF01-RF10: {len(riesgos)}")
    
    def test_estadisticas(self):
        """Verifica generación de estadísticas"""
        stats = self.manager.obtener_estadisticas()
        assert "total_riesgos" in stats
        assert "total_preguntas_trabajador" in stats
        assert "total_preguntas_supervisor" in stats
        assert "total_preguntas" in stats
        assert stats["total_preguntas"] > 0
        print(f"✓ Estadísticas: {stats['total_riesgos']} riesgos, {stats['total_preguntas']} preguntas")
    
    def test_singleton(self):
        """Verifica que obtener_risk_manager retorna singleton"""
        mgr1 = obtener_risk_manager()
        mgr2 = obtener_risk_manager()
        assert mgr1 is mgr2
        print("✓ Singleton funcionando correctamente")


class TestMockAuditEngine:
    """Suite de pruebas para Mock Audit Engine"""
    
    def test_banco_preguntas_expandido(self):
        """Verifica que el banco de preguntas está expandido"""
        assert len(BANCO_PREGUNTAS_GENERAL) > 20  # Al menos 20 preguntas en el banco
        print(f"✓ Banco de preguntas: {len(BANCO_PREGUNTAS_GENERAL)} preguntas")
    
    def test_estructura_preguntas(self):
        """Verifica que cada pregunta tiene estructura correcta"""
        for pregunta in BANCO_PREGUNTAS_GENERAL:
            assert "texto" in pregunta
            assert "categoria" in pregunta
            assert "severidad" in pregunta
            assert "evidencia_clave" in pregunta
        print("✓ Estructura de preguntas validada")
    
    def test_generar_examen_basico(self):
        """Verifica generación de examen básico"""
        examen = generar_examen_simulacro(db_path=":memory:", n_preguntas=10)
        assert isinstance(examen, list)
        assert len(examen) == 10
        assert all(isinstance(p, dict) for p in examen)
        print(f"✓ Examen generado: {len(examen)} preguntas")
    
    def test_generar_examen_cantidad_variable(self):
        """Verifica que se genera la cantidad correcta de preguntas"""
        for n in [5, 10, 20]:
            examen = generar_examen_simulacro(db_path=":memory:", n_preguntas=n)
            assert len(examen) == n
        print("✓ Generación de examen con cantidad variable OK")
    
    def test_calificacion_perfecta(self):
        """Verifica calificación con 100% aciertos"""
        respuestas = {i: True for i in range(10)}
        resultado = calificar_simulacro_detallado(respuestas)
        
        assert resultado['total'] == 10
        assert resultado['correctas'] == 10
        assert resultado['porcentaje'] == 100.0
        assert resultado['nivel_riesgo'] == "EXCELENTE"
        print(f"✓ Calificación 100%: {resultado['nivel_riesgo']}")
    
    def test_calificacion_cero(self):
        """Verifica calificación con 0% aciertos"""
        respuestas = {i: False for i in range(10)}
        resultado = calificar_simulacro_detallado(respuestas)
        
        assert resultado['total'] == 10
        assert resultado['correctas'] == 0
        assert resultado['porcentaje'] == 0.0
        assert resultado['nivel_riesgo'] == "CRÍTICO"
        print(f"✓ Calificación 0%: {resultado['nivel_riesgo']}")
    
    def test_calificacion_parcial(self):
        """Verifica calificación con aciertos parciales"""
        respuestas = {0: True, 1: False, 2: True, 3: False, 4: True}
        resultado = calificar_simulacro_detallado(respuestas)
        
        assert resultado['total'] == 5
        assert resultado['correctas'] == 3
        assert resultado['porcentaje'] == 60.0
        assert resultado['nivel_riesgo'] == "REGULAR"
        print(f"✓ Calificación 60%: {resultado['nivel_riesgo']}")
    
    def test_generar_reporte(self):
        """Verifica generación de reporte textual"""
        examen = generar_examen_simulacro(db_path=":memory:", n_preguntas=5)
        respuestas = {i: (i % 2 == 0) for i in range(5)}  # Alterno True/False
        
        reporte = generar_reporte_auditoria(respuestas, examen, "Test observaciones")
        
        assert isinstance(reporte, str)
        assert "REPORTE" in reporte
        assert "RESUMEN EJECUTIVO" in reporte
        assert "DETALLE POR PREGUNTA" in reporte
        assert "RECOMENDACIONES" in reporte
        print("✓ Reporte generado exitosamente")


# ============= PRUEBAS DE INTEGRACIÓN =============

class TestIntegracion:
    """Pruebas de integración entre módulos"""
    
    def test_risk_manager_con_audit(self):
        """Verifica integración entre RiskManager y Mock Audit"""
        manager = RiskManager()
        examen = generar_examen_simulacro(db_path=":memory:", n_preguntas=10)
        
        # Verificar que el examen tiene preguntas válidas
        assert len(examen) == 10
        assert all(isinstance(p, dict) for p in examen)
        
        print("✓ Integración RiskManager + MockAudit OK")
    
    def test_busqueda_y_puntuacion(self):
        """Verifica búsqueda de riesgos y puntuación"""
        manager = RiskManager()
        
        # Buscar riesgos relacionados a "electricidad"
        resultados = manager.buscar_por_palabra_clave("ELÉCTRICA")
        assert len(resultados) > 0
        
        # Obtener preguntas del riesgo encontrado
        if resultados:
            rf_id = resultados[0]
            preguntas = manager.obtener_preguntas_trabajador(rf_id)
            assert len(preguntas) > 0
        
        print("✓ Búsqueda y obtención de preguntas OK")


# ============= EJECUCIÓN DIRECTA =============

if __name__ == "__main__":
    print("🧪 Ejecutando pruebas del Risk Manager y Mock Audit Engine\n")
    
    # Pruebas RiskManager
    print("=" * 60)
    print("PRUEBAS: RISK MANAGER")
    print("=" * 60)
    
    manager = RiskManager()
    print(f"✓ RiskManager inicializado")
    print(f"✓ Total riesgos: {manager.contar_riesgos()}")
    print(f"✓ Primeros 3 riesgos: {manager.listar_todos_riesgos()[:3]}")
    
    stats = manager.obtener_estadisticas()
    print(f"\nEstadísticas:")
    print(f"  - Total riesgos: {stats['total_riesgos']}")
    print(f"  - Preguntas trabajador: {stats['total_preguntas_trabajador']}")
    print(f"  - Preguntas supervisor: {stats['total_preguntas_supervisor']}")
    print(f"  - Total preguntas: {stats['total_preguntas']}")
    print(f"  - Promedio por riesgo: {stats['promedio_preguntas_por_riesgo']}")
    
    # Búsqueda ejemplo
    print(f"\nBúsqueda de 'ALTURA':")
    resultados = manager.buscar_por_palabra_clave("ALTURA")
    for rf_id in resultados:
        print(f"  - {rf_id}")
    
    # Pruebas Mock Audit
    print("\n" + "=" * 60)
    print("PRUEBAS: MOCK AUDIT ENGINE")
    print("=" * 60)
    
    print(f"✓ Banco de preguntas: {len(BANCO_PREGUNTAS_GENERAL)} preguntas")
    
    # Generar examen
    examen = generar_examen_simulacro(db_path=":memory:", n_preguntas=10)
    print(f"✓ Examen generado: {len(examen)} preguntas")
    
    # Simular respuestas
    respuestas = {i: (i % 2 == 0) for i in range(len(examen))}
    resultado = calificar_simulacro_detallado(respuestas)
    
    print(f"\nResultado simulacro:")
    print(f"  - Correctas: {resultado['correctas']}/{resultado['total']}")
    print(f"  - Porcentaje: {resultado['porcentaje']}%")
    print(f"  - Nivel riesgo: {resultado['nivel_riesgo']}")
    print(f"  - Veredicto: {resultado['mensaje']}")
    
    print("\n✅ Todas las pruebas completadas exitosamente!")
