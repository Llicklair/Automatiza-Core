# ⚠️⚠️ Inbox /forja — users: ESCALADA DE PRIVILEGIOS (2026-06-26, ALTA)

Turno de `routes/users.py` (3 lentes). Hallazgo crítico, anota aparte de la prosa:

## 🔴 ALTA — cualquier usuario puede crearse/ascenderse a ADMIN
- **`routes/users.py:68-83` `create_user`** usa `Depends(get_current_user)` (cualquier autenticado), **NO**
  `require_role("admin")`. `UserCreate.role: str = "user"` sin validar. → un `employee` hace `POST /users`
  con `{"role":"admin",...}` y **crea un admin** en su tenant. (Las invitaciones SÍ están admin-gated; esta
  ruta directa lo omite.)
- **`routes/users.py:278-296` `PATCH /{user_id}`** tampoco tiene `require_role("admin")`. → un `employee`
  puede **cambiar su PROPIO rol a admin**, desactivar a otros, o ascender a otros. `delete_user` (L303) SÍ
  está gateado; el PATCH y el POST son los agujeros.
- **Fix (objetivo, bajo riesgo):** cambiar `Depends(get_current_user)` → `Depends(require_role("admin"))` en
  `create_user` (~L71) y en el `PATCH` (~L283), igual que ya hacen `delete_user`/invitaciones. **+**
  validar `role in ALLOWED_ROLES` en `create_user`/`update_user` del servicio (hoy solo `create_invitation`
  lo valida → `role` arbitrario "superadmin" persistible).

## 🔴 Alta — borrar el último admin deja el tenant sin gestión
- **`user_service.py:76-78` `delete_user`** = `db.delete()` + commit sin guard. Un admin puede borrarse a sí
  mismo / al único otro admin → tenant SIN admin, irrecuperable desde la UI. Fix: si `role=="admin"`, contar
  admins activos del tenant y rechazar (409) si quedaría en 0.

## Media — patrón / errores
- `role` como `str` libre (sin `Literal`/enum) en `UserCreate` + sin guard `ALLOWED_ROLES` en
  `create_user`/`update_user` (sí en `create_invitation`). Patrón inconsistente.
- `create_user` sin pre-check de email duplicado ni `except IntegrityError` → 500 en vez de 409 (hermana
  del create→409; `create_invitation` sí lo hace).
- `accept_invitation` (`routes/users.py:240`) `select(User).where(User.email == inv.email)` **sin
  `tenant_id`** → un email que existe en OTRO tenant bloquea la aceptación legítima. Fix: añadir
  `User.tenant_id == inv.tenant_id`. (Raíz: `User.email unique=True` global vs modelo multi-tenant → decisión.)
- `update_user` full_name: PATCH con solo `first_name` borra el apellido previo.

## Baja
- `GET /{user_id}` abierto a cualquier usuario del tenant (fuga menor de info intra-tenant; sin hash).

**Recomendación: los dos primeros (create_user / PATCH sin admin-gate) son lo más urgente del inbox entero
— escalada de privilegios trivial. Fix de 2 líneas + validación de rol. Revísalo pronto.**
