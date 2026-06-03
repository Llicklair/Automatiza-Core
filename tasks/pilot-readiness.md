# Pilot-readiness — ¿qué bloquea de verdad dárselo a UNA asesoría?

Fecha: 2026-06-03. Auditoría del flujo real install → primer valor.

## TL;DR (la verdad incómoda)
El producto está **completo en features** pero **una asesoría real NO puede sacar valor el día 1**:
1. La **IA no funciona out-of-the-box** (el proveedor por defecto necesita el CLI de Claude que no tendrán; y configurar una API key está escondido y no avisa).
2. El **instalador no está firmado** (SmartScreen "editor desconocido") y el **auto-update está roto** en el artefacto actual.

Eso —no más fusiones ni features— es lo que separa esto de un piloto. La mayoría son tu decisión/acción (firma, Google, modelo de coste); 2-3 los puedo arreglar yo en código.

---

## Bloqueantes (ordenados por impacto)

### 1. 🔴 La IA no arranca para un usuario real  — el más grave
- `DEFAULT_LLM_PROVIDER="claude_code"` ([config.py:46]) y `TenantLlmConfig.active_llm_provider` default `claude_code` → requiere el **CLI de Claude Code** instalado y logueado. Una asesoría en su Windows **no lo tiene**.
- Si no hay CLI ni API key, al usar IA se devuelve **texto de error** ("Claude Code CLI no encontrado"), sin fallback ni aviso útil ([llm/claude_code.py]).
- **No hay paso de API key en el onboarding** (ni en bienvenida 4-pasos ni en primeros-pasos). El usuario ve "habla con la IA" pero no se le guía a configurarla.
- **Decisión de negocio tuya (pivotal):** ¿el piloto usa **tu** key central (tú pagas el consumo de 1 asesoría) o **BYOK** (ellos traen su key)? Para un piloto, lo pragmático es key central.
- **Quién:** decisión tuya + yo puedo: (a) cambiar el default para que NO crashee, (b) detectar "IA sin configurar" y mostrar aviso + enlace, (c) meter el paso de API key en el onboarding.

### 2. 🔴 Instalador sin firmar → SmartScreen  — fricción que aborta instalaciones
- `electron-builder` sin code-signing (`forceCodeSigning:false`, sin `winCodeSign`) ([desktop/package.json]). NSIS sin firma = aviso "editor desconocido" en cada instalación limpia. Un gestor no técnico se asusta.
- **Quién:** tú (comprar un certificado de firma de código, ~200-400€/año) — yo no puedo.

### 3. 🟠 Auto-update roto en el artefacto enviado
- El updater está bien cableado (`electron-updater`), pero el `publish` del build tiene repo placeholder (`owner: TU_USUARIO_GITHUB`) → el `.exe` actual **no encuentra updates**. Sin esto, cada fix = reinstalar.
- **Quién:** yo arreglo la config `publish` (owner/repo `Llicklair`); tú publicas releases en GitHub.

### 4. 🟠 La subida de certificado AEAT falla (bug real)
- La clave auto-generada es `base64url` (43 chars). `encryption.py` lo tolera (fallback PBKDF2), pero `aeat/certificate_storage.py` llama a `Fernet(key)` **directo, sin fallback** → `CertificateError` al subir el .p12. Cualquiera que use firma/e-factura lo peta.
- **Quién:** yo (añadir el mismo fallback que ya tiene encryption.py). Arreglo pequeño y claro.

### 5. 🟠 OAuth Google en modo Testing + client vacío
- `GOOGLE_CLIENT_ID` vacío en el `.env` enviado + app Google en **Testing** → refresh tokens caducan ~7 días → cada piloto pierde Gmail/Drive semanalmente hasta reconectar.
- **Quién:** tú (verificar la app en Google Console / pasar a Production); yo puedo dejar el client id real si me lo das.

---

## Fricción / UX (no bloquean, pero dañan la primera impresión)
- **Primer arranque pesado**: Postgres + Python + JRE + pip se **descargan** en el primer lanzamiento (cientos de MB, 10-20 min tras un splash). Frágil con red mala. (Mejora: bundlear binarios.)
- **Dashboard vacío** sin datos demo ni CTA "crea tu primera factura". Dos flujos de onboarding solapados (bienvenida 4 pasos vs primeros-pasos 9). Confunde.
- **Backup**: no hay job automático garantizado a nivel desktop; `secrets.dat` es punto único (si se pierde APPDATA, credenciales irrecuperables).

---

## Camino recomendado al primer piloto (lo mínimo de verdad)
Para poder sentar a UNA asesoría a usarlo:
1. **Resolver la IA** (bloqueante #1): decidir key central vs BYOK; que no crashee sin config; meter el paso de key en onboarding + aviso claro. ← *empezar aquí*
2. **Arreglar el bug del certificado AEAT** (#4) si el piloto va a firmar/e-facturar.
3. **Arreglar el `publish` del updater** (#3) para poder mandarles fixes sin reinstalar.
4. **Firmar el instalador** (#2) — tu acción; o, para 1 piloto cercano, instalárselo tú en persona y saltarte SmartScreen manualmente.
5. **OAuth** (#5) solo si el piloto depende de Gmail/Drive; si no, diferir.

Lo demás (bundling, datos demo, unificar onboarding, backups) es importante pero **después** de tener a alguien usándolo.

## Qué puedo hacer YO ya (código), si quieres
- #4 cert AEAT (fallback Fernet) — pequeño, con test.
- #1 UX: "IA no configurada" → aviso + enlace; paso de API key en el onboarding; default que no crashee.
- #3 config `publish` del updater.
Lo de firma (#2), Google (#5) y la decisión de coste de IA (#1) son tuyas.
