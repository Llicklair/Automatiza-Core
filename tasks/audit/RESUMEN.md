# Auditoría profunda — AutomatizaCore (2026-06-19)

Monorepo: **73.136 LOC Python** (918 ficheros), 593 TS/TSX, 258 ficheros de test.
FastAPI + LangGraph backend · Next 16 / React 19 frontend · Electron desktop.
Dominio crítico: fiscalidad española AEAT + VeriFactu para pymes reales.

Informes por dimensión: `security.md`, `architecture.md`, `code-quality.md`,
`testing.md`, `fiscal.md`, `dependencies.md` (este directorio).

---

## Veredicto

Proyecto **maduro y notablemente bien construido** para un solo desarrollador:
RLS Postgres, backups E2E AES-256-GCM (PBKDF2 1M iter), bcrypt, validadores de
arranque que rechazan secretos por defecto, subprocess sin shell, DOMPurify,
2.193 tests backend que recogen sin errores, separación de capas real, VeriFactu
con gating defensivo correcto. **No es un prototipo.**

Los riesgos reales no son de "calidad" sino de **aislamiento multi-tenant** y
**dos huecos de corrección fiscal** que, dado que el usuario tiene clientes
pagando, son los que importan.

---

## CRÍTICO — actuar antes de más clientes

| # | Hallazgo | Fichero | Impacto |
|---|----------|---------|---------|
| C1 | **RLS fail-OPEN**: la policy devuelve filas de TODOS los tenants cuando `app.current_tenant` es NULL/`''`, y `db/rls.py` mapea a `''` cualquier tenant ausente/no-UUID. Un solo path que llegue a Postgres sin fijar tenant (bug, job, olvido) **filtra datos entre clientes** en silencio en vez de fallar. | `db/migrations/0016_sec_rls.py:43-56`, `db/rls.py` | Fuga de datos cross-tenant |
| C2 | **303 pierde el tipo de IVA 5%** (y 0%/exento): `collected_by_rate.get` solo lee 4/10/21%. Una línea al 5% desaparece de la casilla de IVA devengado → **IVA infradeclarado**. | `services/aeat/casillas_303.py:111-113` | Liquidación IVA incorrecta |

**C1** está parcialmente mitigado (el listener ahora se instala en todas las
sesiones), pero la policy sigue siendo fail-open por diseño. Arreglo correcto:
quitar las ramas NULL/`''` del `USING` → **fail-closed** con exenciones
explícitas para migraciones/pre-auth.

**C2**: verificar con el usuario si `fiscal.py` puede emitir filas al 5% (IVA
reducido temporal energía/alimentos). Si sí, mapear todos los tipos
dinámicamente, no hardcodear 4/10/21.

---

## ALTO

- **H1 — Scanner desactiva el backstop RLS**: `routes/scanner.py` nunca llama
  `set_current_tenant`; el aislamiento depende de que cada servicio recuerde su
  `WHERE`. El `scope` del token tampoco se valida. → fijar tenant en `get_scanner_user`.
- **H2 — `/auth/refresh` reemite tokens desde claims viejos**: no recarga el
  usuario (`services/auth/service.py:128`), usuarios desactivados/degradados
  conservan token 30 días; además es la única ruta auth **sin rate-limit**.
- **H3 — Modelo 111 no calcula retenciones de profesionales** (Art. 95 LIRPF
  15%/7%): falta el campo `Invoice.retencion_irpf`. Diferido a v1.1
  (`modelos_aeat.py:228`). Alto impacto si el cliente paga a profesionales.
- **H4 — Instalador Electron sin firmar + auto-update**: `forceCodeSigning:false`,
  `electron-updater` descarga/instala de GitHub sin verificación de certificado
  de editor. App fiscal → riesgo de cadena de suministro + avisos SmartScreen.
- **H5 — Backend sin lockfile y con `>=` sin pinear**: builds no reproducibles;
  el instalador desktop empaqueta el backend, así que cada build fija versiones
  distintas. (Frontend y desktop sí tienen `package-lock.json`.)

---

## MEDIO

