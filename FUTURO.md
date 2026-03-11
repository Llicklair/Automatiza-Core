# AutomatizaPyme — Plan de implementación futura

> Este documento recoge las funcionalidades planificadas que **no están implementadas aún**.
> Están documentadas aquí para no perder el diseño y poder retomarlo cuando el momento sea el adecuado.
> El orden refleja la prioridad recomendada, no un calendario.

---

## 1. Sistema de licencias (PRIORIDAD ALTA)

**Contexto**: La app corre en local en la máquina de cada cliente. Para controlar el acceso mensual se necesita un servidor de licencias en un VPS. Pendiente de tener el servidor.

### Cómo funciona

```
levantar.bat
  → app arranca
  → llama a https://licencias.automatizapyme.com/validate con LICENSE_KEY
  → si válida: app funciona con normalidad
  → si inválida/expirada: API devuelve 402, frontend muestra pantalla de activación
  → si VPS no responde: gracia de 48h con cache local (no bloquear por caída puntual del servidor)
```

### Parte A — Cliente (dentro de la app)

**Archivo a crear**: `backend/app/core/license.py`

```python
# LicenseManager — responsabilidades:
# - Al arrancar: leer LICENSE_KEY del .env, llamar al VPS, cachear resultado
# - Cada 24h en background: revalidar con el VPS
# - Si el VPS no responde: usar cache local, permitir hasta 48h de gracia
# - Exponer: is_valid() -> bool, expires_at() -> datetime, tenant_name() -> str
```

**Cambios en `backend/app/main.py`**:
- En el lifespan de arranque: `await license_manager.check_on_startup()`
- Nuevo middleware: si `not license_manager.is_valid()` → devolver `HTTP 402` con `{"error": "license_expired"}`
- Excluir de la comprobación: `/health`, `/docs`, `/openapi.json`

**Cambios en `.env`**:
```env
LICENSE_KEY=PYME-XXXX-XXXX-XXXX
LICENSE_SERVER_URL=https://licencias.automatizapyme.com
```

**Frontend** (`frontend/src/app/layout.tsx` o middleware Next.js):
- Interceptar respuestas `402` con `reason: "license_expired"`
- Redirigir a `/licencia-expirada` — pantalla simple con instrucciones para renovar
- La pantalla NO muestra la app, solo el aviso y el enlace de pago

### Parte B — Servidor de licencias (VPS, servicio independiente)

Servicio FastAPI minimalista. No usa Docker Compose del proyecto principal, se despliega solo en el VPS.

**Stack**: FastAPI + SQLite (sin PostgreSQL, no hace falta para esto) + Uvicorn

**Endpoints**:

```
POST   /validate              → la app llama aquí al arrancar
         body: { license_key, machine_id? }
         response: { valid: bool, expires_at: str, tenant_name: str }

POST   /admin/keys            → crear nueva licencia (solo admin)
         header: Authorization: Bearer ADMIN_TOKEN
         body: { tenant_name, expires_at, email_contacto }
         response: { license_key: "PYME-XXXX-XXXX-XXXX" }

DELETE /admin/keys/{key}      → revocar licencia (impago, fraude)
         header: Authorization: Bearer ADMIN_TOKEN

GET    /admin/keys            → listar todas las licencias y su estado
         header: Authorization: Bearer ADMIN_TOKEN

GET    /health                → para monitorización del VPS
```

**Modelo de datos (SQLite)**:
```sql
CREATE TABLE licenses (
    id          TEXT PRIMARY KEY,   -- PYME-XXXX-XXXX-XXXX
    tenant_name TEXT NOT NULL,
    email       TEXT,
    created_at  DATETIME,
    expires_at  DATETIME,
    revoked     BOOLEAN DEFAULT 0,
    last_seen   DATETIME            -- última validación recibida
);
```

**Generación de claves**:
```python
import secrets, string
def generate_key():
    chars = string.ascii_uppercase + string.digits
    segments = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return "PYME-" + "-".join(segments)
# → PYME-X4K2-9MNQ-VRTZ-8JBP
```

