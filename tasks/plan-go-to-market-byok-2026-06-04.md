# Plan de acción go-to-market — modelo BYOK

> Fecha: 2026-06-04 · Fundador: Llicklair
> Decisión fijada: **BYOK ("trae tu clave")**. El usuario aporta y paga su clave LLM (Anthropic / OpenAI / Groq…). AutomatizaPyme **no suministra IA ni asume su coste**.
> Fuentes: `tasks/pilot-readiness.md`, `tasks/iteracion_fallos_ERP_2026-06-03.md`, `consejo-report-20260602…md`, `roadmap.md`, `MARKETING.md`, `docs/guia-piloto.md`.

---

## 0. Qué cambia al fijar BYOK

Fijar BYOK **resuelve el bloqueante #1** del `pilot-readiness` (queda descartada la "key central"), pero traslada el peso a la experiencia de configuración:

- Como nada de IA funciona sin la clave del usuario, el **paso de API key en el onboarding** y el **aviso "IA no configurada"** dejan de ser opcionales: son el **primer punto de fricción del producto** (P0), sobre todo para un gestor no técnico.
- El **coste de IA es del usuario** → hay que comunicarlo sin letra pequeña ("pagas tu consumo directamente al proveedor; típicamente unos pocos € al mes").
- **Revisar el pricing de `MARKETING.md`**: el "soft cap 500 interacciones/mes + overage 0,05€/interacción" se diseñó asumiendo que *tú* pagabas los tokens. Bajo BYOK el usuario ya paga su consumo → cobrar overage por interacción **deja de tener sentido**. Recomendado: eliminar el overage y, como mucho, dejar un *fair-use* solo en cron/automatizaciones para proteger recursos locales. (Decisión de negocio — ver §4.)

---

## 1. Bloqueantes de CÓDIGO (tuyos · horas–días)

Ordenados por impacto/desbloqueo. Todos sin dependencias externas.

| # | Fix | Archivo(s) | Esfuerzo | Depende de |
|---|-----|-----------|----------|-----------|
| C1 | **BYOK que no rompe**: default LLM que no crashee sin clave + detección "IA no configurada" → aviso ámbar + enlace + **paso de API key en onboarding** | `core/config.py` (default `claude_code`→seguro), `llm/claude_code.py`, onboarding (bienvenida 4 pasos / primeros-pasos) | 1–2 d | — |
| C2 | **Bug cert AEAT**: `Fernet(key)` directo sin fallback PBKDF2 → `CertificateError` al subir el .p12 | `aeat/certificate_storage.py` (replicar fallback de `encryption.py`) + test | 2–4 h | — |
| C3 | **Auto-update**: `publish` con owner placeholder → el .exe no encuentra updates | `desktop/package.json` (`build.publish` → owner/repo `Llicklair`, repo de releases **público**) | 1–2 h | repo releases público |
| C4 | **QA.E2E Playwright** (signup → factura → 303): único TODO técnico del roadmap sin bloqueos externos | `frontend` (Playwright) | ~2 d | — |

> C1 y C2 son los que de verdad separan el piloto de "no se puede usar". C3 evita reinstalar en cada fix.

---

## 2. FIABILIDAD del motor IA (medir antes de invertir)

Del smoke 03-jun (24/29). Los fallos son de 3 causas raíz, **dominadas por el provider `claude_code`** — que en BYOK **no es el provider real** (lo será `anthropic`, con tool-calling nativo).

| # | Acción | Por qué | Esfuerzo |
|---|--------|---------|----------|
| F1 | **Medir la batería con `anthropic`** (el provider real BYOK) antes de tocar nada | Aísla cuántos fallos son solo de `claude_code` (rehúsa tools de forma no determinista). Probablemente varios desaparecen | 0,5 d |
| F2 | Coordinador: entrada ambigua / entidad inexistente → **pedir aclaración**, no alucinar y ejecutar un plan | Causa raíz C. Riesgo real: ejecutar operaciones inventadas | 1–2 d |
| F3 | Timeout 180s + **degradación parcial** de la cadena (continuar pasos independientes, reportar el fallido) en vez de abortar todo | Causa raíz B | 1 d |
| F4 | (Solo si F1 lo justifica) endurecer prompt de tools / reintento en `claude_code` | Causa raíz A — baja prioridad si el piloto va con `anthropic` | 0,5–1 d |

---