- **M1 — XSS almacenado**: `MessageDetailModal.tsx:66` pinta HTML de email
  entrante con `dangerouslySetInnerHTML` sin sanitizar (existe `sanitizeHTML` y
  se usa en otros sitios). Combinado con JWT en localStorage → exfiltración.
- **M2 — Justificante/CSV simulado en path legacy**: `sede_client.submit_signed_xml(dry_run=True)`
  genera `fake_csv = uuid4().hex[:16]` y `build_acuse_text` lo imprime como
  "CSV (justificante)… Verificable en sede.agenciatributaria" sin marca de
  simulación. **Roza la línea roja** del proyecto. (El path nuevo VeriFactu y los
  PDF BORRADOR sí respetan la invariante.)
- **M3 — Redondeo inconsistente**: `_casilla.py:16`, `casillas_130.py:63`,
  `casillas_303.py:87` cuantizan sin `ROUND_HALF_UP` (default Python = HALF_EVEN),
  mientras `fiscal.py`/`billing/queries.py` usan HALF_UP. Puede divergir en x.xx5.
- **M4 — i18n roto y el check es ciego**: `check_i18n_parity.mjs` dice "OK 4817"
  pero solo compara es vs en. Real: es/en=4817, **ca/eu/gl=429** (~91% sin traducir).
- **M5 — Lógica de negocio en rutas** (viola ARCHITECTURE.md): `routes/marketing.py`
  (865 LOC, plan inline + 40 db calls), `routes/calendar.py` (4 queries cross-domain),
  `client_portal.py`. + `billing/commands.py:361` y `hr/commands.py:188` abren
  `AsyncSessionLocal()` propio rompiendo 1-transacción-por-request.
- **M6 — Lint falla**: `tsc --noEmit` = 0 errores ✅ pero `npm run lint` = 24
  warnings > techo de 20 → exit 1. Todos `react-hooks/exhaustive-deps`; 8 son
  auto-fixables y 5 son `eslint-disable` obsoletos.
- **M7 — 22 ficheros tragan `except Exception` sin logger**, incluyendo flujos de
  dinero/legal (`migration/bulk_import`, `treasury/sepa`, `tenant/certificates`,
  `signing/autofirma`).

---

## BAJO / deuda

- 261 `any` en TS (0 `@ts-ignore` — excelente). 35 ficheros con `eslint-disable`.
- God files: `modelos_aeat.py` (1048), `marketing.py` (865), `hr/queries.py` (841).
- ~20 env vars usadas sin documentar en `.env.example` (Telegram, Langfuse,
  Posthog, Redis, Backup_*).
- Floors viejos: `cryptography>=43`, `lxml>=4.9.0`, `python-jose>=3.3.0`
  (PyJWT ya presente → jose podría retirarse).
- GitNexus index **stale** → reindexar (`npx gitnexus analyze`).

---

## Cobertura de tests — huecos críticos

- **RLS / multi-tenant efectivamente sin test**: conftest usa SQLite, no ejecuta
  policies Postgres. El aislamiento (C1) no está cubierto. → test de integración
  con Postgres real.
- **SEPA/pagos fino**: 1 e2e, sin unit del XML de remesa.
- CI: backend sólido (Postgres real + `--cov-fail-under=57`), pero **mypy y
  `ruff format` son advisory (continue-on-error)** y la cobertura frontend es
  cosmética (~2.7%).

---

## Plan de acción recomendado (orden)

1. **C1** RLS fail-closed + **test de integración Postgres** que pruebe el aislamiento.
2. **C2 + M3** Mapear todos los tipos de IVA dinámicamente + unificar ROUND_HALF_UP.
3. **H1/H2** Fijar tenant en scanner + recargar usuario y rate-limit en `/refresh`.
4. **M1** Sanitizar el HTML de email entrante.
5. **M2** Marcar el CSV simulado como tal (o no almacenarlo).
6. **H4/H5** Firmar instalador + lockfile Python (`pip-tools`/`uv`).
7. Resto (lint, i18n parity check, logging en swallows, split god files): higiene continua.
