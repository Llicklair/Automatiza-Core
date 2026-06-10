# Auditoría brutal — Frontend AutomatizaCore (2026-06-10)

> ✅ **Quick-wins COMPLETADOS 2026-06-11** — #5 home y #8-EmptyState en 4664abd/b126a3a;
> esta ronda: #1 idiomas (2744a34), #2 marketing (d6f36f7), #12 sonner + ToastContainer
> (2714dcb — bonus: el toast store NO tenía renderer, todos los toasts del repo eran
> invisibles), #4 alert/confirm 16 callsites (406affc), #8-PageHeader (5dacc49),
> #3 loading.tsx ×10 (7a28add).
> ✅ **#9 páginas monstruo COMPLETADO 2026-06-11** — 7 páginas troceadas al patrón
> `_components/`/`_hooks/` (5.209 → ~906 líneas de page.tsx): marketing 743→63
> (e84eb61), analitica 969→163 (0fd3a2f), portal 763→145 (f868429), correos 660→145
> (3ec520b), usuarios 609→179 (b62e1a2), clientes 537→153 (e0c743a), email-marketing
> 528→58 (9eb154a). Pure-move verificado con tsc por página + next build final.
> Pendiente anotado: doble carga de accounts() entre TabCuentas/TabCrear (marketing).
> ✅ **#10 polling COMPLETADO 2026-06-11** — hook `lib/hooks/usePolling` (enabled +
> pausa en pestaña oculta con catch-up, 7 tests) en b8d3886; ApprovalsTab pasa a
> push WS approval_created + respaldo 60s, ActivityTab/usePendingApprovalsCount
> migrados (dc8eb92); 6 polls continuos migrados — layout (ahora reactivo a
> hydrated/token, antes podía no arrancar), useMiEquipo, useTaskPanel, useFichajes,
> useEscaner, useAutomatizacionesExecution (7619fdc). Polls acotados de OAuth/tasks
> y UI ticks intactos a propósito (pausarlos rompería las esperas OAuth).
> Pendientes (proyectos, no quick-wins): #7 a11y,
> #11 tokens de diseño/PageContainer, #6 tabs, migración i18n real (#1 fase 2),
> y el alert de `portal-cliente/page.tsx` (fuera del layout, sin ToastContainer).

Alcance: `frontend/src` (Next.js App Router + Tailwind + next-intl + Electron). Muestreo: home, bandeja, facturas (compras/ventas), banca, rrhh, marketing, analítica, configuración, `components/ui|shared`, stores, hooks.

**Veredicto general**: la base es buena — cero `fetch()` directo fuera de `lib/api` (regla cumplida al 100%), patrón `_components/` + `_hooks/` por página, DataTable de tanstack, home bien descompuesta (91 líneas). Los problemas reales son: i18n abandonada a medias, dos migraciones de componentes estancadas, errores silenciados, y media docena de páginas monstruo.

---

## UX / Diseño

### 1. [ALTO] i18n es una fachada: la app está hardcodeada en español
- **Archivos**: 109 `page.tsx`; solo 24 archivos usan `useTranslations`. Existen catálogos completos `src/messages/{es,en,ca,eu,gl}.json` (432 líneas c/u) y selector de idioma en `configuracion/idioma`.
- **Qué está mal**: el usuario puede cambiar a catalán/euskera/inglés y ~80% de la UI sigue en español (53 "Cargando…" hardcodeados, títulos, botones, toasts). Vendes una opción rota.
- **Mejora**: decisión de producto: o se completa la migración por módulos (proyecto, ~2-3 días con script de extracción), o se ocultan los idiomas no soportados del selector hasta entonces (**quick-win**, 10 min). Lo segundo primero.

