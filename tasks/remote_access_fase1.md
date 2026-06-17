# Acceso remoto — Fase 1 (prospecto que lo pide: 10+ empleados, sin instalar)

Decisión: 10+ empleados + "solo URL" → **Cloudflare Tunnel** (Tailscale descartado).
Disciplina: Fase 1 = hacer funcionar a ESTE prospecto con túnel manual + validar.
Auto-provisión multi-cliente → Fase 2 (solo si llega un 2º cliente).

Runbook de despliegue: `docs/remote-access-cloudflare.md`.

**Estado:** conectividad **validada end-to-end** (móvil 4G → quick tunnel +
proxy `tools/dev-tunnel-proxy.js`) — el deal es técnicamente viable. Túnel de
prueba ya cerrado. H2 RBAC resuelto. Siguiente: túnel con nombre + Access para
el prospecto real (operativa de Marcos) y, opcional, C2/H1.

## Hecho (código, verificado)

- [x] `frontend/src/lib/api/base.ts` — resolver único (HTTP + WS). Mismo origen
      tras proxy/túnel; absoluto `:8080` en directo. tsc --noEmit EXIT 0.
- [x] `client.ts`, `error-reporter.ts`, `useNotificationSocket.ts` → usan el resolver.
- [x] `middleware/rate_limit.py` — IP real vía `CF-Connecting-IP`/`X-Forwarded-For`
      solo desde peer loopback (no spoofable desde fuera). Import OK.
- [x] `core/net.py` + `auth.py` — `/auth/register` solo local (loopback sin
      cabeceras de proxy). Tests: `test_api_auth.py` 13 passed (incl. 2 nuevos
      que fijan el bloqueo remoto).
- [x] `main.py` — `openapi_url` cerrado en producción (igual que /docs, /redoc).

## Operativa (no-código, lo hace Marcos)

- [ ] Crear túnel con nombre sobre su dominio Cloudflare + `config.yml` con el
      ingress allowlist (`/api/v1` + `/ws` → 8080; resto → 3000).
- [ ] **Cloudflare Access** delante del hostname (emails de los empleados / SSO).
- [ ] Validar end-to-end desde 4G antes de entregar la URL al prospecto.
- [ ] Confirmar `DEBUG=False` y backend en `0.0.0.0:8080`.

## Pendiente antes de cuentas de empleado no-admin (Fase 1.5)

Revisión de seguridad — hallazgos abiertos (aceptables para piloto 1-admin):

- [x] **H2 RBAC** ✅: bulk-import (`routes/import_bulk.py`, dependencia a nivel
      de router) y gestión de integraciones connect/disconnect/auth-url
      (`routes/integrations.py`) exigen `require_role("admin")`. Los roles
      `user`/`viewer` ya no pueden mutar en masa ni cortar el banco/email; las
      lecturas (status/recent/list) siguen abiertas. Tests:
      `test_rbac_admin_endpoints.py` (5) + suite import/integrations (45).
- [ ] **C2 lockout por cuenta**: bloqueo por email tras N intentos fallidos
      (hoy solo límite por IP `5/5min`; Access cubre el grueso desde internet).
- [ ] **H1 token WS**: mover `?token=` al primer frame del WS; acortar TTL access.
- [ ] **C3 CORS LAN**: si algún cliente usa LAN directa, `FRONTEND_URL` debe
      incluir la IP LAN (en modo túnel es mismo origen, no aplica).

## Fase 2 (diferido — solo con 2º cliente)

- [ ] Empaquetar `cloudflared` en el instalador Electron.
- [ ] UI de auto-provisión (túnel + hostname por cliente desde la app).
- [ ] `PUBLIC_URL` configurable para redirects OAuth de integraciones en remoto.
