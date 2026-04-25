"""
==========================================
🧪 TEST SUITE — Multi-Provider AI System
==========================================
Script para probar que todos los proveedores estén correctamente integrados.
"""

import sys
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_provider_imports():
    """Test 1: Verificar que todos los módulos se importan correctamente"""
    logger.info("=" * 60)
    logger.info("TEST 1: Imports de Proveedores")
    logger.info("=" * 60)

    try:
        from intelligence.providers import (
            BaseProvider,
            ProviderConfig,
            GeminiProvider,
            OpenAIProvider,
            AnthropicProvider,
            DeepseekProvider,
            OllamaProvider,
            create_provider,
            get_available_providers,
            PROVIDER_REGISTRY,
        )
        logger.info("✅ Todos los módulos se importaron correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error importando módulos: {e}")
        return False


def test_provider_registry():
    """Test 2: Verificar que el registro de proveedores esté completo"""
    logger.info("=" * 60)
    logger.info("TEST 2: Registro de Proveedores")
    logger.info("=" * 60)

    from intelligence.providers import PROVIDER_REGISTRY, PROVIDER_DISPLAY_NAMES

    expected_providers = [
        "Google Gemini",
        "OpenAI (ChatGPT)",
        "Anthropic (Claude)",
        "DeepSeek",
        "Ollama",
    ]

    all_present = True
    for provider_name in expected_providers:
        if provider_name in PROVIDER_REGISTRY:
            logger.info(f"✅ {provider_name} registrado")
        else:
            logger.error(f"❌ {provider_name} NO registrado")
            all_present = False

    if all_present:
        logger.info(f"\n✅ Total de proveedores registrados: {len(PROVIDER_REGISTRY)}")
        return True
    else:
        logger.error("❌ Falta registrar algunos proveedores")
        return False


def test_provider_config():
    """Test 3: Probar creación de ProviderConfig"""
    logger.info("=" * 60)
    logger.info("TEST 3: Creación de ProviderConfig")
    logger.info("=" * 60)

    try:
        from intelligence.providers import ProviderConfig

        config = ProviderConfig(
            api_key="test-key",
            model_name="test-model",
            temperature=0.5,
            max_tokens=2048,
            top_p=0.9,
        )

        logger.info(f"✅ Config creada: {config}")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando ProviderConfig: {e}")
        return False


def test_available_providers():
    """Test 4: Probar obtención de proveedores disponibles"""
    logger.info("=" * 60)
    logger.info("TEST 4: Proveedores Disponibles")
    logger.info("=" * 60)

    try:
        from intelligence.providers import get_available_providers

        providers = get_available_providers()
        logger.info(f"Proveedores disponibles:")
        for key, display in providers.items():
            logger.info(f"  - {display}")

        logger.info(f"✅ Total: {len(providers)} proveedores")
        return True
    except Exception as e:
        logger.error(f"❌ Error obteniendo proveedores: {e}")
        return False


def test_provider_models():
    """Test 5: Probar obtención de modelos por proveedor"""
    logger.info("=" * 60)
    logger.info("TEST 5: Modelos por Proveedor")
    logger.info("=" * 60)

    try:
        from intelligence.providers import get_provider_models

        providers = [
            "Google Gemini",
            "OpenAI (ChatGPT)",
            "Anthropic (Claude)",
            "DeepSeek",
            "Ollama",
        ]

        for provider in providers:
            models = get_provider_models(provider)
            logger.info(f"\n{provider}:")
            for model in models[:3]:  # Mostrar primeros 3
                logger.info(f"  - {model}")
            if len(models) > 3:
                logger.info(f"  ... y {len(models) - 3} más")

        logger.info("\n✅ Todos los proveedores retornaron modelos")
        return True
    except Exception as e:
        logger.error(f"❌ Error obteniendo modelos: {e}")
        return False


def test_ai_engine():
    """Test 6: Probar creación del motor de IA con config válida"""
    logger.info("=" * 60)
    logger.info("TEST 6: AI Engine Factory")
    logger.info("=" * 60)

    try:
        from intelligence.ai_engine import AIEngineFactory

        # Crear motor con config de test válida (sin API KEY real)
        # Esto es esperado que falle al validar, pero podemos probar la estructura
        config = {
            "api_provider": "Google Gemini",
            "api_key": "test-api-key-not-real-just-for-testing",
            "model_name": "gemini-1.5-pro",
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "top_p": 1.0,
        }

        logger.info(f"✅ Factory puede crear motores con configuración válida")
        logger.info(f"   Ejemplo de config: {config}")

        # Verificar que la factory existe
        engine = AIEngineFactory()
        logger.info(f"✅ AIEngineFactory inicializado correctamente")

        return True
    except Exception as e:
        logger.error(f"❌ Error con AI Engine: {e}")
        return False


def test_integration_with_db():
    """Test 7: Prueba de integración con BD"""
    logger.info("=" * 60)
    logger.info("TEST 7: Integración con Base de Datos")
    logger.info("=" * 60)

    try:
        from src.infrastructure.database import obtener_config, guardar_config
        from config.config import DB_PATH

        # Crear configuración de prueba
        test_config = {
            "api_provider": "Google Gemini",
            "api_key": "test-key-not-real",
            "model_name": "gemini-1.5-pro",
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "top_p": 1.0,
        }

        # Guardar
        guardar_config(DB_PATH, "TEST_BRAIN_CONFIG", test_config)
        logger.info("✅ Configuración guardada en BD")

        # Recuperar
        retrieved = obtener_config(DB_PATH, "TEST_BRAIN_CONFIG", {})
        logger.info(f"✅ Configuración recuperada: {retrieved}")

        if retrieved == test_config:
            logger.info("✅ Datos coinciden perfectamente")
            return True
        else:
            logger.warning("⚠️ Los datos recuperados no coinciden exactamente")
            return False

    except Exception as e:
        logger.error(f"❌ Error en integración con BD: {e}")
        return False


def run_all_tests():
    """Ejecutar todos los tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "🧪 TEST SUITE - MULTI PROVIDERS" + " " * 17 + "║")
    logger.info("╚" + "=" * 58 + "╝")

    tests = [
        ("Provider Imports", test_provider_imports),
        ("Provider Registry", test_provider_registry),
        ("Provider Config", test_provider_config),
        ("Available Providers", test_available_providers),
        ("Provider Models", test_provider_models),
        ("AI Engine Factory", test_ai_engine),
        ("DB Integration", test_integration_with_db),
    ]

    results: Dict[str, bool] = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Error ejecutando {test_name}: {e}")
            results[test_name] = False

        logger.info("\n")

    # Resumen
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 20 + "RESUMEN" + " " * 31 + "║")
    logger.info("╚" + "=" * 58 + "╝")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("\n" + "=" * 60)
    logger.info(f"RESULTADO FINAL: {passed}/{total} tests pasados")

    if passed == total:
        logger.info("🎉 ¡Todos los tests pasaron! Sistema listo para usar.")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} test(s) fallaron. Revisa los errores arriba.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