**Seguridad del servidor**:
- HTTPS obligatorio (Let's Encrypt / Certbot, gratuito)
- `ADMIN_TOKEN` en `.env` del VPS, mínimo 32 caracteres aleatorios
- Rate limiting: máximo 10 validaciones/hora por IP (evita abuso)
- Las validaciones se loguean con timestamp e IP para detectar compartición de claves

### Parte C — Protección del código ("wrapeo")

Una vez el sistema de licencias esté operativo, ofuscar el mecanismo para dificultar bypasses:

- **Backend**: compilar con [Nuitka](https://nuitka.net/) (`nuitka --onefile backend/app/main.py`)
- **Frontend**: el build de producción de Next.js ya minifica; añadir `javascript-obfuscator` para la lógica crítica
- **Objetivo concreto**: proteger la lógica de `license.py`, no el resto del código ERP

> La ofuscación protege contra el usuario casual que quiere saltarse el pago.
> No es un muro infranqueable, es una barrera de coste/esfuerzo suficiente para el perfil de cliente objetivo (PYME, no hacker).

### Parte D — Huella de hardware (opcional, fase posterior)

Para evitar que una clave se comparta entre múltiples instalaciones:

```python
import uuid, hashlib, platform

def get_machine_id() -> str:
    # Combina identificadores estables del hardware
    raw = f"{uuid.getnode()}-{platform.node()}-{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

- La primera activación registra el `machine_id` en el servidor
- Las siguientes validaciones comprueban que el `machine_id` coincide
- Si no coincide: el servidor puede avisar (sin bloquear automáticamente, para evitar falsos positivos por cambio de hardware)

---

## 2. Seguridad de la aplicación (PRIORIDAD ALTA)

Fixes de seguridad identificados que no requieren el VPS pero se posponen para hacerlos todos juntos:

### 2.1 CORS restrictivo
**Archivo**: `backend/app/main.py`
```python
# Cambiar:
allow_origins=["*"]
# Por:
allow_origins=[settings.FRONTEND_URL]  # nueva variable en config.py y .env
```
Añadir a `.env`: `FRONTEND_URL=http://localhost:3000`

### 2.2 Rate limiting en login
**Archivo**: `backend/app/api/v1/routes/auth.py`
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/5minutes")  # 5 intentos cada 5 minutos por IP
async def login(request: Request, ...):
    ...
```

### 2.3 Cap de paginación
En todos los endpoints de lista, añadir:
```python
limit: int = Query(default=50, le=100)  # máximo 100, nunca más
```

### 2.4 Validación de SECRET_KEY al arrancar
**Archivo**: `backend/app/core/config.py`
```python
@model_validator(mode="after")
def check_secret_key(self):
    if self.SECRET_KEY == "CAMBIA_ESTO_EN_PRODUCCION_usa_openssl_rand_hex_32":
        raise ValueError(
            "SECRET_KEY no puede ser el valor por defecto. "
            "Genera una clave segura: openssl rand -hex 32"
        )
    return self
```

### 2.5 Tokens en HttpOnly cookies (largo plazo)
Actualmente los JWT se guardan en `localStorage`, vulnerable a XSS.
La solución correcta es `HttpOnly cookies` (el token nunca es accesible desde JavaScript).
Requiere cambios en backend (Set-Cookie) y frontend (eliminar gestión manual del token).
Dejar para cuando se estabilice la autenticación.

---

## 3. Recuperación de contraseña (PRIORIDAD MEDIA)

Actualmente no existe flujo de "olvidé mi contraseña". Si un cliente pierde acceso, no puede recuperarlo solo.

**Flujo**:
```
1. Usuario introduce email en /auth/forgot-password
2. Backend genera token seguro (JWT, expira en 1 hora), lo guarda en Redis
3. Backend envía email con enlace: https://app/auth/reset?token=XXX
4. Usuario hace clic → formulario de nueva contraseña
5. Backend valida token (no expirado, no usado), actualiza password, invalida token
```

**Requiere**: servicio de email configurado (SMTP o SendGrid). Ya hay `email_agent.py` en el proyecto pero no está conectado al flujo de auth.

---

## 4. Audit trail completo (PRIORIDAD MEDIA)

La tabla `AuditLog` existe en el modelo de datos pero no se rellena de forma consistente.
Muchas operaciones críticas (borrar factura, cambiar salario, revocar acceso) no dejan rastro.

**Solución recomendada**: SQLAlchemy event listeners automáticos.

```python
# backend/app/db/audit.py
from sqlalchemy import event

AUDITED_MODELS = [Invoice, Client, Employee, Payroll, Workflow]

for model in AUDITED_MODELS:
    @event.listens_for(model, 'after_insert')
    def audit_insert(mapper, connection, target):
        log_audit(action="create", entity=model.__tablename__, entity_id=target.id)

    @event.listens_for(model, 'after_update')
    def audit_update(mapper, connection, target):
        log_audit(action="update", entity=model.__tablename__, entity_id=target.id)

    @event.listens_for(model, 'after_delete')
    def audit_delete(mapper, connection, target):
        log_audit(action="delete", entity=model.__tablename__, entity_id=target.id)
```

Relevante para cumplimiento GDPR: derecho de acceso (qué datos tiene el sistema sobre el usuario) y trazabilidad de cambios.

---

## 5. Backup automático de base de datos (PRIORIDAD MEDIA)

Sin backup, una corrupción del volumen Docker significa pérdida total de datos del cliente.

**Solución simple**: añadir servicio `backup` al `docker-compose.yml`.

```yaml
backup:
  image: postgres:15-alpine
  depends_on:
    - db
  environment:
    PGPASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - ./backups:/backups
  entrypoint: >
    sh -c "pg_dump -h db -U ${POSTGRES_USER} ${POSTGRES_DB}
           > /backups/pyme_db_$$(date +%Y%m%d_%H%M).sql
           && find /backups -name '*.sql' -mtime +7 -delete"
  profiles: ["backup"]   # no arranca por defecto, se lanza manualmente o con cron
```

El cliente ejecutaría `docker-compose --profile backup up backup` manualmente o programado con el Programador de tareas de Windows.

---

## 6. Índices de base de datos en claves foráneas (PRIORIDAD BAJA)

Actualmente las columnas FK no tienen índice. Con pocos datos no se nota, pero con uso real las consultas de facturación se vuelven lentas.

**Migración a crear** (Alembic):
```python
op.create_index('ix_invoice_lines_product_id', 'invoice_lines', ['product_id'])
op.create_index('ix_invoice_lines_invoice_id', 'invoice_lines', ['invoice_id'])
op.create_index('ix_payrolls_employee_id', 'payrolls', ['employee_id'])
op.create_index('ix_tasks_tenant_id', 'tasks', ['tenant_id'])
op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
```

---

## 7. Control de gasto LLM por tenant (PRIORIDAD BAJA)

Sin límites, un usuario que automatice tareas agresivas puede generar facturas altas de API.

**Diseño**:
- Nueva columna `monthly_token_budget: int` en tabla `Tenant` (default: 500.000 tokens/mes)
- Contador en Redis: `tokens:{tenant_id}:{YYYY-MM}` → se incrementa con cada llamada LLM
- Antes de cada llamada al LLM: comprobar si el contador supera el presupuesto → `HTTP 429` si sí
- Reset automático el día 1 de cada mes (TTL en Redis)

---

## Resumen de estado

| # | Funcionalidad | Depende de | Estado |
|---|---|---|---|
| 1 | Sistema de licencias | VPS disponible | Pendiente |
| 2 | Seguridad mínima (CORS, rate limit, etc.) | Nada | Pendiente |
| 3 | Recuperación de contraseña | Servicio email | Pendiente |
| 4 | Audit trail completo | Nada | Pendiente |
| 5 | Backup automático BD | Nada | Pendiente |
| 6 | Índices FK en BD | Nada | Pendiente |
| 7 | Control de gasto LLM | Nada | Pendiente |
