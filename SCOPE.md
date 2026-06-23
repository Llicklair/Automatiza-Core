# AutomatizaCore — Scope de Producto v1

> Documento de definición de producto. Define qué es, para quién, qué hace, y qué necesita para ser viable comercialmente.
>
> _Última revisión: 2026-04-25 (v4)_

---

## 0. Visión y diferenciación

### Qué es

AutomatizaCore es un ERP de escritorio con inteligencia artificial integrada. En lugar de navegar menús y rellenar formularios, el usuario escribe instrucciones en lenguaje natural — "crea una factura para García S.L. por 1.200€" — y el sistema lo ejecuta.

### Para quién

**Asesorías, gestorías y pequeñas empresas españolas (1-50 empleados)** que:
- Hoy usan Excel, papel o un ERP genérico que no entienden
- No tienen departamento de IT
- Necesitan facturación, nóminas, control de clientes y documentos en un solo sitio
- Valoran que su base de datos NO se aloje en servidores de terceros (queda en su ordenador; las funciones de IA envían solo los datos necesarios al proveedor LLM que el cliente elija, nunca a un servidor de AutomatizaCore)

### Por qué existe

Los ERP existentes (Holded, Sage, A3, Contasol) tienen dos problemas para este segmento:
1. **Curva de aprendizaje alta** — el usuario necesita saber dónde está cada función
2. **Datos en la nube** — muchas PYMEs y asesorías son reticentes a subir datos fiscales y de empleados a servidores de terceros

AutomatizaCore resuelve ambos: la IA elimina la curva de aprendizaje, y la arquitectura local-first mantiene toda la base de datos en el ordenador del cliente, sin servidor central que la almacene. La inferencia de IA envía los datos necesarios directamente al proveedor LLM que el cliente configura (Anthropic/OpenAI/…), bajo el DPA de ese proveedor y nunca a través de servidores de AutomatizaCore.

### Riesgo competitivo

Holded, Sage y otros están añadiendo asistentes IA. La ventaja no es "tener IA" sino:
- **IA como interfaz principal**, no como chatbot añadido al margen
- **Agentes que ejecutan acciones**, no solo responden preguntas
- **Local-first**: sin servidor central con datos del cliente (la BD vive en su equipo); la IA usa el proveedor LLM del cliente bajo DPA
- **Precio de entrada bajo** vs suscripciones SaaS crecientes

Esta ventaja tiene fecha de caducidad. La velocidad de lanzamiento es el factor decisivo.

---

## 1. Capacidades v1

### Facturación y ventas
Crear facturas, albaranes, presupuestos y pedidos desde lenguaje natural. Cálculo automático de IVA, numeración correlativa, vinculación con clientes en BD. Facturas recurrentes con periodicidad configurable. Visible en UI sin recarga.

### Recursos Humanos
Alta de empleados, cálculo de nóminas, registro de jornada, liquidaciones. Procesa instrucciones como "calcula la nómina de marzo de todos los empleados".

### Control horario y gestión de jornadas
Panel dedicado para gestionar el tiempo de trabajo de cada empleado:
- **Horario contractual**: horas semanales del contrato, franja horaria asignada (ej. 9:00-17:00), tipo de jornada (completa, parcial, turnos)
- **Registro diario**: fichaje de entrada/salida (manual o por el empleado), cálculo automático de horas trabajadas vs horas contractuales
- **Horas extra**: detección automática cuando las horas trabajadas superan las contractuales, diferenciación entre compensadas y pagadas
- **Ausencias e incidencias**: registro de faltas con motivo (baja médica, vacaciones, permiso, ausencia injustificada), impacto automático en nómina
- **Vista calendario**: visualización mensual por empleado o por equipo, con colores por tipo de jornada/incidencia
- **Alertas**: aviso cuando un empleado acumula horas extra no compensadas, o cuando faltan fichajes

> Obligatorio: el registro de jornada es requisito legal en España desde 2019 (RD-ley 8/2019). El sistema debe poder exportar los registros en formato válido para inspección laboral.

### CRM y clientes
Ciclo de ventas completo: clientes, oportunidades, actividades, pipeline. Gestión de reservas y reuniones.

### Banca y contabilidad
Carga de extractos bancarios (CSV/OFX), consulta de saldos, listado de movimientos, conciliación. Informes financieros: P&L, balance, cashflow.

### Documentos e inteligencia documental (RAG)
Subida de contratos, facturas PDF o cualquier documento. Indexación con embeddings vectoriales (pgvector). Preguntas sobre contenido: "¿cuándo vence el contrato con Telefónica?" extrae la respuesta del PDF.

