# Prompts por rol custom — set definitivo

Custom employees disponibles (todos `is_builtin=false`, `status=idle`):

| Nombre | Rol | UUID corto |
|---|---|---|
| Marcos Recio | Director de Tecnología (CTO) | `6b1d51ac…` |
| Yolanda Sánchez | Directora Financiera (CFO) | `4eb5…` (consulta BD) |
| Kepler Nebular | Director Ejecutivo (CEO) | `29a3ce6a…` |
| Alicja Wiszczulis | Auditora Interna | `490ff0ae…` |

**Cómo deberían comportarse:** el planner asigna `agent="custom"` con el `employee_id` correcto **por encaje real con el rol**, sin que tú menciones a nadie por nombre. Cada rol tiene su carril: tareas tecnológicas → CTO; financieras → CFO; estratégicas/ejecutivas → CEO; auditorías/control → Auditora.

**Cambios recientes que afectan a estos prompts:**
- Timeout de agente custom subido a **180s** (antes 120s) — system_prompts largos ahora caben sin saltar TimeoutError.
- Errores vacíos eliminados — si algo falla, verás el motivo concreto en `Task.error_message` (timeout, type error, etc.).

---

## Prompt 1 — CTO (Marcos)

```
Mira qué procesos del negocio tenemos automatizados a día de hoy
y cuáles seguimos haciendo a mano. ¿Dónde se nos va más tiempo
en tareas repetitivas — clasificar documentos, escribir correos,
gestionar facturación, papeleo de RRHH? Dime las tres áreas
donde meter automatización daría más horas semanales al equipo.
```

**Encaje:** automatización de procesos, eficiencia operativa, evaluación técnica del estado actual. Es trabajo de Director de Tecnología.

**Esperado en `Task.plan`:** un nodo `agent="custom"` con `employee_id` = Marcos + 4 nodos builtin (documents, email, billing, hr) consultando datos para alimentar al CTO.

---

## Prompt 2 — CFO (Yolanda)

```
Necesito un análisis completo de la salud financiera del trimestre.
Revisa el flujo de caja, los días medios de cobro, las facturas
pendientes vs cobradas, los saldos bancarios y cualquier asiento
contable que esté fuera de lo normal. Mándame las conclusiones
con tres recomendaciones concretas para mejorar la liquidez.
```

**Encaje:** flujo de caja, DSO, liquidez, conclusiones financieras. Es trabajo de Directora Financiera.

**Esperado:** `agent="custom"` → Yolanda + builtin (billing, banking, accounting, email).

---

## Prompt 3 — CEO (Kepler)

```
Quiero la foto estratégica del estado de la empresa para
prepararme la junta del viernes. Pipeline comercial, ingresos
del trimestre, situación del equipo y cualquier riesgo de
cumplimiento que tengamos abierto. Dame además tres prioridades
estratégicas para el próximo trimestre.
```

**Encaje:** visión transversal, junta, prioridades estratégicas. Es trabajo del Director Ejecutivo.

**Esperado:** `agent="custom"` → Kepler + builtin (crm, billing, hr, compliance).

⚠️ Si Kepler ha sido el que dio timeout antes, ahora con 180s debería caber. Si vuelve a saltar TimeoutError, considera acortar su `system_prompt` desde la UI de tu app.

---

## Prompt 4 — Auditora (Alicja)

```
Tengo dudas razonables sobre los gastos del mes pasado. Revisa
todos los documentos y movimientos bancarios buscando duplicados,
facturas sin asiento contable, gastos por encima del umbral de
aprobación interna, y cualquier irregularidad respecto a la
política de la empresa. Mándame el informe ordenado por
gravedad.
```

**Encaje:** detección de irregularidades, control de política interna, auditoría operativa. Es trabajo de Auditora Interna.

**Esperado:** `agent="custom"` → Alicja + builtin (documents, banking, billing, compliance).

---

## Cómo validar cada ejecución

Después de lanzar un prompt, consulta la BD:

```sql
SELECT id, status, plan, error_message, agent_results
FROM tasks
ORDER BY created_at DESC
LIMIT 1;
```

Lo correcto es ver:

1. **`status = "done"`**
2. **`plan`** con un nodo `agent="custom"` apuntando al `employee_id` del rol que ESPERAS para ese prompt
3. **`agent_results`** con `success: true` para todos los pasos
4. La respuesta consolidada en `activity_feed` (último entry de la tarea)

Si **`status = "failed"`** y `error_message` empieza por "Timeout de 180s..." → el system_prompt del custom es demasiado largo, simplifícalo.

Si el `employee_id` del nodo custom apunta al rol **equivocado** (ej. CTO recibiendo el prompt 2 que es financiero) → el LLM no está pesando bien el bloque `Expertise:`. Avísame y endurezco la guía de PRECEDENCIA.

Si **no hay nodo custom** y todo es builtin → el LLM ignoró el bloque entero, hay que aumentar su prominencia en el prompt del planner.

---

## Para añadir más custom employees

`create_ai_employee_from_description` desde tu UI. Cuanto más específico sea el rol y más claro el `system_prompt` (sin verbosidad innecesaria), mejor encaje hará el planner. Ejemplos de roles que aún no tienes y podrían ser útiles:

- **Directora de Operaciones (COO)** — supervisión de procesos productivos
- **Responsable de Calidad** — revisión de outputs antes de entregar al cliente
- **Asesor Legal** — interpretación contractual y disputas
- **Customer Success Manager** — análisis de satisfacción y churn