### 2. [ALTO] Errores silenciados = usuario a ciegas
- **Archivos**: 16 `catch {}` / `catch { /* ignore */ }` (concentrados en `marketing/page.tsx`: líneas 119, 162, 177, 280, 396, 408, 548, 556) + 50 mensajes genéricos "Error al cargar / No se pudo…".
- **Qué está mal**: si falla publicar un post o cargar cuentas sociales, no pasa nada visible. En un ERP, un fallo silencioso en facturación/banca destruye confianza.
- **Mejora**: regla: todo catch en handler de acción de usuario → `toast.error()` con el detalle de `ApiError` (ya existe `lib/api/errors.ts`). Los catch de polling pueden seguir silenciosos pero con comentario explícito. **Quick-win** por archivo; barrido completo ~1 día.

### 3. [MEDIO] Skeletons existen pero casi nadie los usa
- **Archivos**: `components/shared/Skeletons.tsx` y `ui/skeleton.tsx` → usados en solo 2 archivos de `app/`. Solo ~9 rutas tienen `loading.tsx` de 109 páginas. El loading dominante es texto "Cargando…" o spinner.
- **Mejora**: añadir `loading.tsx` con skeleton de tabla/cards a las 10 rutas más usadas (facturas, banca, clientes, rrhh, bandeja). **Quick-win** (es copy-paste del patrón existente en `clientes/loading.tsx`).

### 4. [MEDIO] `alert()` y `window.confirm()` nativos en flujos reales
- **Archivos**: `app/(dashboard)/clientes/portal/page.tsx:107,123`, `app/(dashboard)/mi-equipo/_components/EmployeeGrid.tsx:46`, `app/portal-cliente/page.tsx:72`.
- **Qué está mal**: ya existen `stores/confirm.ts` y `stores/toast.ts`; estos 4 sitios rompen el lenguaje visual (diálogo nativo de Electron/Chromium, sin estilo).
- **Mejora**: migrar los 4 callsites al confirm/toast store. **Quick-win** (30 min).

### 5. [MEDIO] Home: buen "centro de mando", pero 12+ secciones sin priorización
- **Archivo**: `app/(dashboard)/page.tsx` — MorningBrief, KPIs, AiInsights, Cashflow, RecentInvoices, AiActivity, Approvals, RRHH, LiveTeam, TimeSaved, Usage, Integrations + AiChatBar.
- **Qué está mal**: técnicamente impecable (descompuesta, ErrorBoundary), pero todo pesa igual: el primer scroll no distingue "qué requiere mi acción hoy" (aprobaciones) de métricas vanidosas (TimeSaved, Usage). Para una pyme, aprobaciones pendientes y tesorería deberían ir arriba.
- **Mejora**: no rediseñar — reordenar: Approvals + MorningBrief + KPIs arriba; TimeSaved/Usage/Integrations colapsados o al pie. Opcional: secciones ocultables persistidas en preferencias. **Quick-win** el reorden; preferencias = mini-proyecto.

### 6. [BAJO] Bandeja: sólida, pequeños detalles
- **Archivo**: `app/(dashboard)/bandeja/page.tsx` (76 líneas, tab en URL — bien). Tabs hechos a mano en vez de `ui/tabs.tsx`; el patrón tab-custom se repite también en `banca/page.tsx`.
- **Mejora**: unificar con `ui/tabs.tsx` cuando se toque la página. **Quick-win** oportunista.

### 7. [BAJO] Accesibilidad mínima
- 52 `aria-label` en toda la app (35 archivos con algún `aria-*`); el `ui/EmptyState` nuevo sí cuida ARIA pero nadie lo usa (ver hallazgo 8). Iconos lucide mayormente sin `aria-hidden`. Contraste: paleta oscura con `text-muted-foreground` sobre fondos sutiles — revisar en los 62 hex hardcodeados (hallazgo 11).
- **Mejora**: barrido de botones icon-only (eliminar, refrescar, cerrar) añadiendo `aria-label`. Proyecto pequeño (~medio día), priorizar tablas de facturas/banca.

---

## Deuda técnica frontend

