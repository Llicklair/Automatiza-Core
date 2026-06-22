# react-hooks/exhaustive-deps — resolución de los 16 warnings

**Fecha:** 2026-06-22
**Resultado:** 16 → 0 warnings · `tsc --noEmit` OK · `eslint --max-warnings 0` OK · `test:ci` 171/171 OK

Nota clave: `t` proviene de `useTranslations` (next-intl) y es referencialmente
estable mientras no cambien locale/namespace. Por eso añadirlo a un array de deps
(o como dep de un `useCallback`/`useMemo`) NO provoca bucles de render: a lo sumo
re-ejecuta al cambiar de idioma, que es el comportamiento correcto.

| fichero:línea | hook | dep(s) que faltaban | fix aplicado | por qué |
|---|---|---|---|---|
| `automatizaciones/_hooks/useAutomatizacionesCRUD.ts:130` | `useMemo` (defaultEditorNodes) | `TRIGGER_LABELS`, `t` | `TRIGGER_LABELS` se envolvió en `useMemo([t])` para estabilizarlo; luego se añadieron `TRIGGER_LABELS` y `t` al array | `TRIGGER_LABELS` se recreaba cada render (objeto dependiente de `t`); añadirlo crudo rompería el memo → primero estabilizar, después añadir |
| `banca/_hooks/useAgentPolling.ts:38` | `useCallback` (launch) | `t` | add-dep: `[stop, t]` | `t` estable; sólo se usa en el fallback de error |
| `compliance/_components/BOETab.tsx:58` | `useEffect` | `fetchBOE` | `fetchBOE` → `useCallback([t])`; effect deps `[seccion, fetchBOE]` | la función se recreaba cada render → estabilizar con useCallback antes de añadirla |
| `compliance/_components/CalendarioTab.tsx:69` | `useEffect` (mount) | `t` | add-dep: `[t]` | effect inline; `t` estable, sólo deriva strings de alerta |
| `configuracion/actualizaciones/_hooks/useActualizaciones.ts:84` | `useEffect` (mount) | `loadHealth` | `loadHealth` → `useCallback([t])`; effect deps `[loadHealth]` | función recreada cada render → estabilizar y añadir |
| `configuracion/autonomia/page.tsx:69` | `useCallback` (load) | `t` | add-dep: `[toast, t]` | `t` estable; sigue el patrón ya existente con `toast` |
| `configuracion/backups/page.tsx:74` | `useEffect` (mount) | `reload` | `reload` → `useCallback([toast, t])`; effect deps `[reload]` | función recreada cada render → estabilizar y añadir |
| `escaner/_components/ErpImportReview.tsx:41` | `useEffect` | `loadPreview` | `loadPreview` → `useCallback([documentId, t])`; effect deps `[loadPreview]` | función recreada cada render; se mantiene la llamada sin target en el effect |
| `impuestos/_components/Expediente303Drawer.tsx:40` | `useEffect` | `t` | add-dep: `[open, quarter, year, t]` | effect inline (promesa); `t` estable, sólo fallback de error |
| `impuestos/_components/PreventiveCheckCard.tsx:84` | `useEffect` | `t` | add-dep: `[quarter, year, t]` | idéntico patrón al anterior |
| `inventario/almacenes/page.tsx:37` | `useEffect` (mount) | `load` | `load` → `useCallback([t])`; effect deps `[load]` | función recreada cada render → estabilizar y añadir |
| `inventario/reposicion/page.tsx:33` | `useEffect` (mount) | `load` | `load` → `useCallback([t])`; effect deps `[load]` | igual |
| `inventario/stock/_components/LotsPanel.tsx:72` | `useEffect` | `load` | `load` → `useCallback([productId, t])`; effect deps `[load]` | igual (depende de `productId`) |
| `inventario/stock/_components/WarehouseStockPanel.tsx:44` | `useEffect` | `load` | `load` → `useCallback([productId, t])`; effect deps `[load]` | igual |
| `mi-equipo/_hooks/useMiEquipo.ts:59` | `useCallback` (loadData) | `t` | add-dep: `[t]` | `t` estable; `loadData` lo usa en fallback. Se pasa a `usePolling`/effect sin riesgo de loop |
| `tesoreria/remesas/_hooks/useRemesas.tsx:128` | `useEffect` (mount) | `loadData` | `loadData` → `useCallback([t])`; effect deps `[loadData]` | función recreada cada render → estabilizar y añadir |

## Recuento de tipos de fix

- **add-dep directo** (la dep ya era estable): 6 → Expediente303Drawer, PreventiveCheckCard, autonomia, useMiEquipo, useAgentPolling, CalendarioTab
- **useCallback (estabilizar función + añadir)**: 9 → BOETab, useActualizaciones, backups, ErpImportReview, useRemesas, almacenes, reposicion, LotsPanel, WarehouseStockPanel
- **useMemo (estabilizar objeto + añadir)**: 1 → useAutomatizacionesCRUD (TRIGGER_LABELS)
- **eslint-disable justificado**: 0 (no fue necesario en ningún caso)

Imports añadidos (`useCallback`/`useMemo`) sólo donde faltaban; cero cambios de
comportamiento observable.