### Correo electrónico
Envío y lectura de correos (Gmail, Outlook, SMTP) si el usuario configura credenciales. Instrucciones como "envía un resumen de facturas pendientes a contabilidad@empresa.com". Sin credenciales: modo demo.

### Automatizaciones (workflows)
Tareas recurrentes en lenguaje natural: "cada lunes, envíame un resumen de facturas pendientes". Ejecución automática por cron, condiciones lógicas (AND/OR/NOT/umbrales), consultas a BD en tiempo real antes de ejecutar.

### Compliance y asesoría fiscal
Consulta automática del BOE, avisos de vencimientos fiscales (IVA, IRPF), respuestas de asesoría basadas en documentos indexados.

---

## 2. Flujos críticos — deben funcionar impecablemente

> Hacer 5 flujos perfectos vale más que 15 flujos rotos.
> Cualquier nueva funcionalidad solo entra si estos 5 siguen funcionando.

### Flujo 1 — Factura desde lenguaje natural
```
"Crea una factura para Cliente X por 1500€ de consultoría"
→ Clasifica → billing agent → valida cliente → crea factura + líneas → confirma → visible en UI
```
**Criterios**: Factura en BD con número correlativo y estado correcto. Aparece en UI sin recarga. Respuesta en < 5 segundos.

### Flujo 2 — Consulta financiera
```
"¿Cuánto hemos facturado este mes y qué facturas están pendientes?"
→ billing agent → query → agrega → responde en chat
```
**Criterios**: Números coinciden con un SELECT manual. Respuesta en < 3 segundos.

### Flujo 3 — Alta de empleado
```
"Da de alta a María García, contrato indefinido, 2200€/mes, inicio 1 junio"
→ HR agent → crea Employee + contrato → confirma → visible en /rrhh
```
**Criterios**: Empleado en BD con todos los campos requeridos. Sin errores de validación. Respuesta en < 5 segundos.

### Flujo 4 — Workflow recurrente end-to-end
```
"Cada lunes envíame un resumen de facturas pendientes"
→ Workflow guardado → scheduler programa job → lunes: billing genera resumen → email envía → log success
```
**Criterios**: Email recibido, ejecución registrada con status: success, sin intervención humana.

### Flujo 5 — Consulta documental (RAG)
```
Usuario sube contrato PDF → "¿Cuándo vence el contrato con Proveedor X?"
→ Documents indexa → RAG busca chunks → responde con fecha
```
**Criterios**: Fecha correcta extraída del PDF. Verificable contra el documento original.

### Flujo 6 — Control horario de empleado
```
Empleado ficha entrada → trabaja → ficha salida → sistema calcula horas
→ si excede contrato → marca hora extra → refleja en nómina mensual
Manager: "¿Cuántas horas extra ha hecho Juan este mes?" → HR agent responde
```
**Criterios**: Registro de jornada almacenado con hora entrada/salida. Cálculo correcto de horas extra vs contractuales. Exportable para inspección laboral.

### Flujo 7 — Primera experiencia (onboarding)
```
Usuario instala → abre app → asistente guiado:
1. Nombre empresa + NIF + dirección fiscal
2. Opción importar datos o empezar de cero
3. Configurar email (saltable)
4. 3 ejemplos en lenguaje natural
5. Crear primer cliente + primera factura como tutorial
→ Usuario llega a pantalla principal habiendo hecho algo real
```
**Criterios**: Usuario completa el flujo en < 5 minutos. Sin errores ni pantallas en blanco. Al finalizar existe al menos 1 cliente y 1 factura en BD. El 100% de los pasos son saltables excepto NIF + nombre empresa.

---

## 3. Limitaciones conocidas de v1

| Limitación | Motivo |
|-----------|--------|
| Sin conexión bancaria directa | Open Banking/PSD2 requiere integración con Belvo o Salt Edge |
| Sin firma electrónica | No hay integración con DocuSign/Autofirma |
| Sin presentación automática a AEAT | Requiere certificado digital y API de sede electrónica |
| Una empresa por instalación | Diseño deliberado: una empresa = una BD local |
| La BD operativa no se sincroniza a la nube | Decisión de privacidad, no limitación técnica (las funciones de IA sí envían datos al proveedor LLM elegido) |
| Requiere internet para IA | El LLM es remoto; sin conexión, la IA no funciona |

---

## 4. Roadmap

### Criterio de lanzamiento — v1.0 no sale sin esto

> Un checkbox sin marcar en esta lista es un bloqueante. No hay excepciones.