## 3. ENDURECER EL CAMINO DEL DINERO (antes del primer cliente de pago)

Del `consejo-report`. Es lo que convierte un demo en algo que un gestor confía con dinero real.

| # | Acción | Estado actual | Esfuerzo |
|---|--------|---------------|----------|
| M1 | **Límites de importe inline** en writes financieros | `create_journal_entry`, `create_invoice`, `approve_payroll` sin cap | 1 d |
| M2 | **Aprobación human-in-the-loop por umbral configurable** | Guardian: **0 matches** de `requires_approval` en todo el backend | 2–3 d |
| M3 | **Persistir el tracker de gasto LLM a BD** | hoy `defaultdict` en memoria, se pierde al reiniciar (`token_ledger` per-employee existe; falta agregado tenant) | 1–2 d |
| M4 | **Dashboard de uso/coste IA por tenant** | `/llm-usage/stats` ya existe; falta UI | 1–2 d |

> Nota BYOK: M3/M4 siguen siendo valiosos (el usuario quiere ver **su** gasto en el proveedor), pero ya no son para facturarle a él — son transparencia, no metering de cobro.

---

## 4. TRÁMITES y DECISIONES externas (tuyas · semanas — empezar YA en paralelo)

El cuello de botella real ya no es código. Estos corren en calendario, no en commits → **arráncalos esta semana**.

| # | Trámite / decisión | Plazo | Desbloquea | Coste aprox. |
|---|--------------------|-------|-----------|--------------|
| E1 | **Alta colaborador social AEAT** (vía gestor) | 4–6 semanas | Presentación telemática de modelos | gestor ~600–1.000€ |
| E2 | **Cert de pruebas FNMT** (online) | 10 min, gratis | Homologación M3/M4/M5 | 0€ |
| E3 | **Certificado Code Signing EV** | días | Instalador firmado (sin SmartScreen) + M5 | ~400€/año |
| E4 | **Abogado SaaS** | — | EULA, DPA, dictámenes (incl. AI Act) | 800–1.500€ |
| E5 | **Póliza E&O / RC** | — | EULA y lanzamiento | ~1.800–2.400€ |
| E6 | **Pricing BYOK**: eliminar overage por interacción; definir fair-use solo de cron | decisión | Coherencia de planes | 0€ |
| E7 | Google OAuth → Production (solo si el piloto usa Gmail/Drive) | días | Evitar reconexión semanal | 0€ |
| E8 | Stripe vs Redsys (DEC.05) | decisión | Suscripciones | — |

---

## 5. SECUENCIA RECOMENDADA

**Semana 1 (esta)**
- Arrancar en paralelo, mismo día: E1 (gestor AEAT), E2 (FNMT), E3 (Code Signing), E4 (abogado). Son los de mayor latencia.
- Código: C2 (cert AEAT, 2–4 h) → C1 (BYOK onboarding, 1–2 d) → C3 (updater).
- F1: medir la batería con `anthropic`.

**Semana 2**
- C4 (E2E Playwright).
- F2 + F3 (robustez del coordinador y de las cadenas).
- E6: cerrar el pricing BYOK.

**Semanas 3–4**
- M1–M2 (caps + aprobación por umbral) → es lo que habilita "primer cliente de pago".
- M3–M4 (transparencia de gasto).
- Cuando llegue la homologación (depende de E1/E2): cerrar **un ciclo fiscal real con AEAT** = la validación que hoy falta.

**Gate para sentar a UNA asesoría a usarlo de verdad**: C1 + C2 + C3 hechos, F1 medido, instalador firmado (E3) o instalado en persona. El resto (bundling de binarios, datos demo, backups, unificar onboarding) es importante pero **después** de tener a alguien dentro.

---

## 6. Riesgos abiertos a vigilar

- **Cobertura de tests 0,17%** (113 tests / 67K LOC) sobre código que mueve dinero y modelos AEAT. Subir cobertura del camino del dinero antes de escalar.
- **Ningún ciclo fiscal cerrado con AEAT** todavía → "sustituye a tu gestoría" es promesa no validada hasta E1/E2 + homologación.
- **Primer arranque pesado** (descarga de Postgres/Python/JRE, 10–20 min): bundlear binarios mejora mucho la primera impresión.
- **`secrets.dat` punto único**: si se pierde APPDATA, credenciales irrecuperables → backup garantizado a nivel desktop.
