# VeriFactu — envío a la AEAT: spec de la costura

> Estado: **2026-06-19**. Documento de la "costura" del envío VeriFactu y de lo que falta
> para conectarlo. Escrito en modo **máxima cautela** (certificado denegado → vamos a ciegas):
> se separa claramente lo **CONFIRMADO** (anclado a artefactos del repo) de lo **POR CONFIRMAR**
> (necesita certificado + entorno de preproducción de la AEAT). Línea roja: **nunca** fabricar
> CSV/acuse/justificante; el envío real queda *gated* por `confirmed=True` + certificado.

## 1. Estado y alcance

| Pieza | Estado |
|---|---|
| XML `RegistroAlta`/`RegistroAnulacion` válido contra XSD oficial | ✅ hecho (`registro_facturacion`, test `test_verifactu_registro_xml`) |
| Huella encadenada (SHA-256) + QR | ✅ hecho (`verifactu_chain`) |
| Parseo del acuse `RespuestaRegFactuSistemaFacturacion` | ✅ hecho (`verifactu_submit.parse_acuse`, testeado) |
| Interfaz/costura del envío (submitter, factory, gate) | ✅ hecho (`verifactu_submit`, testeado sin cert) |
| Firma XAdES del envío | ⏳ pendiente (cert) |
| POST SOAP con mTLS a preproducción | ⏳ pendiente (cert + endpoint por confirmar) |
| Enganche en la emisión de factura (`create_invoice`) | ⏳ pendiente (NO conectado a propósito) |

**Nada de esto se invoca todavía desde el flujo vivo.** El modo por defecto (`no_remission`)
es un no-op idéntico al comportamiento actual.

## 2. La costura (`backend/app/services/billing/verifactu_submit.py`)

- `VerifactuSubmitter` (Protocol): `submit(db, *, record, confirmed=False) -> VerifactuAck`.
- `NoRemissionSubmitter`: no-op (modo `no_remission`, default). Devuelve `remitted=False`.
- `PreproduccionSubmitter`: genera el XML (`generate_alta_xml`) → valida contra XSD
  (`validate_verifactu_xml`) → **si `confirmed=False` → dry-run, NO hay POST** → con
  `confirmed=True` exige transporte real (hoy `NotImplementedError`).
- `VerifactuTransport` (Protocol): `post(*, xml, environment, confirmed) -> str` (acuse crudo).
  - `_RealVerifactuTransport`: **`NotImplementedError`** (firma + SOAP mTLS pendientes).
- `get_submitter(db, *, tenant_id, transport=None)`: elige impl por `verifactu_mode.get_mode`.
- `parse_acuse(response_xml) -> VerifactuAck`: parser **puro** (sin red/BD), por *local-name*
  (tolera prefijos y el sobre SOAP).

## 3. Cadena del envío real (cuando haya certificado)

```
generate_alta_xml(db, record)        # XML oficial (ya validado contra XSD)
  → validate_verifactu_xml(xml)      # gate de calidad
  → firmar XAdES con el cert del tenant (BYO)        ← PENDIENTE
  → POST SOAP (mTLS) a preproducción                  ← PENDIENTE
  → parse_acuse(respuesta) → VerifactuAck            # ya hecho
  → persistir verifactu_status / CSV en el registro   ← al conectar el hook
```

## 4. Formato del acuse — CONFIRMADO (anclado a `RespuestaSuministro.xsd` del repo)

`RespuestaRegFactuSistemaFacturacion`:
- `CSV` (opcional) — **solo si NO hay rechazo del envío**. Es el justificante de la AEAT;
  nunca se fabrica.
- `TiempoEsperaEnvio`, `Cabecera`, `DatosPresentacion` (opcional).
- `EstadoEnvio`: `Correcto` | `ParcialmenteCorrecto` | `Incorrecto`.
- `RespuestaLinea` (0..1000), por registro:
  - `IDFactura` → `IDEmisorFactura`, `NumSerieFactura`, `FechaExpedicionFactura`.
  - `EstadoRegistro`: `Correcto` | `AceptadoConErrores` | `Incorrecto`.
  - `CodigoErrorRegistro` (entero, opcional), `DescripcionErrorRegistro` (opcional).
  - `RegistroDuplicado` (opcional) → si está, el registro se rechazó por duplicado.

## 5. POR CONFIRMAR (necesita certificado + preproducción) — no asumir como verdad

- **Endpoint de preproducción**: candidato
  `https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP`
  (en `VERIFACTU_ENDPOINTS`, marcado *POR CONFIRMAR*). Validar contra el WSDL oficial vigente.
- **Sobre SOAP**: presumiblemente document/literal, `SOAPAction` vacío — **sin verificar**.
- **Perfil de firma XAdES**: presumiblemente XAdES-EPES *enveloped* — **confirmar** algoritmos
  y qué nodo se firma exactamente contra la especificación oficial.
- **mTLS**: el POST usa el certificado del tenant (modelo BYO) como cliente TLS.
- **Régimen**: decidir **VERI\*FACTU (remitido en tiempo real)** vs **no-VERI\*FACTU**
  (no remite; registro de eventos `EventosSIF.xsd`, conservación, a requerimiento). Es una
  **decisión fiscal** (consultar gestor), no técnica.
- **Reintentos / idempotencia**: la AEAT identifica por huella; definir política de reintentos.

## 6. Punto de enganche (cuando haya cert) — NO conectado hoy

`backend/app/services/billing/commands.py:131` (`create_invoice`), tras
`maybe_append_verifactu_record(...)` y **después del commit**:

```python
record = await maybe_append_verifactu_record(db, invoice=new_invoice)
# ... commit ...
if record is not None:  # solo en modo 'voluntary'
    submitter = await get_submitter(db, tenant_id=new_invoice.tenant_id)
    ack = await submitter.submit(db, record=record, confirmed=...)  # confirmed gated
    # persistir ack.estado_envio / ack.csv en el registro
```

- En `no_remission` (default), `record is None` → no se llama → comportamiento idéntico a hoy.
- **Recomendado**: no enviar inline dentro del commit atómico — delegar a un worker o a una
  transacción propia, para no acoplar la latencia de la AEAT a la emisión.
- Mismo patrón en `create_rectificativa` (`commands.py:244`).

## 7. Cómo probar cuando llegue el certificado

1. Obtener un certificado (FNMT o, si denegado, reintentar / DNIe / presencial). Ver
   `tasks/todo.md`.
2. Confirmar endpoint + WSDL de preproducción y el perfil XAdES (sección 5).
3. Implementar `_RealVerifactuTransport.post` (firma XAdES + POST SOAP mTLS).
4. Probar **contra preproducción** (sin efectos fiscales) con `confirmed=True` y un cert real.
5. Verificar que `parse_acuse` casa con el acuse real; ajustar si la AEAT difiere del XSD.

## 8. Línea roja (máxima cautela)

- El `CSV`/acuse **solo** procede de una respuesta real parseada (`parse_acuse`). Jamás se
  genera un CSV/justificante/PDF417 ficticio.
- Sin `confirmed=True` **no hay POST** (dry-run). Sin transporte real ni certificado,
  `confirmed=True` levanta `NotImplementedError` — no se simula un envío exitoso.
- La costura no cambia el comportamiento del modo por defecto (`no_remission`).