- [ ] Los 7 flujos críticos pasan sin intervención manual
- [ ] Onboarding completo (flujo 7) funciona en < 5 minutos
- [ ] VeriFactu implementado y validado con AEAT (ver sección 5.6) — **bloqueante legal**
- [ ] Auto-update operativo (el usuario puede recibir parches sin reinstalar)
- [ ] Backup exportable desde Settings
- [ ] Mensajes de error comprensibles — cero errores técnicos visibles al usuario
- [ ] Precio y canal de distribución decididos (ver sección 6)

### v1.0 — Producto mínimo viable (actual)
- [x] 14 agentes especializados funcionales
- [x] Orquestador con clasificación de intención
- [x] 7 flujos críticos end-to-end
- [ ] Panel de control horario (fichajes, horas extra, ausencias, calendario)
- [x] Aplicación Electron con PostgreSQL embebido
- [ ] Onboarding de primera experiencia (ver sección 5)
- [ ] Modo offline graceful (ver sección 5)
- [ ] TicketBAI / VeriFactu — facturación legal (ver sección 5) ⚠️ bloqueante legal
- [ ] Backup automático local
- [ ] Auto-update del Electron app

### v1.5 — Completar la experiencia
- [ ] Página frontend para email (/email)
- [ ] Página frontend para Excel (/excel)
- [ ] Ruta API para Excel agent
- [ ] Ruta API para Marketing agent
- [ ] Importación de datos desde Excel/CSV (migración desde ERP anterior)
- [ ] Reclutamiento: posiciones, CVs, seguimiento de candidatos

### v2.0 — Diferenciación
- [ ] Integración bancaria real (Belvo/Salt Edge)
- [ ] Firma electrónica (Autofirma/DocuSign)
- [ ] Multi-empresa por instalación
- [ ] Dashboards visuales con gráficos
- [ ] App móvil (consulta, no gestión completa)

### Futuro
- Presentación automática a AEAT
- Marketplace de plugins/agentes de terceros
- Modo cloud opcional (sincronización voluntaria)

---

## 5. Requisitos no funcionales — críticos para producto real

### 5.1 Primera experiencia (onboarding)

Hoy: el usuario instala, abre, y ve una pantalla vacía. Tiene que intuir qué hacer.

**Necesita**: Un asistente guiado que en 5 minutos:
1. Pida nombre de empresa, NIF, dirección fiscal
2. Ofrezca importar datos existentes (Excel/CSV) o empezar de cero
3. Configure email (opcional, puede saltar)
4. Muestre 3 ejemplos de lo que puede hacer con lenguaje natural
5. Cree el primer cliente/factura como tutorial

Sin esto, el 80% de usuarios abandona en los primeros 10 minutos.

### 5.2 Degradación cuando el LLM falla

Hoy: si el LLM no responde o devuelve algo imparseable, el sistema muestra errores técnicos ("No se pudo parsear el plan del LLM").

**Necesita**:
- Mensajes de error comprensibles: "No he podido procesar tu solicitud. ¿Puedes reformularla?"
- Retry automático (1-2 intentos) antes de mostrar error
- Las funciones de UI (tablas, formularios) deben funcionar SIN la IA — el ERP básico no debería depender del LLM
- Indicador visual claro de "IA no disponible" vs "error en tu solicitud"

### 5.3 Dependencia de internet y costes LLM

- **Sin internet**: La IA no funciona, pero el ERP debería seguir operativo para consultas, listados, formularios manuales
- **Costes**: Cada interacción con IA tiene coste de tokens. Necesita:
  - Estimación de coste mensual por volumen de uso
  - Mecanismo para que el usuario sepa su consumo
  - Posibilidad de modelo local (Ollama/llama.cpp) como alternativa sin coste

### 5.4 Backup y recuperación

Local-first significa: si el PC muere, la empresa pierde todo. Esto es un showstopper.

**Necesita (mínimo v1)**:
- Exportación programada de BD a archivo (pg_dump automático)
- Botón "Exportar backup" en settings
- Guía de restauración clara

**Deseable (v1.5)**:
- Backup automático diario a carpeta configurable (USB, NAS, carpeta de nube tipo Dropbox)
- Verificación de integridad del backup

### 5.5 Mecanismo de actualización

**Necesita**:
- Auto-update via Electron autoUpdater (Squirrel/electron-updater)
- Notificación no intrusiva de nueva versión
- Migraciones de BD automáticas al actualizar
- Rollback si la migración falla

### 5.6 Facturación legal en España

**TicketBAI** (País Vasco) y **VeriFactu** (resto de España) son obligatorios para software de facturación en 2026.

Requisitos mínimos:
- Encadenamiento de facturas (hash de la anterior)
- Firma electrónica de cada factura
- Envío a la AEAT/hacienda foral en tiempo real o plazo
- QR en cada factura impresa
- Registro de eventos (alta, anulación, modificación)

**Sin esto, el software no puede venderse legalmente como herramienta de facturación en España.**

