# Frontend test suite (test:ci) — diagnóstico

Comando CI: `vitest run --coverage` (script `test:ci` en frontend/package.json)
Resultado: **FALLA** (exit code 1)

## Conteos
- Test Files: 1 failed | 18 passed (19 total)
- Tests: 5 failed | 166 passed (171 total) | 0 skipped
- Duración: ~16.3s

## Fichero que falla
`src/app/(dashboard)/inventario/stock/__tests__/MovementModal.test.tsx` (5/5 tests del fichero fallan)

## Causa raíz (común a los 5)
Faltan claves de traducción i18n en el namespace `inventario.movementModal.*` para el locale `es`.
`IntlError: MISSING_MESSAGE: Could not resolve ...`. Como next-intl devuelve la propia clave
en lugar del texto traducido, Testing Library no encuentra los elementos esperados (botones/labels/textos).

### Tests fallidos y causa concreta
1. **renders the stock_kind selector (Unidad / Caja)** — falta `inventario.movementModal.kind_unit` / `kind_box` / `stockKind`; no encuentra botón con name "Unidad".
2. **shows both unit and box counters in the description** — falta `inventario.movementModal.boxesShort`; no encuentra el texto "4 cajas".
3. **switches stock_kind to box when Caja is clicked** — falta `kind_box`; no encuentra botón con name "Caja".
4. **shows the reason selector with write-off motives for salida** — falta `inventario.movementModal.reason` (+ `reasonNone`, `reason_rotura`, `reason_merma`, `reason_robo`, `reason_caducado`); no encuentra label "Motivo".
5. **updates reason when an option is selected (write-off)** — misma causa: falta label "Motivo" / claves `reason_*`.

### Claves faltantes (locale es)
- inventario.movementModal.stockKind
- inventario.movementModal.kind_unit
- inventario.movementModal.kind_box
- inventario.movementModal.boxesShort
- inventario.movementModal.reason
- inventario.movementModal.reasonNone
- inventario.movementModal.reason_rotura
- inventario.movementModal.reason_merma
- inventario.movementModal.reason_robo
- inventario.movementModal.reason_caducado
