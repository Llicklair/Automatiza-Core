# Cobertura del loop /forja — mapa de flujos

> ⚠️ HONESTIDAD DEL NÚMERO (leer esto): el % de abajo mide **AMPLITUD de primer contacto** (¿he
> visitado el barrio?), NO **profundidad de revisión** (¿he registrado cada casa?). No confundir.

## Dos métricas distintas

### 1) AMPLITUD — áreas tocadas ≥1 vez · **28/65 ≈ 43%** (sales_orders ya con 6 lentes)
Denominador = 65 route-areas. Una marca ✅ = "he barrido **1 flujo** de esta área con **1 lente**". El área
(p.ej. `accounting`) tiene MUCHOS flujos y funciones; tocar uno NO la revisa entera. Por eso 41% suena a
mucho con pocos turnos: es "primer contacto", barato.

### 2) PROFUNDIDAD — lo que de verdad falta (la métrica honesta)
El repo tiene ~**11.400 símbolos**, **33.500 edges**, ~**300 flujos** de ejecución finos. He examinado a
fondo ~**35-40 funciones** en ~26 áreas, cada una con **1 lente de las 6**. Estimación REAL:
- por flujo fino: ~30-40 de ~300 ≈ **~10-12%**
- por símbolo: ~40 de 11.400 ≈ **<0,5%**
- "completo" = área × flujo × **6 lentes** → denominador real ~65 × (flujos/área) × 6 = **miles de celdas**;
  cubiertas: **single digits %**.

**Conclusión honesta: el trabajo de revisión profunda está en torno al ~5-12%, no al 40%.** El 40% es la
barra de "he pisado el área", útil para no repetir, pero NO es "revisado". Tu sospecha es correcta.

## Pasada actual: **1** · lente: mixta (elegida por turno)
Una "pasada" = todas las áreas tocadas ≥1 vez. Al completarla → rotar lente y RESETEAR (ver abajo). Una
revisión seria de verdad = **6 pasadas** (las 6 lentes) + bajar de "área" a "flujo fino" dentro de cada una.

## RESET DEL MAPA  ·  `/clean forja map` / "resetea el mapa"
Cuando una pasada llega al 100% de amplitud (o cuando quieras forzar vuelta nueva):
1. Se **archiva** la pasada completada abajo (con la lente y fecha).
2. Todas las ✅/🔶 vuelven a ⬜.
3. Se **incrementa la pasada** y se fija la **siguiente lente** (1 correctitud → 2 seguridad → 3
   concurrencia → 4 errores → 5 test-gaps → 6 perf → vuelta a 1).
Trigger: el usuario dice `/clean forja map` o "resetea el mapa" → el orquestador hace lo anterior. (Auto al
llegar a 100% si el usuario lo deja correr.)

### Pasadas archivadas
- _(ninguna aún — pasada 1 en curso)_

---

## Áreas (pasada 1) — ✅ tocada · 🔶 parcial · ⬜ pendiente
✅ accounting · aeat_presentation · analytics · auth · banking · client_portal · clients · collections ·
crm · documents · hr_employees · hr_payrolls · import_bulk · integrations · invoices · messaging ·
modelos_aeat · onboarding_wizard · portal · pos · products · purchase_orders · quotes · recurring_invoices ·
treasury · email_marketing · marketing · **sales_orders ⭐(6 lentes — amplitud≈profundidad en este)**
🔶 verifactu_config · verify · hr_time · hr_expenses · albaranes · approvals · signing
⬜ admin · advisory · ai_employees · alerts · autonomy · backup_local · calendar · collections_(done) ·
generative_ui · hr · hr_documents · license · llm_usage · marketplace · metrics · notifications ·
onboarding_regap · presentacion_asistida · projects · recruitment · scanner · search ·
system · tasks · telemetry · templates · tenant · users · warehouses · workflows · erp
