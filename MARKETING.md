# AutomatizaPyme — Mensajes de marketing canónicos

> Frases vinculantes para landing, EULA, ads y comunicación. Cambiarlas
> requiere coherencia con `ARCHITECTURE.md §16` y `docs/telemetry-data-policy.md`.

## Promesa central

> **Tu base de datos vive en tu equipo. Nunca enviamos tus datos de
> negocio sin tu permiso explícito.**

(A.9bis del debate consensuado. Define el moat: local-first verificable.)

## Definición de "datos de negocio"

Datos protegidos por la promesa anterior:

- Facturas (números, importes, líneas).
- Clientes / proveedores (NIFs, IBANs, nombres, direcciones).
- Nóminas, retenciones, contabilidad.
- Contenido de prompts y outputs de agentes IA.
- Documentos subidos por el usuario.

Datos técnicos que el usuario puede autorizar a enviar (opt-in):

- Versión del software, sistema operativo, errores anonimizados.
- Identificador pseudonimizado del tenant (hash con salt rotada 90d).
- Métricas de uso agregadas (sin identificadores re-identificables).

## Tiers de pricing

| Tier | Precio (sin IVA) | Descripción |
|---|---|---|
| Solo | 39€/mes | Facturación + VeriFactu + 1 empresa |
| Pro | 65€/mes | + banking + contabilidad + IA marketing/RRHH |
| Gestoría | 159€/mes | Multi-empresa hasta 25 + canal directo |

Trial 14 días sin tarjeta. Anual con descuento equivalente a 2 meses.
Soft cap 500 interacciones/mes en Pro con overage 0,05€ + IVA por interacción
adicional (banner explícito, nunca bloquea fiscal). Cron jobs no cuentan
para soft cap pero tienen cap propio (200/mes Pro, 200×N hasta 2000 Gestoría).

## Posicionamiento competitivo

Frente a Holded (12€), Anfix (9€), Quipu (13€): AutomatizaPyme cobra
3-4× porque combina:

1. **Privacidad real** — local-first, no SaaS cloud puro.
2. **Cumplimiento Verifactu nativo** — cadena hash + QR + presentación
   telemática vía Plataforma Colaboradores Sociales AEAT.
3. **IA agentes con human-in-the-loop documentado** — escenario A AI Act
   con `autonomy_policy` configurable.
4. **Sustitución de gestoría** — modelos 303, 130, 347, 390, 111, 190
   generables + presentación telemática desatendida (con apoderamiento
   REGAP del cliente).

## SLA tier

| Tier | SLA |
|---|---|
| Solo | Best effort |
| Pro | L1 48h hábiles |
| Gestoría | L1 4h hábiles + canal directo email fundador |

## Compromisos sobre IA

AutomatizaPyme es **proveedor del sistema de IA integrado** bajo
Reglamento UE 2024/1689 (AI Act). Cumplimiento documentado en
`docs/ai_act_scoping.md`. En v1 MVP:

- El agente `recruitment` **no puntúa candidatos** (Escenario A AI Act).
- El agente `hr` genera **plantillas formales sin motivar despidos**
  (structure-only).
- Todos los agentes muestran banner Art. 50 de transparencia ("estás
  interactuando con un sistema de IA").
- Footer en cada respuesta del agente con proveedor + modelo + tokens
  para trazabilidad B2B.

## Plataforma soportada en v1

Windows 10 22H2+ y Windows 11. macOS confirmado para Q4-2026
(landing público). Linux solo enterprise con contrato (no precio listado).

## Punto de contacto privacidad

DPD: **privacidad@automatizapyme.com**. Plazo respuesta: 30 días
naturales (RGPD Art. 12.3).
