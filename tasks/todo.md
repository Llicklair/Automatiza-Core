# Limpieza de menús e interfaz — sidebar

Fecha: 2026-05-04
Archivo central: `frontend/src/components/layout/nav-config.ts`

## Contexto

El sidebar tiene varios labels duplicados y páginas reales que no aparecen. Las
páginas `/tareas`, `/actividades`, `/aprobaciones` no son huérfanas: son
redirects intencionales hacia `/mi-equipo` y `/bandeja` (URLs legacy). No se
tocan.

## Cambios propuestos

### 1. Renombrar item top "Tareas" → "Mi equipo"
- **Por qué**: el label dice "Tareas" pero `href = /mi-equipo`. Engaña y choca
  con `Proyectos › Tareas`.
- **Cómo**: en `nav-config.ts:30`, cambiar `label: "Tareas"` por
  `label: "Mi equipo"`. Mantener icono `Sparkles` o cambiar a `Users2`.
- **Riesgo**: ninguno. Solo afecta al label visible y `ROUTE_LABELS`.

### 2. Diferenciar "Calendario" duplicado
- **Por qué**: top-level `/calendario` y `CRM › Calendario` (`/crm/calendario`)
  comparten label exacto.
- **Cómo**: renombrar el de CRM a "Calendario CRM" o "Eventos comerciales"
  (`nav-config.ts:68`). El del top queda como "Calendario".
- **Riesgo**: ninguno.

### 3. Aplanar la sección "Integraciones"
- **Por qué**: la sección padre se llama "Integraciones" y tiene un hijo
  "Conexiones" (`/integraciones`) y otro "Mensajería"
  (`/configuracion/integraciones`). Confuso.
- **Cómo**:
  - Convertir "Integraciones" en item plano apuntando a `/integraciones`
    (sin subItems).
  - Mover "Mensajería" → `/configuracion/integraciones` dentro del submenú
    "Configuración" como una entrada más.
- **Riesgo**: ninguno. Las URLs no cambian.

### 4. Añadir páginas reales que faltan en el sidebar
- **`/correos`** → bajo "Herramientas" como "Correos" (icono `Mail`).
- **`/excel`** → bajo "Herramientas" como "Importar Excel"
  (icono `FileSpreadsheet`).
- **Riesgo**: ninguno, son enlaces nuevos.

### 5. (OPCIONAL — pendiente de tu visto bueno) hubs de sección sin enlace
Páginas raíz que existen pero no se exponen en el sidebar:
`/ventas`, `/compras`, `/crm`, `/contabilidad`, `/rrhh`, `/tesoreria`,
`/inventario`, `/configuracion`. Antes de tocar nada, hay que confirmar si
contienen un panel resumen útil o si solo son scaffolding. Si son útiles,
añadirlas como primera subentrada "Resumen" en cada submenú padre.

### 6. (NO TOCAR salvo que pidas) etiquetas vs URL
- `Tesorería › Cuentas` → `/banca`
- `Inventario › Productos` → `/catalogo`
Son URLs legacy con label correcto. No rompe nada; renombrar la URL implicaría
mover páginas y migrar imports. Dejarlo.

## Verificación post-cambio

1. `tsc --noEmit` en `frontend/`.
2. Abrir el sidebar en cada sección y confirmar que:
   - "Mi equipo" aparece en lugar de "Tareas".
   - No hay dos "Calendario" iguales.
   - "Integraciones" es un item plano y "Mensajería" vive en Configuración.
   - "Correos" e "Importar Excel" aparecen en Herramientas.
3. `gitnexus_detect_changes()` para confirmar que solo cambia
   `nav-config.ts` (+ posibles imports de iconos nuevos).

## Estado

- [ ] 1. Renombrar "Tareas" → "Mi equipo"
- [ ] 2. Diferenciar "Calendario" CRM
- [ ] 3. Aplanar "Integraciones"
- [ ] 4. Añadir "Correos" y "Excel" en Herramientas
- [ ] 5. Decidir sobre hubs de sección (requiere confirmación)
- [ ] 6. Verificación tsc + sidebar visual
