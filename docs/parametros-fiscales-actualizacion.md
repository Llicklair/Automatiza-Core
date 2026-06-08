# Parámetros fiscales y su actualización cuando la AEAT cambia

Objetivo: que el sistema refleje los cambios de la AEAT/BOE **sin valores
caducados**, pero de forma **segura** (un tipo mal scrapeado = impuestos mal
calculados = responsabilidad legal). Por eso la regla es:

> **Las fechas y los avisos se actualizan solos; los TIPOS/IMPORTES se versionan
> por año y se actualizan con revisión humana, avisados por el detector de BOE.**

---

## 1. Lo que YA se actualiza solo

- **Calendario de vencimientos AEAT** — `integrations/boe_scraper.get_proximos_vencimientos`
  (lo usa `compliance.check_fiscal_deadlines`). Es la fuente viva: no hay fechas
  hardcodeadas y hay un safeguard CONT.0 que, si no carga, remite a la Sede en vez
  de inventar fechas.
- **Novedades del BOE** — `compliance.check_boe_news` (scraper de la sección
  fiscal). Detecta cambios normativos relevantes para PYMEs.

**Recomendado (pendiente):** una tarea programada que ejecute `check_boe_news`
+ una comprobación de "parámetros que cambian de año" y, si detecta algo, genere
un **aviso** (services/alerts) para que alguien revise y actualice el config.
Eso es "auto-actualización" segura: el sistema vigila y avisa; el humano confirma.

## 2. Parámetros versionados por año (revisar cada enero / cuando el BOE cambie)

| Parámetro | Dónde vive | Valor actual | Fuente |
|---|---|---|---|
| Tipos IVA (21/10/4) | `compliance` _CONTEXTO_NORMATIVO + cálculos 303/390 | 21 / 10 / 4 % | Ley IVA |
| Base máxima cotización mensual | `hr/queries.py` `_BASE_MAX_COTIZACION_MENSUAL` | 2024: 4.720,50 · 2025: 4.909,50 · 2026: 5.101,20 | Orden anual cotización (BOE) |
| MEI trabajador | `hr/queries.py` `_MEI_TRABAJADOR` | 2025: 0,13 % · 2026: 0,15 % | RD-ley 2/2023 |
| Cuota de solidaridad (tramos) | `hr/queries.py` `_CUOTA_SOLIDARIDAD_TIPOS` | 2025 / 2026 cargados | RD-ley 2/2023 |
| Tipos SS resto (CC 4,70 / desempleo 1,55 / FP 0,10) | `hr/queries.py` | vigentes | Orden anual |
| Retención alquiler (115) | `reports/modelos_aeat` `TIPO_RETENCION_115` | 19 % | Reglamento IRPF |
| Retención profesionales | `compliance` _CONTEXTO_NORMATIVO | 15 % (7 % primeros años) | Reglamento IRPF |
| Umbral 347 | `reports/modelos_aeat` `MODELO_347_THRESHOLD` | 3.005,06 € | Reglamento |
| Escala/tramos IRPF retención | (pendiente — ver IRPF) | — | Reglamento IRPF |

**Patrón ya usado** (replicarlo para todo lo nuevo): diccionario keyed por año +
función `valor(year)` que cae al año conocido más reciente si falta. Así, añadir
el valor de un año nuevo es **una línea** y todo el sistema (nómina, modelos,
deadlines) lo coge automáticamente.

## 3. Por qué NO scrapeamos los tipos automáticamente

Cambiar un tipo de IRPF/SS desde un scraper sin revisión humana es peligroso: un
falso positivo cambia el cálculo de nóminas e impuestos de todos los tenants, con
responsabilidad para la empresa (art. 99 LIRPF; art. de la LGSS para cotización).
El BOE además publica con matices (fechas de efecto, regímenes, excepciones) que
un scraper no interpreta bien. Por eso: **detectar y avisar (automático) →
actualizar el config (humano)**.

## 4. Checklist de revisión anual (enero)
- [ ] Orden de cotización del año (base máxima, MEI, tipos) → `hr/queries.py`.
- [ ] Cuota de solidaridad del año → `_CUOTA_SOLIDARIDAD_TIPOS`.
- [ ] Tipos IVA y retenciones (alquiler, profesionales) si han cambiado.
- [ ] Umbrales (347) y novedades de modelos.
- [ ] Escala IRPF si se implementa el cálculo oficial de retención.
