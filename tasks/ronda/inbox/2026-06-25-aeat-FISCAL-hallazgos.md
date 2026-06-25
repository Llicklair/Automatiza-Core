# Inbox /forja — hallazgos FISCALES en services/aeat (2026-06-25, barrido #9)

El loop arregló el crash de `_round2(None)` en el 303 (PR #51, sin cambiar cálculos). Estos
**cambian el resultado declarado** → revisión humana obligatoria antes de tocar:

## ⚠️ ALTA — cambia la autoliquidación
2. **`casillas_303.py:174-183` la casilla 27 incluye el recargo de equivalencia (c18/c21/c24)**
   [alta]. Según instrucciones oficiales del Modelo 303 (BOE HFP/1124/2022), c27 = c03+c06+c09+
   c11+c13 SOLO (régimen general); el recargo tiene su propio subtotal y NO va a c27. Verificado:
   tenant en recargo 5,2% base 1.000€ declara c27=52€ cuando debería ser 0€. **Cambia el resultado
   de la liquidación → confirma contra la norma y revísalo tú antes de tocar.** (Fix candidato:
   excluir c18/c21/c24 de la suma de c27.)

## Media
3. **`casillas_390.py:38-39` doble redondeo en `_sum`** [media]. Redondea cada fila y luego el
   total → demostrado 3×0,005 da 0,03 en vez de 0,02. Acumulado descuadra el cruce 303-vs-390.
   Fix objetivo: sumar valores brutos y `round2` solo al total (como hace el 303). Cambia valores
   declarados (céntimos) → a tu criterio, pero es corrección clara.

## Nota contrato UI/backend (no aritmético)
- `casillas_303.py:226` c45 (total a deducir) = c29+c37; la c31 (cuota bienes de inversión,
  `editable=True`, default 0) nunca se suma a c45 en backend. Si el usuario edita c31 en el front
  y el front no recalcula c45, la declaración queda con c45 subestimado. Revisar contrato front/back.

## Follow-up tests (sugerido por el finder)
- Tests: tenant con recargo de equivalencia; `_round2(None)`; cruce 303-vs-390 (suma de 4 trimestres = 390 anual).
