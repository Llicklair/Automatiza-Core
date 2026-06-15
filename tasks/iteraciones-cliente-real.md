# Iteraciones de cliente real — gestión y seguimiento

> Documento **vivo** para conducir las iteraciones de validación end-to-end del ERP
> simulando un **cliente real** que usa cada módulo, detectar fallos y **blindar**
> cada flujo validado con un test que lo replica.
>
> Complementa —no sustituye— a:
> - [`testing-protocol.md`](testing-protocol.md) — manual evergreen de cómo probar (TAREAS vs AUTOMATIZACIONES, sync al Electron).
> - [`test_funcional_completo.py`](test_funcional_completo.py) — script que ya simula un usuario real vía API contra todos los módulos.
> - [`restructuracion-modulos.md`](restructuracion-modulos.md) — backlog de módulos a medias / a reconceptualizar (gestoría documental, marketing, modelos AEAT…).

---

## 1. Por qué este documento

La suite tiene **~2.100 tests**, pero la mayoría son **unitarios** (validan secciones de
código aisladas): solo **~57 ficheros** tocan la API vía `AsyncClient`/`auth_client` y
hay **solo 2 specs Playwright** (`frontend/e2e/`). Tras la última tanda de cambios
(refactors de `pdf`/dispatcher, docs, fixes), **es esperable que varios flujos reales
fallen** aunque los unitarios pasen: *un test unitario verde no garantiza que el usuario
pueda completar el flujo de punta a punta.*

**Meta:** convertir cada flujo de usuario real en algo **probado y blindado**, módulo a
módulo, *poco a poco*.

---

## 2. El ciclo de iteración

Para **cada flujo** de la tabla de seguimiento (§4):

1. **Elegir** un flujo de usuario real (una columna de la tabla). Empezar por los módulos
   en Producción y los críticos (facturación, RRHH, banca, AEAT).
2. **Simular el cliente real** de punta a punta:
   - Backend/API → ampliar/usar [`test_funcional_completo.py`](test_funcional_completo.py)
     o un test `AsyncClient` que recorra el flujo como lo haría el usuario.
   - UI → **Playwright** (`frontend/e2e/*.spec.ts`) cuando el flujo es de interfaz
     (login → navegar → rellenar → enviar → ver resultado).
3. **Detectar el fallo** (500, 422, dato incoherente, paso que no completa, lógica en la
   ruta en vez del servicio, etc.). Anotarlo.
4. **Iterar / arreglar** el código (root cause, no parche). Si toca un módulo a medias,
   ver y actualizar [`restructuracion-modulos.md`](restructuracion-modulos.md).
5. **Validar** que el flujo completa de verdad (BD coherente, respuesta esperada).
6. **Blindar**: añadir **un test que replica el flujo** (ver §3). Debe fallar antes del
   arreglo y pasar después (red → green).
7. **Marcar** el flujo en la tabla (§4): estado + fichero del test que lo cubre.

> Regla de oro: **una iteración no está "hecha" hasta que hay un test que la replica.**
> Si no hay test, el flujo volverá a romperse en el próximo refactor sin avisar.

---

## 3. Dónde vive el test que blinda cada flujo

| Tipo de flujo | Dónde | Cómo |
|---|---|---|
| Recorrido de API multi-paso (crear cliente → factura → PDF) | `backend/tests/test_e2e_<modulo>.py` | `AsyncClient` + `auth_client`; un test por flujo, asserts sobre estado en BD y respuesta |
| Flujo de UI (login → pantalla → acción → resultado) | `frontend/e2e/<modulo>.spec.ts` | Playwright; reusar patrón de `happy-path.spec.ts` |
| Recorrido transversal "todos los módulos" | [`test_funcional_completo.py`](test_funcional_completo.py) | añadir el paso del módulo nuevo al script existente |
| Agente / TAREA o AUTOMATIZACIÓN | `backend/tests/test_*_business.py` | validar **ambos** mecanismos (ver `testing-protocol.md`) |

