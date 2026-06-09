# SLA por tier — OPS.SLA

> Acuerdo de Nivel de Servicio consensuado en debate IA-1 ↔ IA-2 Ronda 8 §63 + Ronda 11 O.1. Tiered según los 3 niveles de pricing definidos en `MARKETING.md`.

## §1 Tiers

### Solo — 39€/mes

* **Soporte**: best-effort.
* **Canal**: email a `soporte@automatizacore.com`.
* **Tiempo de respuesta**: sin compromiso explícito. Resolución dentro de plazo razonable, normalmente <72h hábiles.
* **Cobertura**: lunes a viernes, 9:00 a 18:00 CET.
* **Knowledge base**: acceso completo a la KB pública.

### Pro — 65€/mes

* **Soporte**: L1 con SLA explícito.
* **Canal**: chat in-app (Crisp) + email.
* **Tiempo de respuesta L1**: 48 horas hábiles.
* **Tiempo de respuesta L2** (escalado por bug del software): mejor esfuerzo, parche en próxima release menor.
* **Cobertura**: lunes a viernes, 9:00 a 18:00 CET.
* **Knowledge base**: acceso completo + acceso anticipado a release notes.

### Gestoría — 159€/mes

* **Soporte**: L1 con SLA premium + canal directo.
* **Canal**: chat in-app + email + canal directo (email del fundador) para incidencias críticas.
* **Tiempo de respuesta L1**: 4 horas hábiles.
* **Tiempo de respuesta L2** (bug crítico que bloquea presentación AEAT): respuesta inicial en 2h hábiles + parche prioritario.
* **Cobertura**: lunes a viernes, 8:00 a 20:00 CET.
* **Knowledge base**: acceso completo + canal privado de discusión de roadmap.

## §2 Definición de "horas hábiles"

* Lunes a viernes, excluidos festivos nacionales españoles + autonómicos del territorio del cliente (en gestoría: festivos del territorio donde radique la sociedad).
* No se incluyen incidencias reportadas en sábado, domingo o festivo en el contador — el plazo arranca el siguiente día hábil a las 9:00 CET.

## §3 Definición de "incidencia"

Una incidencia es un reporte que **al menos cumple uno** de:

1. El software no arranca o el cliente no puede iniciar sesión.
2. Una operación crítica de facturación o presentación AEAT falla con error técnico.
3. Datos del cliente parecen corruptos o inconsistentes.
4. El sistema rechaza una operación legítima sin razón clara.
5. El cliente reporta sospecha de brecha de seguridad.

No son incidencias bajo SLA:

* Solicitudes de nuevas funcionalidades (van al roadmap).
* Consultas de cómo usar el software (van a la KB o a soporte sin SLA estricto).
* Problemas atribuibles a infraestructura del cliente (Postgres local corrupto por corte eléctrico, etc.) que el cliente puede resolver siguiendo la KB.

## §4 Procedimiento de escalado

1. **L1 (soporte de primer nivel)**: el cliente contacta por el canal del tier. Responde el equipo de soporte con resolución directa, redirección a KB o creación de ticket.

2. **L2 (escalado a ingeniería)**: si el L1 identifica un bug del software, crea ticket etiquetado con tier del cliente. Triaje en la siguiente reunión diaria del equipo dev.

3. **L3 (escalado al fundador)**: solo para tier Gestoría con incidencia crítica de presentación AEAT no resoluble en L2 dentro del plazo.

4. **Incidente AEPD** (sospecha de brecha de datos personales): runbook `docs/...` (TODO Sprint 9) + notificación AEPD en 72h conforme RGPD Art. 33.

## §5 Compensaciones por incumplimiento

* **Solo**: no aplica (best-effort).
* **Pro**: si el L1 supera las 48h hábiles sin respuesta inicial, el cliente recibe **un mes gratis** previa solicitud por escrito en los 30 días siguientes.
* **Gestoría**: si el L1 supera las 4h hábiles sin respuesta inicial Y la incidencia afecta a presentación AEAT con vencimiento <7 días, el cliente recibe **dos meses gratis** previa solicitud por escrito.

Las compensaciones no son acumulativas y se limitan a un máximo de 2 meses gratis por trimestre natural.

## §6 Integración Crisp chat (referencia)

Crisp ofrece chat in-app con widget JS embebido en el frontend Next.js. Coste: ~25€/mes para el plan necesario.

**TODO Sprint 7**: inicializar widget en `app/(dashboard)/layout.tsx` con configuración por tier (mostrar el widget solo a `Pro` y `Gestoría`). Plantear privacidad: el contenido del chat puede contener PII del usuario — Crisp es proveedor externo. Política de telemetría documenta cómo se trata.