### 5.7 Seguridad y RGPD/LOPD

El sistema maneja datos sensibles: nóminas, datos personales de empleados, información fiscal.

**Necesita**:
- Control de acceso: ¿quién puede ver nóminas? ¿Y datos de clientes?
- Log de auditoría de accesos (quién accedió a qué dato y cuándo)
- Cifrado de la BD local (o al menos de campos sensibles)
- Derecho al olvido: capacidad de borrar todos los datos de una persona
- Política de privacidad clara para el usuario final

### 5.8 Rendimiento

| Operación | Objetivo |
|-----------|----------|
| Arranque de la aplicación | < 15 segundos |
| Respuesta de IA (flujos simples) | < 5 segundos |
| Consultas a BD (listados, búsquedas) | < 1 segundo |
| Indexación de documento PDF | < 10 segundos por página |
| Carga de página frontend | < 2 segundos |

---

## 6. Modelo de negocio

> Sin definición de modelo de negocio, las decisiones técnicas se toman en el vacío.

### Opciones a evaluar

| Modelo | Pros | Contras |
|--------|------|---------|
| **Licencia única + mantenimiento anual** | Ingreso upfront, familiar para PYMEs | Ingresos no recurrentes, difícil financiar desarrollo continuo |
| **Suscripción mensual** | Ingresos predecibles, alineado con coste LLM | Resistencia de PYMEs a "otro SaaS mensual" |
| **Freemium** | Baja barrera de entrada, viralidad | Difícil convertir en segmento PYME |
| **Pago por uso de IA** | Justo: pagas lo que usas | Impredecible para el cliente, genera ansiedad de uso |

### Recomendación preliminar

**Suscripción mensual con tier gratuito limitado**:
- **Gratis**: hasta 10 facturas/mes, 1 empleado, sin workflows automáticos, sin RAG — suficiente para probar, insuficiente para operar
- **Pro (€X/mes)**: IA ilimitada, facturas ilimitadas, workflows, RAG, soporte email
- **Asesoría (€X/mes)**: Multi-empresa (v2), soporte prioritario, compliance avanzado

El tier gratuito es una demo con límites reales, no un ERP completo sin IA. La IA y los límites operativos son el upsell. El coste de LLM se absorbe en Pro.

### Canal de distribución — decisión urgente pre-lanzamiento

El canal determina el precio, el onboarding y el soporte. Para PYMEs españolas el canal más eficiente es **B2B indirecto via asesorías**: la asesoría adopta el producto y lo recomienda a sus clientes (que ya confían en ella). Alternativas:

| Canal | Pros | Contras |
|-------|------|---------|
| **Asesorías (B2B indirecto)** | Acceso directo al segmento, confianza establecida, volumen por cuenta | Ciclo de venta más largo, necesitas convencer a la asesoría primero |
| **Web directa (B2C)** | Control total, sin intermediario | Coste de adquisición alto, requiere marketing activo |
| **Marketplaces** | Descubrimiento gratuito | Competencia directa, márgenes reducidos |

**Decisión pendiente** (bloqueante para lanzamiento): ¿asesorías primero o web directa?

### Métricas de éxito de v1.0

Sin un número, no sabes cuándo has terminado. Propuesta:

| Métrica | Objetivo a 90 días del lanzamiento |
|---------|-------------------------------------|
| Clientes pagando (Pro) | 10 |
| Churn mensual | < 10% |
| Flujos críticos completados sin error | > 95% |
| NPS | > 30 |
| Tiempo medio de onboarding | < 5 minutos |

### Pendiente de decidir — bloqueante pre-lanzamiento
- [ ] **Canal de distribución**: asesorías primero o web directa
- [ ] **Precio exacto** por tier (Pro y Asesoría)
- [ ] Si tier gratuito incluye N interacciones IA/mes adicionales
- [ ] Modelo de soporte: solo email, chat, telefónico

---

## Apéndice: Decisiones tomadas

| Decisión | Razón | Fecha |
|----------|-------|-------|
| Local-first (no SaaS) | Privacidad como diferenciador + confianza segmento PYME | Inicio proyecto |
| Electron + PostgreSQL embebido | Instalación sin dependencias, familiar para usuario Windows | Inicio proyecto |
| Claude como LLM principal | Mejor relación calidad/coste para español + tool use | Inicio proyecto |
| Un tenant por instalación | Simplifica v1, multi-empresa planificado para v2 | Inicio proyecto |
| Sin servidor central con datos del cliente (BD local) | Elimina el riesgo de brecha masiva y las preocupaciones RGPD de hosting; la IA usa el proveedor LLM del cliente bajo DPA | Inicio proyecto |