Convención de nombres: `test_e2e_<modulo>.py` (backend) y `<modulo>.spec.ts` (Playwright)
para distinguir los flujos de usuario real de los unitarios.

---

## 4. Tabla de seguimiento

Estado: ⬜ pendiente · 🟡 fallo detectado / en arreglo · ✅ validado y con test que lo blinda.

| Módulo | Flujo de usuario real (mínimo a cubrir) | Estado | Test que lo blinda | Notas |
|---|---|---|---|---|
| **Facturación** | Crear cliente → crear factura → PDF | ⬜ | — | crítico |
| **Veri\*factu** | Factura → QR/huella → `GET /verify/{huella}` devuelve datos | ✅ | `backend/tests/test_e2e_verifactu.py` | flujo API verificado (0 errores); E2E Playwright sigue en `skip` |
| **Contabilidad** | Asiento / libro diario → P&G → balance | ⬜ | — | |
| **Banca** | Importar movimientos → conciliar → resumen | ⬜ | — | |
| **Tesorería** | Cashflow → pago/cobro → remesa SEPA | ⬜ | — | beta |
| **RRHH — nóminas** | Alta empleado → nómina (IRPF+SS) → aprobación → PDF | ⬜ | — | crítico |
| **RRHH — gestoría documental** | Conversación con LLM → contrato/certificado generado | ⬜ | — | **a reconceptualizar → ver restructuracion-modulos.md** |
| **CRM** | Cliente → oportunidad → actividad → portal | ⬜ | — | |
| **Inventario** | Producto → stock/lotes → almacén → reorder | ⬜ | — | |
| **Ventas/Compras** | Pedido → albarán (reversa stock) → factura | ⬜ | — | |
| **POS/TPV** | Abrir sesión → venta → cierre | ⬜ | — | |
| **Compliance / AEAT** | Generar modelo 303/130 → **plantilla oficial** → presentación asistida | ⬜ | — | **plantilla debe ser la oficial → ver restructuracion-modulos.md** |
| **Marketing** | Conectar red (OAuth) → crear campaña/post → publicar/programar | 🟡 | `test_e2e_marketing_publish.py`, `test_email_campaign_worker.py` | bugs #2 (publish 200 al fallar) y #3 (email-mkt 0 fallos) **arreglados**; quedan #1 (front), OAuth → `restructuracion-modulos.md` |
| **Email marketing** | Lista → campaña → envío | ⬜ | — | |
| **Documentos / RAG** | Subir documento → clasificar → preguntar (cita a página) | ⬜ | — | |
| **Empleados IA** | Crear empleado IA desde NL → asignar skills → ejecutar | ⬜ | — | |
| **Workflows / Automatizaciones** | NL → workflow persistente → scheduler dispara → tarea | ⬜ | — | validar el ciclo completo |
| **Onboarding** | Wizard → simulación 303 → REGAP | ⬜ | — | |
| **Backup / Restore** | Backup (pg_dump) → restore | ⬜ | — | (503 si no es Postgres — ya cubierto) |

> Añade/parte filas según haga falta. Cuando un flujo pase a ✅, enlaza el test.

### Por dónde empezar (prioridad)

De la investigación de cobertura (ver `restructuracion-modulos.md` §4), el orden sugerido:

1. **Veri\*factu / `/verify`** — obligación legal, hoy en `test.skip`. **Primero.**
2. **Modelo AEAT 303** — 18 endpoints de modelos sin ningún test; riesgo fiscal.
3. **Marketing "Publicar ahora"** — bug crítico que dice "publicado" sin publicar.
4. **Tesorería + SEPA**, **cobros**, **importación masiva**, **multi-almacén** — 0 cobertura.

> El único E2E de usuario real hoy es `test_funcional_completo.py` (20 fases) y **no**
> cubre marketing, Veri\*factu ni AEAT — justo los más críticos.

---

## 5. Estado de la suite (línea base)

