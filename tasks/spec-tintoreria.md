# Spec — Vertical Tintorería (flujo mostrador con albarán-resguardo)

_Origen: reunión con Pascual 2026-07-22. Estado: BORRADOR pendiente de validar
con Marcos/Pascual. Principio: core intacto — todo se construye DENTRO del
repo como vertical activable por tenant, sin fork._

## El flujo del negocio (como lo pidió el cliente)

1. Cliente llega al mostrador con prendas.
2. Empleado, en una pantalla táctil tipo iPad y **casi sin teclear**:
   a. Busca el cliente por **NIF / teléfono / nombre** en un solo campo — o lo
      **da de alta exprés** (nombre + teléfono) si no existe.
   b. Selecciona los servicios/prendas de un **catálogo con iconos** (grid
      táctil, clic-clic-clic).
   c. Añade **notas y concepto** si hace falta.
   d. **Genera el albarán** → se imprime el **ticket-resguardo** y se lo lleva
      el cliente.
3. La prenda pasa por estados: **recibido → en proceso → listo → entregado**
   (cambio de estado en un clic).
4. El cliente vuelve con el resguardo → el empleado **lo localiza al instante**
   (por número o escaneando el código del ticket) → **"Entregar"** → queda
   registrado como entregado, con fecha/hora y asociado a sus productos.

## Qué existe ya en el core (se reutiliza, no se duplica)

| Pieza | Estado |
|---|---|
| Modelo `DeliveryNote` + líneas + numeración + rutas + página Albaranes | ✅ |
| Ticket 80 mm + impresión (diálogo/silenciosa/térmica) — construido para el TPV | ✅ se reutiliza el patrón |
| Búsqueda de clientes / alta de clientes | ✅ (falta el "un solo campo" + alta exprés) |
| Etiquetas de prenda + resguardo PDF + tarjeta fidelización | ✅ (hoy sobre pedidos; se porta a albarán) |
| Escáner (lector USB / cámara móvil) | ✅ |
| Tools del agente (`create_albaran`, `list_albaranes`) | ✅ |

## Tandas de construcción (cada una verificada y entregable por sí sola)

### T1 — Estados del ciclo tintorería (S)
- `DeliveryNote.status`: añadir `recibido`, `en_proceso`, `listo` al flujo
  (hoy: draft/confirmed/delivered → mapeo compatible; `delivered`=entregado).
- Máquina de estados + transición en un clic desde la lista/detalle.
- Registro de quién y cuándo entrega (`delivered_at`, `delivered_by`).

### T2 — Ticket-resguardo 80 mm del albarán (S/M)
- HTML autocontenido (mismo patrón que el ticket del TPV): negocio, nº albarán
  grande, **código de barras/QR con el número** (para localizarlo al volver),
  líneas, notas, leyenda "Resguardo de depósito".
- Botón imprimir + impresión automática al generar (reutiliza ajustes de
  impresora del TPV).

### T3 — Modal de creación rápida "modo mostrador" (M)
- Grid táctil de productos con **iconos** y categorías (asunción: campo
  icono/emoji por producto — validar si quieren fotos).
- Cliente: un solo buscador (NIF/teléfono/nombre) + **alta exprés** inline.
- Notas/concepto. Botón grande "Generar albarán" → crea + imprime resguardo.
- Botones grandes, cero teclado salvo búsquedas.

### T4 — Localizar y entregar (S/M)
- Buscador de albaranes por número/cliente/teléfono + **escaneo del código del
  resguardo** (lector USB o cámara).
- Vista de entrega: prendas, estado, notas → botón **"Entregar"** → estado
  `entregado` registrado.

### T5 — Acceso de empleados (M)
- Rol/permiso "mostrador": crear albaranes, cambiar estados y entregar SIN
  acceso al resto del ERP (facturas, nóminas, config).
- Landing simplificada para ese rol (directo al modo mostrador).

### T6 — Cobro/factura desde el albarán (M, tras validar con Pascual)
- "Entregar y cobrar": vuelca las líneas del albarán al TPV → factura
  simplificada F2 con su registro VeriFactu (todo eso ya existe).

## Ampliación (2026-07-22, segunda conversación con Marcos)

### Hechas ya
- **Servicios sin stock** ✅: una tintorería vende SERVICIOS (`item_type=service`,
  ya existía en el modelo). El descuento/reversión de stock del albarán ahora
  los ignora — antes "entregar" un albarán de servicios reventaba con "stock
  insuficiente" (bug cazado y testeado).
- **iPad/tablet** ✅ por diseño: el modo mostrador es una página web táctil
  (botones grandes) — desde el iPad se abre el navegador contra la app
  (LAN HTTPS con el CA, o el servidor del kit `deploy/` con TLS real, que es
  lo recomendado para Pascual).

### Tandas nuevas
- **T7 — Albaranes ↔ Facturas muchos-a-muchos (M)**: tabla de enlace
  `invoice_delivery_notes`; seleccionar N albaranes de un cliente → "Facturar"
  (una factura agrupa varios albaranes: caso hotel/restaurante a fin de mes) y
  una factura puede colgar de varios albaranes y viceversa. Vista de qué
  albaranes están facturados y cuáles no.
- **T8 — Albaranes modificables (S/M)**: editar líneas/notas/cliente de un
  albarán no entregado (con guardas: entregado o facturado → solo rectificar).
- **T9 — Import/export masivo (S/M)**: catálogo de servicios con iconos por
  CSV (el import de productos ya existe — añadir columna icon), clientes ya
  importables; dataset "albaranes" en el export Excel del asistente y en CSV.

### Pregunta abierta para Pascual
- **"Distintos tipos de clientes en el albarán"** — hipótesis: particular vs
  EMPRESA (hoteles/restaurantes con albaranes acumulados y factura mensual
  agrupada, lo que conecta con T7; quizá tarifas distintas por tipo). El campo
  `client_type` ya existe en el cliente. VALIDAR qué quiso decir exactamente.

## Asunciones a validar ANTES de construir

1. Estados exactos: ¿`recibido / en proceso / listo / entregado` basta? ¿Hace
   falta `anulado`?
2. ¿El cobro es a la RECOGIDA (T6) o a veces al depositar? ¿Ambos?
3. Iconos del catálogo: ¿emoji/icono por categoría basta o quieren fotos?
4. ¿Aviso al cliente cuando está "listo" (SMS/WhatsApp)? — fuera de esta spec
   si no lo pidieron; anotarlo como fase 2 si interesa.
5. Hardware del mostrador: ¿tablet con navegador contra el servidor (kit
   deploy) o el PC con la app? (Afecta al tamaño de los botones, no al código.)

## Fuera de alcance de esta spec

- Fork/duplicado del proyecto (descartado: doble mantenimiento del core
  VeriFactu auditado).
- Multi-local: lo cubre el kit de despliegue en servidor (`deploy/`).
- Remisión VeriFactu (P4): sigue su propio plan.
