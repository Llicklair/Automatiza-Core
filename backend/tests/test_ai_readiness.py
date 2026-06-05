"""Tests del estado de configuración de IA (BYOK).

`evaluate_ai_readiness` es lógica pura: decide si la IA del tenant está lista
para usarse, de modo que el frontend muestre un aviso con enlace en vez de dejar
que la IA falle con un error críptico al primer uso. Punto clave del modelo BYOK:
el proveedor por defecto `claude_code` (CLI) NO está disponible para un usuario
final en producción.
"""

from app.services.tenant_service import evaluate_ai_readiness


def test_claude_code_no_listo_en_produccion():
    ready, reason = evaluate_ai_readiness("claude_code", {}, "production")
    assert not ready
    assert "Claves API" in reason


def test_claude_code_si_en_desarrollo():
    ready, _ = evaluate_ai_readiness("claude_code", {}, "development")
    assert ready


def test_claude_code_si_en_testing():
    ready, _ = evaluate_ai_readiness("claude_code", {}, "testing")
    assert ready


def test_claude_code_listo_si_cli_disponible():
    # Máquina del dev/fundador: el CLI está instalado → IA lista aunque el
    # entorno sea 'production'. (Evita el falso positivo del aviso.)
    ready, _ = evaluate_ai_readiness("claude_code", {}, "production", cli_available=True)
    assert ready


def test_claude_code_no_listo_si_cli_ausente():
    # Gestor típico con BYOK: sin el CLI → no listo, debe avisar.
    ready, reason = evaluate_ai_readiness("claude_code", {}, "production", cli_available=False)
    assert not ready
    assert "Claves API" in reason


def test_anthropic_con_clave_y_activado_listo():
    keys = {"anthropic": {"api_key": "sk-ant-xxx", "enabled": True}}
    ready, reason = evaluate_ai_readiness("anthropic", keys, "production")
    assert ready
    assert reason == "IA configurada."


def test_anthropic_sin_clave_no_listo():
    keys = {"anthropic": {"api_key": "", "enabled": True}}
    ready, reason = evaluate_ai_readiness("anthropic", keys, "production")
    assert not ready
    assert "Falta la clave" in reason


def test_anthropic_desactivado_no_listo():
    keys = {"anthropic": {"api_key": "sk-ant-xxx", "enabled": False}}
    ready, reason = evaluate_ai_readiness("anthropic", keys, "production")
    assert not ready
    assert "desactivado" in reason


def test_proveedor_vacio_no_listo():
    ready, reason = evaluate_ai_readiness("", {}, "production")
    assert not ready
    assert "proveedor" in reason.lower()


def test_openai_con_clave_listo():
    keys = {"openai": {"api_key": "sk-xxx", "enabled": True}}
    ready, _ = evaluate_ai_readiness("openai", keys, "production")
    assert ready
