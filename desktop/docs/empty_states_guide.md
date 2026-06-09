# Catálogo de empty states productivos — UI.EMP

> **Versión 1.0 — 2026-05-14**. Diseño consensuado en Ronda 25 §50.

Un buen empty state responde en menos de 5 segundos a "¿qué es esto y qué
hago ahora?". Este catálogo establece la copy + icono + CTA primario
recomendado para los ~15 dominios principales de AutomatizaCore.

## Componentes disponibles

- **`@/components/ui/EmptyState`** (recomendado) — API tipada, ARIA
  `role="status"` + `aria-live="polite"`, sizes `sm | md`, action y
  secondaryAction con `{ label, href, onClick }`. Visual `bg-primary/10`.
- **`@/components/shared/EmptyState`** (legacy, soportado) — API de
  action como `ReactNode` libre. Visual `bg-muted` (sutil). Ya tiene
  ARIA. Migrar a `ui/EmptyState` cuando se toque la página.

## Reglas de copy

1. **Título** ≤ 6 palabras, específico al dominio: ❌ "No hay datos"
   ✅ "Aún no has emitido ninguna factura".
2. **Descripción** explica el porqué + qué hacer. Máximo 2 frases.
3. **CTA primario** un verbo + sustantivo, no "Crear" suelto: ✅ "Crear
   primera factura", "Importar desde Holded", "Conectar banco".
4. **CTA secundario** solo si hay alternativa real (importar / asistente
   IA). Si no, omitir.
5. Evitar emojis y signos de exclamación. Tono profesional.

## Catálogo por dominio

| Dominio | Icono Lucide | Título | Descripción | CTA primario | CTA secundario |
|---|---|---|---|---|---|
| Facturas emitidas | `FileText` | "Aún no has emitido ninguna factura" | "Genera tu primera para empezar a cobrar. El agente puede crearla a partir de un albarán o de la conversación." | Crear primera factura → `/ventas/facturas/nueva` | Importar desde Holded → `/configuracion/integraciones` |
| Facturas recibidas | `ShoppingCart` | "Sin facturas registradas todavía" | "Sube un PDF y el escáner extrae los datos. Reconciliaremos automáticamente contra tus movimientos bancarios." | Subir factura → `/escaner` | — |
| Clientes | `Users2` | "Tu directorio está vacío" | "Da de alta tu primer cliente o impórtalos en masa. La IA los detecta automáticamente al escanear facturas recibidas." | Añadir cliente → `/clientes/nuevo` | Importar CSV → `/configuracion/integraciones` |
| Productos / Catálogo | `Package` | "Catálogo sin productos" | "Define tus productos o servicios para acelerar la emisión de facturas." | Crear producto → `/catalogo/nuevo` | — |
| Empleados | `Users2` | "No hay empleados registrados" | "Añade tu plantilla para gestionar nóminas, ausencias y partes horarios." | Añadir empleado → `/rrhh/empleados/nuevo` | Importar CSV → `/configuracion/integraciones` |
| Banca · movimientos | `Landmark` | "Sin movimientos bancarios" | "Conecta tu banco via N43 para que el agente reconcilie automáticamente con tus facturas." | Conectar banco → `/configuracion/integraciones` | Subir N43 manual → `/banca/import` |
| Aprobaciones pendientes | `CheckCircle2` | "Nada pendiente de aprobar" | "Cuando el agente prepare acciones que necesiten tu validación, aparecerán aquí." | Ver bandeja → `/bandeja` | — |
| Automatizaciones | `Zap` | "Sin automatizaciones activas" | "Pídele al agente que programe una tarea (\"factura recurrente cada 1 de mes\") y la verás aquí." | Hablar con el agente → `/mi-equipo` | Ver plantillas → `/automatizaciones/plantillas` |
| Documentos | `FileText` | "Tu carpeta de documentos está vacía" | "Sube contratos, modelos AEAT o cualquier PDF para que la IA los indexe y los consulte." | Subir documento → `/documentos/upload` | — |
| Asientos contables | `BookOpen` | "Aún no hay asientos contables" | "Los asientos se generan automáticamente al emitir facturas o registrar movimientos. También puedes crearlos a mano." | Asiento manual → `/contabilidad/libro-diario/nuevo` | — |
| Proyectos | `Briefcase` | "No tienes proyectos activos" | "Agrupa tareas, presupuestos y facturas por proyecto para rentabilizar mejor cada trabajo." | Crear proyecto → `/proyectos/nuevo` | — |
| Actividades CRM | `Activity` | "Sin actividades programadas" | "Llamadas, reuniones, follow-ups. Crea una o deja que el agente las añada por ti." | Nueva actividad → `/crm/actividades/nueva` | — |
| Presupuestos | `FileSpreadsheet` | "Ningún presupuesto en curso" | "Crea presupuestos con la IA. Cuando el cliente acepte, se convierten en factura con un clic." | Crear presupuesto → `/ventas/presupuestos/nuevo` | — |
| Oportunidades | `TrendingUp` | "Tu pipeline está vacío" | "Registra oportunidades para hacer seguimiento de ventas en curso por etapa." | Nueva oportunidad → `/crm/embudo-de-ventas/nueva` | — |
| Plantillas | `LayoutTemplate` | "Sin plantillas guardadas" | "Crea plantillas reutilizables para facturas, contratos o emails repetidos." | Nueva plantilla → `/plantillas/nueva` | — |
| Alertas / Notificaciones | `Bell` | "Sin notificaciones" | "Cuando el agente complete tareas o necesite tu atención, aparecerán aquí." | — | — |

## Ejemplo de uso (ui/EmptyState)

```tsx
import { FileText } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";

<EmptyState
    icon={FileText}
    title="Aún no has emitido ninguna factura"
    description="Genera tu primera para empezar a cobrar. El agente puede crearla a partir de un albarán o de la conversación."
    action={{ label: "Crear primera factura", href: "/ventas/facturas/nueva" }}
    secondaryAction={{ label: "Importar desde Holded", href: "/configuracion/integraciones" }}
/>
```

## Migración de las páginas existentes

1. Si la página usa `@/components/shared/EmptyState` y la copy ya
   coincide con el catálogo, dejarlo — funciona y tiene ARIA.
2. Si la copy es genérica ("No hay datos", "Empty list"), sustituir por
   `ui/EmptyState` con la copy del catálogo arriba.
3. Para tablas con filtros (búsqueda activa sin resultados), no usar
   este componente — mostrar "No coincide con tu búsqueda" + botón
   "Limpiar filtros". Eso NO es un empty state productivo, es un null
   state de búsqueda.

## Próximas iteraciones

- Variante `ai-suggestion`: cuando el agente puede generar el primer
  registro con un solo clic. Botón "Pedírselo al agente" con icono `Bot`.
- A/B test de copy ES vs EU/CA/GA (I18N.UI).
