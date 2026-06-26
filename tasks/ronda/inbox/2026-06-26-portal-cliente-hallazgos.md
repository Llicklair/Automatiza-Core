# Inbox /forja (run-2, híbrido) — portal del cliente (2026-06-26, lente seguridad/IDOR)

Marco global: el portal usa auth propia — `authenticate_portal` valida un `portal_token` y emite un
`client_portal_access_token` con (client_id, tenant_id). **Calibración clave: RLS solo aísla por tenant,
NO por client** → había que verificar el filtro por `client_id` en cada endpoint.

## ✅ RESULTADO: portal SÓLIDO en IDOR (sin defecto alto)
Verificados los WHERE reales: `/me` (`Invoice.client_id == client.id` + tenant), `/invoices/{id}/pdf`
(filtra id + client_id + tenant), y `get_current_client_portal` valida pertenencia del token. Ningún
endpoint cliente devuelve recursos de otro cliente del mismo tenant. **No hay IDOR.** (Resultado limpio
y verificado, no ausencia de búsqueda.)

## Menores (no auto-fixeables — decisión/diferible)
1. **[baja] `client_portal.py:131-137` `authenticate_portal` busca el token sin anclar tenant** — el lookup
   `WHERE token_hash == h AND is_active` no filtra tenant (los demás lookups del fichero sí). El `token_hash`
   es SHA-256 de 32 bytes (`secrets.token_urlsafe`) → inaprovechable por entropía. Inconsistencia
   estructural, no explotable. Fix no trivial (el tenant se RESUELVE del token, no se conoce antes) →
   defensa en profundidad diferible.
2. **[media, diseño] `client_portal.py:89` token en la URL del magic-link** —
   `portal-cliente?token={raw_token}` deja el secreto en logs de proxy/CDN, historial del navegador y
   `Referer`. Patrón estándar de magic-link, pero riesgo de fuga del token mientras el enlace esté activo
   (caducidad 1-365d, default 90). Mitigaciones posibles: token en fragmento `#` (no viaja al servidor/Referer),
   o intercambio inmediato por cookie httpOnly al primer uso, o TTL más corto. Decisión de UX/diseño.
