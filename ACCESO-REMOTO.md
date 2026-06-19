# Acceso remoto — decisión de producto y arquitectura

> **Posicionamiento:** el acceso remoto es una **feature del plan de 180 €/mes**.
> No es un extra gratuito: es una palanca de venta del plan premium (y eso
> justifica construir la automatización cuando esté validada — es ingreso, no
> solo coste).

Documentos relacionados:
- Runbook de montaje manual: [docs/remote-access-cloudflare.md](docs/remote-access-cloudflare.md)
- Estado y pendientes técnicos: [tasks/remote_access_fase1.md](tasks/remote_access_fase1.md)

---

## 1. Qué es y cómo funciona (resumen)

El PC de la oficina corre la app (backend `:8080`, frontend `:3000`, Postgres).
Un empleado en casa no ve ese `localhost`. La solución:

`cloudflared` (en el PC) abre una conexión **de salida** a Cloudflare — **no se
abren puertos ni hace falta IP fija**. Cloudflare publica una URL estable bajo
**tu** dominio (`cliente.automatizacore.com`) y mete las peticiones por ese canal
hasta el PC.

Claves que ya están en el código (Fase 1, hecho):
- El frontend resuelve el backend por **mismo origen** cuando se sirve tras el
  túnel → sin CORS, sin exponer el `:8080` (`frontend/src/lib/api/base.ts`).
- Ruteo por path: `/api/v1` y `/ws` → `:8080`; el resto → `:3000`. Nada más es
  accesible desde internet.
- Endurecimiento: registro local-only, rate-limit por IP real, RBAC admin,
  `/openapi.json` cerrado en producción.

---

## 2. Estado

- **Fase 1 — conectividad: HECHA y VALIDADA.** Probada end-to-end desde 4G con un
  quick tunnel. El código va en el `.exe`; la app está "lista para ser tunelada".
- **Fase 2 — el botón "Activar acceso remoto": PENDIENTE.** Condicionada a
  (a) validar que los clientes pagan por ello y (b) la decisión de operador (§4).

Hoy el túnel se monta **a mano, por cliente** (runbook). El `.exe` NO crea túneles.

---

## 3. La mecánica del botón (Fase 2, cuando toque)

1. El cliente pulsa *Activar acceso remoto*.
2. La app llama a **tu servidor** (el de licencias en Render).
3. Tu servidor —con el token de Cloudflare guardado **server-side**, nunca en el
   `.exe`— crea el túnel + el subdominio `clienteX.automatizacore.com` y devuelve
   un *tunnel token*.
4. La app arranca el `cloudflared` empaquetado como **servicio de Windows**
   (autoarranque con el PC, reconexión sola, URL estable).

Lo que **sí** se autogestiona: arranque, reconexión, persistencia de la URL.

---

## 4. La decisión clave: ¿quiero ser el operador?

El botón turnkey **te convierte en el proveedor/operador del acceso remoto de
todos tus clientes**. Esto choca con la filosofía que ya elegiste en **Zernio**
(BYO API key — "no soy soporte multitenant").

¿Por qué no aplicar BYO aquí (que el cliente traiga su dominio/Cloudflare)?
Porque **una pyme no registra ni configura un dominio**. Copiar una API key es
trivial; montar Cloudflare no. El equivalente BYO **no cuela** con pymes.

**El fork, sin punto medio limpio:**

| Opción | Experiencia | ¿Eres operador? |
|---|---|---|
| **Botón turnkey** | Un clic, subdominio automático | **Sí** — todos los túneles bajo tu cuenta/dominio |
| **Montaje asistido** | Lo configuras tú con cada cliente | **No** — pero no es un botón |

Implicaciones de ser operador:
- **Punto único de fallo:** si tu cuenta de Cloudflare cae/suspende, **todos** los
  clientes pierden acceso a la vez.
- Eres el conducto de los datos financieros de todos ellos y el soporte si algo falla.

---

## 5. Costes

- **Túneles de Cloudflare: gratis e ilimitados.**
- **Cloudflare Access (el portero de identidad): ~50 usuarios gratis EN TOTAL** en
  tu cuenta (no por cliente). Más allá: ~7 €/usuario/mes.
- El plan es **180 €/empresa/mes (flat)**, no por usuario. Así que el coste de
  Access (COGS) **escala con el nº total de empleados** entre todos los clientes y
  empieza a comer margen pasados ~50 usuarios.
- **Mitigación:** Access es opcional. Sin él, el túnel sigue gratis y la seguridad
  recae en el login de la app + el subdominio no adivinable (algo menos robusto).
  Decisión a tomar según volumen.

---

## 6. Recomendación / próximos pasos

1. **Registrar `automatizacore.com`** (necesario igual: web, email, licencias, subdominios).
2. Montar el túnel **a mano** para el primer prospecto (operador de uno solo,
   riesgo mínimo, cero construcción).
3. **Validar que pagan** por el acceso remoto como parte del plan de 180 €.
4. **Solo entonces** decidir operador sí/no:
   - Si 2-3 clientes lo piden y el dinero lo justifica → construir el botón (Fase 2).
   - Si no → quedarse en montaje asistido.

### Antes de dar de alta empleados no-admin (Fase 1.5)
Pendientes de seguridad documentados en
[tasks/remote_access_fase1.md](tasks/remote_access_fase1.md): C2 (lockout por
cuenta) y H1 (token WS en la URL).
