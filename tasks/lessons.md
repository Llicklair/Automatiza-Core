# Lecciones aprendidas

Registro de patrones detectados durante el trabajo para no repetir errores.

---

## 2026-05-02 — Verificar hallazgos de subagentes Explore antes de actuar

**Contexto:** Durante la auditoría Fase 1 de multi-tenancy (`docs/multitenancy/tenant_scoped_tables.md`), un subagente Explore reportó tres "hallazgos críticos". Al leer el código real, dos de los tres eran falsos positivos:

- `generative_ui.py:91` — el subagente vio `select(Client...)` en línea 91 y reportó "sin filtro tenant", pero la línea 92 contenía `.where(Client.tenant_id == tenant_id)`. El query SÍ filtraba.
- `DocumentEmbedding sin tenant_id` — el modelo en `embeddings.py:16` SÍ tiene `tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)`. El subagente reportó incorrectamente que no existía.
- `node_engine.py:334, 340` — query sin filtro de tenant pero NO vulnerable porque los IDs vienen de BD ya validada upstream (en endpoint y en `run_workflow`). Reportado como crítico pero realmente es solo "defensa en profundidad recomendable".

**Patrón:** Los subagentes Explore leen extractos limitados de archivos. Pierden contexto de:
- Métodos chained (`.where()` después del `select()` en línea siguiente)
- Validación upstream que ocurre fuera del archivo inspeccionado
- Constraints de seguridad en otra capa (endpoint, middleware, dependencia FastAPI)

**Regla:** Antes de aplicar correcciones a hallazgos reportados como "críticos" por un subagente:
1. Leer la función completa con la herramienta Read directamente.
2. Confirmar la cadena de validación upstream cuando un identificador entra como parámetro.
3. Reportar al usuario "hallazgo X confirmado" o "hallazgo X falso positivo" antes de editar código.

**Aplicación:** Esta regla se aplica especialmente cuando el subagente reporta "missing where" / "missing filter" / "missing validation" — estos patrones son los que más fácilmente generan falsos positivos por lectura parcial.
