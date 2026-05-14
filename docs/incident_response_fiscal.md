# Runbook incidente fiscal del cliente — OPS.RUN

> **Crítico**: este runbook es **condición previa al pago de siniestro** en pólizas E&O Hiscox / AIG CyberEdge / Markel Pro IT (consensuado en Ronda 12 §63). Sin runbook documentado, el seguro puede rechazar la cobertura aunque esté contratado.
>
> Activación: cuando un cliente reciba paralela AEAT, comunicación previa, requerimiento o sanción derivada (presuntamente) de un cálculo o presentación realizada por AutomatizaPyme.

## §1 Personas designadas

* **Coordinador de incidentes** (interno): fundador o, si existe, el customer success / data protection officer.
* **Abogado**: el contratado en DEC.06 (~800-1.500€ una vez + retainer si fuera necesario).
* **Asegurador**: contacto del broker E&O.
* **Cliente afectado**: identidad confirmada con `tenant_id` + email registrado.

## §2 Plazos clave

| Paso | Plazo desde recepción |
|---|---|
| Acuse de recibo al cliente | < 24h hábiles |
| Recopilación de evidencia técnica | < 48h hábiles |
| Análisis preliminar de responsabilidad | < 7 días naturales |
| Comunicación oficial al cliente con próximos pasos | < 10 días naturales |
| Notificación al asegurador E&O | **< 30 días naturales** (típico requisito de póliza) |

## §3 Recopilación de evidencia técnica

Desde la BD del cliente (con acceso autorizado o con el cliente en pantalla compartida):

1. **`audit_log`** filtrado por `tenant_id` + ventana temporal del incidente. Buscar entradas de `agent_name` correspondiente.
2. **`agent_execution_trace`** para la operación concreta: prompt_hash + model_used + tokens + tool_calls.
3. **`fiscal_approval_log`** verificar que el modelo presentado tuvo aprobación humana firmada + IP + texto canónico. Si NO la tuvo: bug del sistema (responsabilidad del proveedor).
4. **`verifactu_chain`** verificar integridad con `verify_chain_integrity(tenant_id)`. Si rota: incidente técnico grave.
5. **`backup_record`** verificar último backup pre-incidente para poder reconstruir estado de la BD en el momento.

Exportar todo lo anterior como bundle de diagnóstico (`/api/v1/system/diagnostic-bundle`) y guardarlo en repositorio interno seguro etiquetado con el ID del incidente.

## §4 Análisis de responsabilidad

Cuatro escenarios posibles, en orden de responsabilidad de AutomatizaPyme S.L.:

### Escenario A — Bug del software (responsabilidad del proveedor)

* Síntoma: `audit_log` muestra cálculo erróneo, fórmula incorrecta, dato omitido por bug, error de XSD/format.
* `fiscal_approval_log` muestra aprobación humana, pero los datos aprobados ya estaban mal calculados.
* **Acción**: AutomatizaPyme asume responsabilidad. Activar E&O. Compensar al cliente la sanción si el seguro lo cubre.

### Escenario B — Datos del cliente incorrectos (responsabilidad del cliente)

* Síntoma: el cálculo del software es correcto sobre los datos que recibió. Los datos los introdujo el cliente.
* `agent_execution_trace` muestra que el usuario aportó los datos vía formulario o tool del agente.
* **Acción**: explicar al cliente con evidencia. No procede E&O (responsabilidad contributiva del cliente). Ofrecer asistencia para corregir.

### Escenario C — Aprobación humana omitida o saltada (responsabilidad compartida)

* Síntoma: el modelo se presentó sin `fiscal_approval_log` válido, o el `payload_hash` aprobado no coincide con el presentado.
* **Acción**: si fue por bug → escenario A. Si fue por el cliente saltándose el flow → responsabilidad compartida; ofrecer mediación.

### Escenario D — Cambio normativo posterior (responsabilidad mitigada)

* Síntoma: AEAT publica criterio interpretativo después de la presentación.
* **Acción**: documentar que en la fecha de presentación el sistema cumplía la normativa vigente. Ofrecer al cliente recurso administrativo (TEAR) con asesoría legal.

## §5 Comunicación al cliente

### Plantilla de acuse inicial (24h)

> Estimado/a [nombre],
>
> Hemos recibido tu comunicación de [fecha] relativa al [requerimiento/paralela/sanción] [referencia AEAT]. Hemos abierto el incidente número [ID-INTERNO] y nuestro equipo está revisando los registros técnicos asociados a tu tenant.
>
> Recibirás un análisis preliminar en un plazo máximo de 7 días naturales con próximos pasos. Si lo necesitas urgentemente, contacta directamente con [coordinador] en [email].
>
> Conforme al Reglamento UE 2024/1689 (AI Act), Art. 26.5, esta comunicación queda registrada en nuestro audit log y se conservará durante un mínimo de 6 meses junto con la evidencia técnica del caso.
>
> [Firma del coordinador]

### Plantilla de análisis completado (10 días)

Estructura: hechos + escenario aplicable (A/B/C/D) + acciones que asume AutomatizaPyme + acciones que recomendamos al cliente + relación con la póliza E&O.

## §6 Notificación al asegurador E&O

Documentación requerida típicamente:

* Bundle de diagnóstico completo.
* Análisis técnico de responsabilidad (escenario aplicable).
* Comunicaciones intercambiadas con el cliente hasta la fecha.
* Documentación de la AEAT (paralela, sanción, etc.).
* Si procede: cuantía estimada del perjuicio.

Plazo: ≤ 30 días naturales desde notificación inicial del cliente.

## §7 Post-mortem técnico interno

Independiente del análisis de responsabilidad, **todo incidente que llegue a esta página dispara un post-mortem en `tasks/lessons.md`**:

* Causa raíz.
* Cómo se detectó.
* Cómo se mitigó.
* **Cambio en el código / proceso / prompt para que no se repita.**
* Si afecta a otros tenants: comunicación proactiva.

## §8 Revisión de este runbook

Trimestral. Cambios significativos requieren revisión adicional por abogado contratado en DEC.06. Versión actual: **1.0 — 2026-05-14**.
