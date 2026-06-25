# Inbox /forja — hallazgos en frontend/src (2026-06-25, barrido #14)

0 auto-fixes: el loop NO puede verificar frontend (worktree sin `node_modules` → no corre
tsc/eslint/vitest ni la UI). Estos necesitan tu mano (corre las gates + navegador):

## ⚠️ ALTA — seguridad
1. **`app/(dashboard)/albaranes/_hooks/useAlbaranes.ts:100` JWT en la URL** [alta]. El download
   del PDF hace `a.href = url + "?token=" + token` → el access token queda en logs del server,
   historial del navegador, `Referer` y proxies. Fix: fetch con `Authorization: Bearer` en header +
   blob-download, como `lib/api/client_portal.ts::downloadInvoicePdf`. (Cambia el flujo de descarga →
   verifica en navegador.)
2. **`lib/secureStore.ts:98,74` JWT en `localStorage` en build web** [alta]. El fallback web guarda
   access/refresh token en `localStorage` → cualquier XSS los lee. En Electron está protegido
   (`safeStorage`), pero el modo web los expone. Fix propuesto: `sessionStorage` para el fallback web.
   ⚠️ Cambia comportamiento (no sobrevive cierre de pestaña; afecta refresh) → decisión humana.

## Media / baja
3. **`lib/error-reporter.ts:35` `fetch()` directo fuera de `lib/api/`** [media arch]. El comentario
   alega dependencia circular, pero `client.ts` no importa este fichero (no se sostiene). Fix: mover a
   `lib/api/system.ts` con `request()`, o documentar el endpoint como público y moverlo a `lib/api/`.
4. **`lib/api/client_portal.ts` `portalRequest` sin refresh de token** [baja]. Excepción documentada
   (JWT de portal ≠ empresa), aceptable, pero si el JWT de portal expira da 401 sin reintentar → la UI
   del cliente rompe en silencio. Considerar refresh o re-login limpio.

## Nota de capacidad del loop
- El frontend es el único área donde el loop no puede auto-verificar (sin node_modules en worktree).
  Para fixes de frontend: corre `npx tsc --noEmit` + `npx eslint src/` + `npm run test:ci` en
  `frontend/` tras aplicar, y prueba en navegador.
