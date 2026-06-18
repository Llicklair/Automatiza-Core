# Evaluación global del proyecto — AutomatizaCore / Zernio

> Nota como **artefacto técnico/producto**, EXCLUYENDO clientes/comercial (validación de mercado, ingresos, contratos). Fecha: 2026-06-17.

## Nota global: **7.2 / 10** — _producción temprana, alta (early production, upper tier)_

Rango de confianza: **6.8 – 7.5**. La nota es robusta porque las seis dimensiones convergen en una banda estrecha (7 – 8) y la evidencia citada es verificable y consistente. El margen bajo refleja una incógnita real: las dos integraciones externas críticas (SEDE AEAT, banca PSD2) están sin cablear, lo que no se puede "puntuar al alza" sin verlas funcionar end-to-end.

---

## Tabla de dimensiones

| Dimensión | Nota | Peso | Aporte ponderado | Madurez |
|---|---:|---:|---:|---|
| Arquitectura | 7.0 | 22% | 1.54 | producción-temprana |
| Calidad de código | 7.0 | 20% | 1.40 | producción-temprana |
| Completitud funcional | 7.0 | 22% | 1.54 | producción-temprana |
| Seguridad | 7.5 | 16% | 1.20 | producción-temprana |
| Deuda técnica | 8.0 | 12% | 0.96 | producción-madura |
| Documentación y operabilidad | 7.0 | 8% | 0.56 | producción-temprana |
| **Global (suma ponderada)** | **7.20** | 100% | **7.20** | **producción-temprana (alta)** |

## Justificación de la ponderación

- **Arquitectura, Completitud y Calidad pesan más (22/22/20%)**: son lo que determina si el sistema *es* un producto sólido y *evoluciona* sin colapsar. En un SaaS fiscal multi-tenant, una arquitectura con fronteras reales y una funcionalidad genuinamente ancha son el activo central; la calidad del código es su sostenibilidad.
- **Seguridad pesa alto (16%) pero por debajo del trío núcleo**: es crítica (datos fiscales, multi-tenant), pero aquí ya está *resuelta a buen nivel* (7.5) con defensa en profundidad real; no es el cuello de botella que define la nota. Si tuviera un agujero de libro, habría subido su peso a la fuerza.
- **Deuda técnica pesa menos (12%)**: es una métrica de *salud y mantenimiento*, no de capacidad. Una deuda baja (8.0) es excelente higiene, pero no compensa que falten integraciones; pesar la pulcritud igual que la arquitectura sobrevaloraría la limpieza sobre la sustancia.
- **Documentación y operabilidad pesa menos (8%)**: importa para onboarding y soporte, pero su drift no rompe el producto en producción (solo a un dev nuevo). Es la dimensión menos definitoria del valor técnico.

---

## 3 fortalezas clave

1. **Aislamiento multi-tenant con defensa en profundidad real** _(Seguridad / Arquitectura)_: RLS de Postgres con `FORCE` + rol `NOBYPASSRLS`, listener SQLAlchemy que re-asserta `SET LOCAL app.current_tenant` en cada statement (~166 puntos de apertura de sesión cubiertos), `enforce_tenant` que neutraliza prompt-injection del LLM, **más** filtrado manual por `tenant_id`. Cuatro capas, no una.
2. **Núcleo fiscal de alta fidelidad y verificado** _(Completitud / Testing)_: casillas AEAT (303/130/111/115/390) mapeadas a BOE, cadena VeriFactu (RD 1007/2023) validada contra el vector oficial de la AEAT con advisory locks, y ~2150 tests backend con aserciones numéricas exactas como guardas de regresión sobre lógica legalmente sensible.
3. **Deuda técnica notablemente baja con prevención mecanizada** _(Deuda técnica / Arquitectura)_: 2 TODOs reales en ~649 ficheros, cero FIXME/HACK, cadena de 62 migraciones Alembic perfectamente lineal, y tooling (ruff+mypy+pytest+ESLint+CI) realmente *enforced* — más documentación arquitectónica excepcionalmente honesta que enumera sus propias excepciones.

## 3 riesgos/debilidades clave

1. **Las dos integraciones externas críticas no existen end-to-end** _(Completitud funcional)_: presentación a SEDE AEAT es `dry_run` (CSV ficticio, sin POST) y la banca PSD2 cae a datos demo (sin cliente Nordigen/GoCardless). Toda la lógica existe, pero el último tramo regulatorio/de terceros —el que cierra el ciclo de valor— está sin cablear. Es el mayor freno a la nota.
2. **Fronteras de capa rotas en ~21% de la superficie HTTP** _(Arquitectura / Calidad)_: 14/66 rutas mutan BD inline (`marketing.py` con 19 mutaciones, `email_marketing.py` con 12), violando su propia regla "Routes = ZERO business logic". Es deuda localizada y reconocida, pero erosiona la consistencia que el resto del sistema sí mantiene.
3. **La barrera de seguridad fuerte es fail-open + la prueba de aislamiento real no se ejercita** _(Seguridad / Testing)_: la policy RLS devuelve TODAS las filas si `app.current_tenant` es NULL/'' (deliberado, pero convierte un olvido de `set_current_tenant` en fuga cross-tenant), **y** los tests corren sobre SQLite en memoria, por lo que las policies RLS de Postgres no se prueban realmente. La defensa más importante depende de una red de seguridad (filtrado manual) que no está verificada a nivel de BD.

---

## Qué subiría / bajaría la nota

**Subiría a 8 – 8.5 si:**
- Se cablea la SEDE AEAT real (POST con certificado + XSD oficial) y un agregador PSD2 real → cierra el ciclo fiscal/bancario end-to-end (+0.5–0.8, Completitud).
- Se ejercitan las policies RLS contra Postgres real en CI (no SQLite) → la barrera dura pasa de "asumida" a "verificada" (+0.3, Testing/Seguridad).
- Se sanean las ~14 rutas con mutación inline delegando a servicios → cierra la inconsistencia de capas (+0.2, Arquitectura).

**Bajaría a 6 – 6.5 si:**
- Se descubre que el `dry_run` de AEAT oculta supuestos incorrectos sobre el protocolo real (riesgo no medible hasta cablearlo).
- La política RLS fail-open + ausencia de test Postgres real produjera una fuga cross-tenant en producción (impacto crítico en un SaaS fiscal).
- El mojibake UTF-8 y los `any` concentrados resultaran síntoma de un proceso de revisión más laxo de lo que sugiere el resto.

---

## Veredicto

**Es un ERP/SaaS fiscal multi-tenant de producción temprana, técnicamente serio y ancho, construido con estándares casi-senior y disciplina arquitectónica real, cuya única barrera para ser "producción madura" no es la calidad sino el último tramo de integración regulatoria/bancaria que queda deliberadamente y honestamente sin cablear.**