### 8. [ALTO] Dos migraciones de componentes estancadas: EmptyState y PageHeader duplicados
- **Archivos**: `components/ui/EmptyState.tsx` (nuevo, ARIA, deprecó al viejo) → **0 importadores**; `components/shared/EmptyState.tsx` (marcado `@deprecated`) → 12 callsites. `shared/PageHeader` 40 usos vs `ui/PageHeader` 4.
- **Qué está mal**: el comentario del deprecated dice "mientras se migran los ~10 callsites" — nadie migró nada y el nuevo código sigue importando el viejo (p.ej. `compras/facturas/page.tsx`). Dos estilos visuales conviviendo (gris vs acento).
- **Mejora**: migrar los 12 EmptyState + decidir un único PageHeader y borrar el otro. **Quick-win** (1-2 h) que elimina divergencia visual futura.

### 9. [ALTO] Páginas monstruo con múltiples componentes-con-estado en un archivo
- **Archivos**: `analitica/page.tsx` (969), `portal/page.tsx` (763), `marketing/page.tsx` (725, con 3+ componentes internos cada uno con su `loading`), `correos/page.tsx` (660), `configuracion/usuarios/page.tsx` (600), `clientes/page.tsx` (541), `email-marketing/page.tsx` (518).
- **Qué está mal**: contradicen el patrón propio del repo (`_components/` + `_hooks/`) que banca, automatizaciones y rrhh sí siguen. Marketing mezcla composer, feed y settings en un client component → re-render de todo al teclear.
- **Mejora**: trocear al patrón `_components/_hooks` empezando por marketing y analítica (las que más crecen). Proyecto (~1 día por página). No urgente, pero cada feature nueva ahí encarece.

### 10. [MEDIO] Polling everywhere con intervalos arbitrarios, teniendo ya SSE/WS
- **Archivos**: 16+ hooks con `setInterval` (valores: 1s ×3, 3s, 4s, 10s, 30s, 60s ×3) — `bandeja/ApprovalsTab` 10s, `useAgentPolling`, `useMiEquipo`, etc. Mientras, existen `lib/api/taskStream.ts` (EventSource) y `lib/hooks/useNotificationSocket.ts`.
- **Qué está mal**: en desktop el coste es bajo, pero los intervalos de 1s son agresivos y cada página inventa su frecuencia. Doble fuente de verdad (socket de notificaciones + polling paralelo).
- **Mejora**: hook compartido `usePolling(fn, ms)` con pausa en pestaña oculta, y migrar aprobaciones/actividad al socket de notificaciones que ya emite eventos. Proyecto pequeño.

### 11. [MEDIO] Tokens de diseño con fugas: 62 hex hardcodeados + padding inconsistente
- **Datos**: 62 colores `#xxxxxx` inline en páginas; wrappers de página `p-8` (62) vs `p-6` (28) vs `p-4` (17); `bandeja` usa `px-4 py-8 max-w-5xl`, home `p-8 max-w-[1400px]`.
- **Mejora**: componente `PageContainer` (padding + max-width únicos) y sustituir hex por tokens al tocar cada página. **Quick-win** el componente; el barrido es oportunista.

### 12. [MEDIO] Doble sistema de toasts
- **Archivos**: `stores/toast.ts` (zustand, 60 archivos) vs `sonner` (solo `configuracion/backups/page.tsx` + `ui/sonner.tsx`).
- **Mejora**: migrar backups al store y eliminar sonner del bundle. **Quick-win** (20 min).

### 13. [BAJO] Lo que está bien (no tocar)
- `lib/api/client.ts` único punto HTTP con refresh 401; 55 módulos de dominio en `lib/api/`; cero prop-drilling grave (stores zustand puntuales: toast, confirm, notifications, license); ErrorBoundary por sección en home; tests de contrato en `lib/api/__tests__`.

---

## Top 5 por ROI
1. (#2) Dejar de silenciar errores → toast con detalle. Confianza inmediata.
2. (#8) Cerrar la migración EmptyState/PageHeader y borrar duplicados.
3. (#1) Ocultar idiomas no traducidos del selector (y decidir si se completa i18n).
4. (#4 + #12) Eliminar alert/confirm nativos y sonner — 1 hora total.
5. (#5) Reordenar home: aprobaciones y tesorería arriba, métricas vanidosas abajo.
