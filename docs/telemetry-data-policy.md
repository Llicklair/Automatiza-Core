# Política de datos de telemetría — AutomatizaPyme

> **Cumplimiento**: RGPD Art. 5.1.e (minimización + limitación del plazo),
> Art. 7 (consentimiento informado), Art. 17 (derecho de supresión).
> **Implementación**: `app/core/telemetry_scrubber.py` (AI.SCR), modelo
> `TelemetryOptOut` (AI.REV), job de retención (AI.RET).

## §1 Promesa al usuario

> *"Tu base de datos vive en tu equipo. Nunca enviamos tus datos de negocio
> sin tu permiso explícito."* (A.9bis consensuado)

**Datos de negocio** = facturas, clientes, NIFs, IBANs, importes, nóminas,
contabilidad, contenido de prompts y outputs de agentes. Estos nunca salen
del equipo del cliente.

**Datos técnicos** = información de uso del software (versión, errores,
performance) que puede enviarse opcionalmente y solo con consentimiento.

## §2 Whitelist de campos enviados

Solo los siguientes campos se aceptan en el evento de telemetría
(`scrub_event()` filtra el resto):

| Campo | Tipo | Origen | Notas |
|---|---|---|---|
| `tenant_id_hash` | string(16) | derivado | SHA-256(salt + tenant_id), salt rotada 90d |
| `app_version` | string | constante | versión semántica de la build |
| `os_family` | string | runtime | "windows", "macos", "linux" (no build exacto) |
| `python_version` | string | runtime | "3.11", "3.12" — sin patch |
| `error_class` | string | excepción | clase de la excepción (`ValueError`, etc.) |
| `error_message` | string | excepción | truncado a 200 chars + scrubbed |
| `stack_trace` | string | excepción | rutas convertidas a `<APP>/...` |
| `tool_name` | string | agente | nombre de la tool LLM invocada |
| `model_used` | string | agente | proveedor + modelo LLM |
| `agent_name` | string | agente | nombre del agente que generó el evento |
| `level` | string | logger | "info", "warning", "error" |
| `release` | string | constante | build/commit identifier |
| `timestamp` | ISO 8601 | runtime | fecha-hora del evento |
| `transaction` | string | runtime | endpoint o operación |

**Prohibido** (eliminado por scrubber): paths completos, `tenant_id` plano,
nombres de archivo del cliente, contenido de prompts, contenido de tool args,
IPs, user-agents (fuera del cliente), NIFs (regex), IBANs (regex), emails,
números de tarjeta.

## §3 Retención (AI.RET)

| Tipo | Plazo | Justificación |
|---|---|---|
| **Eventos individuales** | 90 días | Ciclo de release típico — un bug detectado se corrige en una release. Después no necesita el evento original |
| **Agregados estadísticos** | 18 meses | Sin `tenant_id_hash`, solo counters por `app_version`/`error_class`. Permite análisis de tendencia sin re-identificación |
| **K-anonymity** | ≥ 5 | Cohorts con count < 5 se descartan al agregar (impide re-identificación por intersección de atributos) |

Implementación: job de purga programado en Sentry self-hosted ejecuta
`DELETE FROM events WHERE created_at < NOW() - INTERVAL '90 days'`. Los
agregados se generan con un cron que descarta cohorts de tamaño < 5.

## §4 Revocación (AI.REV)

El usuario puede:

1. **Desactivar telemetría globalmente** vía `Settings → Privacidad →
   Avanzado` con texto literal *"renuncio a la revisión por incidente y
   autorizo a AutomatizaPyme a enviar informes técnicos sin pedirme
   confirmación cada vez. Mantengo el derecho a revocar este consentimiento
   en cualquier momento y a solicitar el borrado de los datos enviados."*

2. **Solicitar borrado** de eventos asociados a su tenant vía
   `DELETE /api/v1/telemetry/me` (autenticado). El backend:
   * Marca el tenant como `telemetry_opt_out=True`.
   * Lanza job que purga eventos del VPS con `tenant_id_hash` calculado
     con la salt activa actual.
   * Para eventos >90d con salt rotada, no son re-identificables y por
     tanto no son dato personal bajo RGPD — no aplica derecho de supresión
     (Recital 26 RGPD).

3. **Recibir confirmación** del borrado en correo electrónico del usuario
   en un plazo máximo de 30 días naturales (RGPD Art. 12.3).

## §5 Salt por incidente

La salt para `hash_tenant_id()`:

* Se rota cada 90 días o ante incidente de seguridad.
* Se almacena solo en el VPS (no en el cliente).
* No se reutiliza nunca.
* Su rotación rompe la correlación entre informes — la AEPD no puede
  argumentar trazabilidad cruzada entre periodos.

## §6 Base jurídica

* **Consentimiento explícito** (RGPD Art. 6.1.a) — opt-in por defecto,
  configurable en Settings.
* **Pseudonimización** (RGPD Art. 4.5) — `tenant_id` nunca sale sin hash
  con salt.
* **Privacy by design** (RGPD Art. 25) — scrubber aplicado en el origen,
  no en el destino (Sentry no puede recibir lo que ya fue redactado).

## §7 Punto de contacto

Cualquier consulta sobre tratamiento de datos de telemetría:
**privacidad@automatizapyme.com** (DPD designado conforme RGPD Art. 37 si
procede). Plazo respuesta: 30 días naturales.
