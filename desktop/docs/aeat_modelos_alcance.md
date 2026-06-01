# Modelos AEAT — alcance MVP y roadmap (AEAT.4)

> Copy revisado por abogado fiscalista (decisión humana 13). Esta página informa al cliente de **qué modelos genera AutomatizaPyme y cuáles requieren validación adicional o asesor fiscal externo**.

## §1 Modelos generados y presentables en MVP v1

| Modelo | Periodicidad | Generación | Presentación telemática |
|---|---|---|---|
| **303** — IVA trimestral | Trimestral | ✅ | ✅ |
| **390** — IVA anual | Anual | ✅ | ✅ |
| **130** — IRPF fraccionado (estimación directa) | Trimestral | ✅ | ✅ |
| **347** — Operaciones con terceros >3.005,06€ | Anual | ✅ | ✅ |
| **111** — Retenciones IRPF | Trimestral | ✅ | ✅ |
| **190** — Resumen anual retenciones IRPF | Anual | ✅ | ✅ |

Generación = AutomatizaPyme produce el borrador con los datos agregados desde tu BD.
Presentación telemática = AutomatizaPyme envía el modelo a la AEAT vía Plataforma Colaboradores Sociales con cert de representación propio y apoderamiento REGAP del cliente, **siempre tras aprobación humana firmada** (Modelo `FiscalApprovalLog`).

## §2 Modelos en roadmap (v1.1, Q4-2026)

| Modelo | Por qué no en MVP |
|---|---|
| **131** — IRPF fraccionado (módulos) | Requiere parametrización por epígrafe IAE + cálculo de módulos. Menor demanda en ICP autónomo profesional. |
| **200** — Impuesto sobre Sociedades | Complejidad alta (balance, ajustes fiscales, deducciones). Casi siempre lo prepara un asesor fiscal. |

Mientras tanto: AutomatizaPyme genera el **PDF prellenado** del 131 y 200 que tu asesor puede revisar y presentar manualmente desde la sede AEAT. La presentación asistida (deep-link a sede AEAT con XML pre-rellenado) está disponible para estos dos modelos.

## §3 Modelos NO cubiertos por AutomatizaPyme

Los siguientes modelos AEAT NO son objetivo del producto y NO se generan ni se prevé hacerlo en el roadmap v1.x:

* **100** — IRPF anual del autónomo (lo presenta el propio contribuyente con su gestor habitual).
* **210** — IRNR (no residentes).
* **303 régimen especial** del recargo de equivalencia (TODO v1.1 si entra cliente con tienda minorista).
* **036/037** — Alta censal (trámite previo a usar AutomatizaPyme; el cliente lo hace al darse de alta como autónomo o constituir la SL).
* **720** — Declaración de bienes en el extranjero (excepcional, no es flujo automático).

## §4 Limitaciones declaradas al cliente

> **Importante**: AutomatizaPyme automatiza la **generación y presentación telemática** de los modelos listados en §1 a partir de los datos que la propia plataforma gestiona (facturas emitidas/recibidas, nóminas). La validez fiscal del modelo depende de la corrección de esos datos.
>
> El cliente es **deployer del sistema de IA** bajo AI Act y **contribuyente** ante AEAT. La responsabilidad última de la declaración recae en el contribuyente.
>
> AutomatizaPyme proporciona el **canal de presentación legal** (Plataforma Colaboradores Sociales) con cert de representación propio, **previo apoderamiento REGAP del cliente**, y exige **aprobación humana firmada** (texto canónico tipeado + IP + payload hash) antes de cada presentación.

## §5 Recomendación para casos complejos

Para los siguientes escenarios, AutomatizaPyme **recomienda validación adicional por asesor fiscal**:

* Cierre del ejercicio fiscal anual.
* Operaciones intracomunitarias frecuentes.
* Regímenes especiales de IVA (caja, agencia de viajes, recargo de equivalencia).
* Empresa con >25 empleados o con activos en varios territorios fiscales.
* Cambios de régimen fiscal (alta en módulos, baja, etc.).
* Inspección o requerimiento de la AEAT.

Tu tier Gestoría incluye canal directo con el fundador para coordinar estos casos con tu asesor fiscal externo.

---

**Versión copy**: 1.0 — 2026-05-14
**Pendiente**: validación por abogado fiscalista (decisión humana 13, ~500€).
