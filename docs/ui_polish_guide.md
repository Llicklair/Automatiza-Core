# UI polish guide — patrones canónicos (UI.POL)

> **Versión 1.0 — 2026-05-15**. Cierra el bloque visual del MVP junto
> con UI.EMP (empty states) y UI.DEN (densidad).

Esta guía consolida los patrones de UI que las páginas del dashboard
DEBEN seguir. Su objetivo es eliminar inconsistencias entre dominios
(facturas, clientes, banca, RRHH, etc.) que el usuario percibe como
"productos diferentes" dentro de la misma app.

## §1 Encabezado de página

Usa siempre [`<PageHeader />`](../frontend/src/components/ui/PageHeader.tsx)
en lugar de h1 + p ad-hoc. Garantiza:

- Tipografía consistente (`text-2xl font-semibold tracking-tight`).
- Un único h1 por página (a11y: SR detecta el landmark de página).
- Espacio inferior estándar (`mb-6`) — no compongas con `mt-` extra.

```tsx
import { PageHeader } from "@/components/ui/PageHeader";

<PageHeader
    title="Facturas emitidas"
    description="Listado completo de facturas Q1 2026."
    actions={<Button>Nueva factura</Button>}
/>
```

## §2 Botones y CTAs

Jerarquía visual estándar:

| Variante | Uso | Clase Tailwind base |
|---|---|---|
| **Primary** | Acción principal de la página (1 por sección) | `bg-primary text-foreground hover:bg-primary/90` |
| **Secondary** | Acciones útiles pero no críticas | `bg-background border border-border hover:border-primary` |
| **Ghost** | Acciones contextuales (ej.: "Limpiar filtros") | `text-muted-foreground hover:text-foreground` |
| **Destructive** | Eliminar, descartar | `bg-red-600 text-foreground hover:bg-red-500` |

**Sizing**:
- Default: `px-4 py-2 text-sm` con `rounded-md`.
- Compact (tablas, toolbars): `px-2.5 py-1 text-xs`.
- Hero (CTAs grandes en empty states / onboarding): `px-5 py-2.5 text-sm`.

Evitar tamaños custom. Si el caso pide otro, abrir la discusión antes
de añadirlo a la guía.

## §3 Espaciado y layout

| Token | Valor | Uso |
|---|---|---|
| `p-6` | 24px | Padding raíz de página dashboard |
| `mb-6` | 24px | Separación tras `<PageHeader />` |
| `space-y-4` | 16px | Separación vertical entre secciones |
| `gap-3` | 12px | Separación en grids 2-3 cols |
| `gap-2` | 8px | Separación en grupos de acciones (botones) |

Para páginas que respetan densidad (UI.DEN): usar las clases
`.density-row`, `.density-table-cell`, `.density-card` definidas en
`globals.css` en lugar de padding fijo cuando sea relevante al usuario
de gestoría.

## §4 Empty states

Usar `@/components/ui/EmptyState` (UI.EMP). Catálogo de copy por dominio
en [`empty_states_guide.md`](./empty_states_guide.md). Reglas:

- No usar el componente para "no hay resultados de búsqueda" — eso es
  un null-state distinto (texto + botón "Limpiar filtros").
- La frase y el icono deben venir del catálogo, no inventarse por
  página.

## §5 Loading states

Tres patrones según el contexto:

| Contexto | Patrón |
|---|---|
| Página completa cargando | `<Loader2 className="w-4 h-4 animate-spin" />` + "Cargando…" en padding p-8 |
| Tabla / lista | Skeleton de filas (3-5 placeholders animados) |
| Botón disparando acción | `disabled` + spinner inline + texto "Procesando…" |

Evitar pantallas en blanco. Si la query tarda > 200ms, mostrar algo.

## §6 Modales / dialogs

Usar `@radix-ui/react-dialog` (ya en `package.json`). Estructura mínima:

- `role="dialog"` + `aria-modal="true"` + `aria-labelledby` apuntando al
  título.
- Botón de cierre con `aria-label="Cerrar"` en la esquina superior derecha.
- Acciones primaria/secundaria en footer (derecha alineadas).
- Foco se mueve al modal al abrir; trap del Tab dentro; Escape cierra.

Ejemplo conformante: `components/ai/CostModal.tsx` (UI.COST).

## §7 Iconografía

- Una sola librería: **lucide-react**. No mezclar con FontAwesome ni
  HeroIcons.
- Iconos decorativos: `aria-hidden="true"`. Iconos que sustituyen texto:
  `aria-label="..."` (botones-icono).
- Tamaños canónicos: `w-3` (12px) en badges, `w-3.5` (14px) en botones
  compactos, `w-4` (16px) default, `w-5` (20px) destacados, `w-6+`
  hero/empty states.

## §8 Colores semánticos

| Significado | Tailwind | HSL var | Cuándo usar |
|---|---|---|---|
| Éxito | `emerald-500` o `text-success` | `--success` | Confirmaciones, "completado" |
| Advertencia | `amber-500` o `text-warning` | `--warning` | Acciones reversibles arriesgadas |
| Error | `red-500` o `text-destructive` | `--destructive` | Fallos, rechazos |
| Info | `indigo-500` o `text-info` | `--info` | Mensajes informativos neutros |
| Primary | `text-primary` | `--primary` | Acentos de marca, CTAs |

No usar colores raw (`text-blue-500`) excepto en charts dedicados con
paleta consensuada.

## §9 Tablas

- Header sticky cuando el contenido scrollea (`sticky top-0 bg-card`).
- Filas hover state sutil (`hover:bg-accent/40`).
- Acciones por fila como botones-icono al final, con `aria-label`.
- Si la tabla tiene > 50 filas, virtualizar (futuro: UI.VIRT, post-MVP).

## §10 Antipatrones a evitar

- ❌ `text-2xl font-bold` ad-hoc para titles → usa `PageHeader`.
- ❌ Colores hex hardcodeados → usa tokens de `--primary/--muted/...`.
- ❌ Padding inline `style={{ padding: "12px" }}` → usa Tailwind.
- ❌ Spinner construido a mano con SVG raw → usa `Loader2` de lucide.
- ❌ `console.log` en producción → usa `useToastStore` para feedback.
- ❌ Componente que abre/cierra modal con state local — usa Radix Dialog
  o el store `useConfirmStore` para confirmaciones.

## §11 Aplicación incremental

La rotación de páginas para conformarlas a esta guía se hace en PR
sucesivos, no big-bang. Cada PR de feature debe:
1. Si añade UI: cumplir la guía.
2. Si toca una página existente: aprovechar para alinearla al canon
   antes de extender.

Páginas ya conformes a 2026-05-15:
- `/bienvenida` (UI.ONB)
- `/bienvenida/simulacion-303` (UI.SIM)
- `/configuracion/regap` (PRES.REG)
- `/configuracion/autonomia` (SEC.AUT)
- `/configuracion/preferencias` (UI.DEN)
- `/configuracion/verifactu` (FAC.MODE)

Páginas con `<PageHeader />` pendientes de adopción se identifican con
grep de `text-2xl font-semibold` fuera del componente — el rollout es
mecánico.
