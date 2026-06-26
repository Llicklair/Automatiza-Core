# /forja — `users` follow-ups (diferido del fix de escalada de privilegios)

Turno 2026-06-26 (L2 seguridad). El hallazgo principal (escalada de privilegios en `create_user`/`update_user`)
se ARREGLÓ y está en **PR #57** (`loop/forja/auth-privesc`). Estos quedan para decisión humana:

## 🟠 C5 — `delete_user` sin guard de "último admin"
`backend/app/services/user_service.py:76-78` — `db.delete(user); db.commit()` sin comprobar si es el último
admin activo del tenant. Un admin puede borrarse a sí mismo / al único otro admin → tenant **sin administrador**,
irrecuperable desde la UI. **Fix propuesto:** si `user.role == "admin"`, contar admins activos del tenant y
rechazar (409 `ConflictError`) si quedaría en 0. *No auto-fixeado:* cambia comportamiento de borrado + decisión
de negocio (¿bloquear o degradar?). No explotable por un no-admin (la ruta ya está admin-gated).

## 🟡 `accept_invitation` — lookup sin `tenant_id`
`backend/app/api/v1/routes/users.py:240` — `select(User).where(User.email == inv.email)` sin anclar `tenant_id`.
Un email que ya existe en OTRO tenant bloquea la aceptación legítima de una invitación. Raíz: `User.email
unique=True` global vs modelo multi-tenant. **Fix:** añadir `User.tenant_id == inv.tenant_id` al WHERE — pero
revisar antes la intención del `unique` global (¿se quiere permitir el mismo email en varios tenants?). Decisión.

## 🟡 `create_user` sin pre-check de email duplicado → 500 en vez de 409
`create_user` no hace pre-check ni `except IntegrityError` (a diferencia de `create_invitation`). Email repetido
→ 500 opaco. Hermana del patrón `create→409` ya aplicado en otras entidades. Fix: `try/except IntegrityError →
ConflictError`. Bajo riesgo, pero toca camino de error → encolar como fix dedicado.

## ⚪ Baja — `GET /users/{id}` abierto a cualquier usuario del tenant
Fuga menor de info intra-tenant (sin hash de password). Decisión de producto si se quiere restringir a admin/propio.