- Backend: **~215 ficheros de test** (~2.100 funciones). Solo **~57** ejercen la API como usuario.
- Frontend E2E: **2 specs** Playwright (`happy-path`, `smoke`).
- **Hueco principal:** la mayoría son unit; faltan flujos de usuario real por módulo (tabla §4).

Actualiza esta línea base conforme se añadan tests de flujo real, para ver el progreso.

---

## 6. Cómo registrar una iteración (plantilla)

```
### [FECHA] <Módulo> — <Flujo>
- Cómo se simuló: <API / Playwright / test_funcional_completo.py>
- Fallo detectado: <descripción + file:line>
- Causa raíz: <...>
- Arreglo: <commit / PR>
- Test que lo blinda: <ruta del test>  (red→green ✔)
- Estado tabla §4: ✅
```

> Pega cada iteración cerrada bajo esta sección para tener trazabilidad.

---

## Registro de iteraciones

### 2026-06-15 · Email-marketing · contar fallos de envío (red→green)
- **Cómo se simuló**: test de servicio — campaña con 2 destinatarios y un tenant **sin credenciales de email** → `send_campaign`.
- **Fallo detectado** (🔴): `send_email` no lanza (devuelve `"[SIN CREDENCIALES] …"`), y `send_campaign` solo marcaba `failed` ante excepción → log "2 ok, 0 fallidos" **aunque no se envió nada**. `email_marketing/sender.py`.
- **Arreglo**: helper `send_failed()` en `email/sender.py` (None/string-de-éxito = enviado; `"Error…"`/`"[SIN CREDENCIALES]"` = fallo); `send_campaign` inspecciona el resultado.
- **Test que lo blinda**: `tests/test_email_campaign_worker.py::test_send_campaign_sin_credenciales_cuenta_fallos` (red→green ✔). Suite campañas: **5 passed**, sin regresión.
- **Estado tabla §4**: 🟡 (marketing: quedan #1 front y OAuth).

### 2026-06-15 · Marketing · "Publicar ahora" propaga el fallo (red→green)
- **Cómo se simuló**: backend E2E (`AsyncClient`) — post con cuenta sin token → `POST /marketing/posts/{id}/publish`.
- **Fallo detectado** (🔴 reproducido): la API devolvía **HTTP 200** aunque la publicación fallaba (`publish_post_now` descartaba el `PublishResult`; el post quedaba `status='failed'` pero el front lo daba por publicado). `app/api/v1/routes/marketing.py:724`.
- **Arreglo**: la ruta ahora inspecciona el `PublishResult` y responde **502** con `error_message` cuando `!ok`.
- **Test que lo blinda**: `backend/tests/test_e2e_marketing_publish.py` (red→green ✔). Suite marketing/publisher: **62 passed**, sin regresión.
- **Estado tabla §4**: 🟡 (quedan bug #1 front "Publicar ahora no llama a publish", #3 email-mkt cuenta 0 fallos, OAuth `unknown` — ver `restructuracion-modulos.md`).

### 2026-06-15 · Veri\*factu · emisión por API → `/verify`
- **Cómo se simuló**: backend E2E (`AsyncClient`) — activar modo `voluntary` → emitir factura por API (`POST /clients/{id}/invoices` + `PATCH status pending`) → la cadena se engancha sola → `GET /verify/{huella}` público.
- **Resultado**: **0 errores**. La emisión por API dispara `maybe_append_verifactu_record`; la huella verifica con `integrity_ok=True`; la cadena enlaza (`huella_anterior`); `no_remission` no crea cadena.
- **Test que lo blinda**: `backend/tests/test_e2e_verifactu.py` (3 tests). Suite Veri\*factu completa: **37 passed**.
- **Estado tabla §4**: ✅
- **Pendiente**: activar el E2E de UI (Playwright `happy-path.spec.ts`, hoy en `skip`).

<!-- Las iteraciones cerradas se van añadiendo aquí con la plantilla de §6 -->
