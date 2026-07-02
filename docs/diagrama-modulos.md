# Diagrama de módulos y funcionalidades — AutomatizaCore

> Mapa de la app tal como la ves (sidebar real) + la capa de IA que la mueve.
> Los diagramas son Mermaid: se renderizan en el preview de VS Code y en GitHub.
>
> 🔎 **Versión detallada, interactiva y contrastada con el código:** abre [`diagrama-proyecto/index.html`](diagrama-proyecto/index.html) · referencia en texto greppable: [`diagrama-proyecto/MAPA-PROYECTO.md`](diagrama-proyecto/MAPA-PROYECTO.md).

---

## 1. Arquitectura por capas (cómo está construido)

```mermaid
flowchart TB
    Desktop["🖥️ App de escritorio · Electron<br/>autogestiona PostgreSQL + Python + JRE"]
    FE["Frontend · Next.js 16 / React 19<br/>109 páginas · todo pasa por lib/api"]
    API["API · FastAPI<br/>65 rutas · 474 endpoints · JWT · multi-tenant estricto"]

    subgraph IA["🧠 Capa de IA"]
        Coord["Coordinador · agents/orchestrator<br/>Lenguaje natural → Clasifica → Planifica → Despacha"]
        Agents["14 Agentes de dominio<br/>LangGraph"]
        Gate["Gate de Autonomía<br/>AUTO · CONFIRM · MANUAL"]
    end

    Orq["Orquestador · services/workflow<br/>workflows programados + scheduler"]
    Svc["Services<br/>lógica de negocio por dominio"]
    DB[("PostgreSQL + pgvector")]

    Desktop --> FE --> API
    API --> Coord
    Coord --> Agents
    Agents --> Gate
    Agents --> Svc
    API --> Svc
    Orq --> Coord
    Svc --> DB
    Agents --> DB
```

**En una frase:** escribes en lenguaje natural → el **Coordinador** decide qué **agente** actúa → el **Gate de autonomía** decide si ejecuta, pide confirmación o solo sugiere → la acción real la hacen los **Services** contra **PostgreSQL**. El **Orquestador** repite todo esto en automatizaciones programadas.

---

## 2. Módulos y funcionalidades (lo que ves en la app)

```mermaid
mindmap
  root((AutomatizaCore))
    Inicio
      Primeros pasos
      Mi portal
      Mi equipo - empleados IA
      Automatizaciones - workflows
      Calendario y Bandeja
    Negocio
      Ventas
        Facturas - FacturaE / Verifactu
        Albaranes / Presupuestos / Pedidos
        Recurrentes / Servicios
      Compras
        Facturas / Pedidos / Proveedores
      Contactos
        Clientes / Portal cliente
      CRM
        Embudo de ventas / Actividades
        Calendario / Reservas / Reuniones
      RRHH
        Empleados / Nóminas
        Reclutamiento / Jornada / Gastos
      Inventario
        Productos / Stock / Lotes FEFO
        TPV / Escáner de almacén
      Proyectos
        Panel / Tareas
    Finanzas
      Tesorería
        Cuentas banca / Cashflow
        Pagos y cobros / Remesas
      Contabilidad
        Libro diario / Cuadro de cuentas
        P y G / Balance / Activos
        Asesorías
      Impuestos - Modelos AEAT
      Verifactu - Modo / AEAT / Firma
    Análisis
      Analítica
      Informes IA
      Marketing / Email Marketing
      Alertas
    Gobierno
      Compliance - consulta fiscal
      Auditoría - trazas
    Herramientas
      Documentos / Escáner
      Plantillas / Correos
      Integraciones
      Configuración - API keys / Autonomía / Backups
```

---

## 3. Los 14 agentes de IA (el "cerebro")

Cada agente vive en `backend/app/agents/<dominio>/` y su único contrato es ejecutar tareas de su dominio. El **Coordinador** los enruta; el **Gate de autonomía** controla qué pueden hacer solos.

| Agente | Qué hace | Autonomía por defecto |
|---|---|---|
| **Coordinador** (orchestrator) | Lenguaje natural → clasifica, planifica y despacha al agente adecuado | — |
| **billing** | Crea/emite facturas, FacturaE 3.2.2, Verifactu, numeración legal | `fiscal` = MANUAL (forzado) |
| **accounting** | Asientos, libro diario/mayor, cierre de periodo, Modelo 303, informes | CONFIRM |
| **banking** | Conciliación bancaria (import N43, auto-match) | banking_write = MANUAL |
| **crm** | Leads, embudo, actividades, agenda comercial | AUTO |
| **hr** | Nóminas, horarios, empleados | CONFIRM |
| **inventory** | Stock, lotes FEFO, reposición, ajustes | CONFIRM |
| **documents** | OCR/parse, clasifica, importa facturas de compra, indexa para RAG | CONFIRM |
| **compliance** | Consultas fiscales (RAG legal), calendario AEAT, BOE | AUTO (solo lectura); lo `fiscal` forzado a MANUAL |
| **marketing** | Posts, campañas, plan de contenidos, imágenes, redes (Zernio) | CONFIRM |
| **recruitment** | Puestos, candidatos, lectura de CV, pipeline | CONFIRM |
| **email** | Bandeja, enviar y responder correos (Gmail/Outlook/IMAP) | CONFIRM |
| **rag** | Búsqueda semántica y respuestas sobre tus documentos | AUTO |
| **excel** | Generación y análisis de hojas de cálculo | AUTO (no crítico) |

**Gate de autonomía** (`/configuracion/autonomia`): por cada dominio eliges **AUTO** (actúa solo), **CONFIRM** (prepara y espera tu clic) o **MANUAL** (solo sugiere). Lo fiscal está **forzado a MANUAL** por ley.

---

## 4. Cómo se conectan los módulos visibles con la capa de IA

```mermaid
flowchart LR
    subgraph UI["Lo que ves"]
        V[Ventas / Facturas]
        C[Contabilidad]
        T[Tesorería]
        I[Inventario]
        M[Marketing]
        D[Documentos / Escáner]
        Comp[Compliance / Impuestos]
        RH[RRHH]
    end
    subgraph AG["Agentes IA"]
        billing & accounting & banking & inventory & marketing & documents & compliance & hr
    end
    V --> billing
    C --> accounting
    T --> banking
    I --> inventory
    M --> marketing
    D --> documents
    Comp --> compliance
    RH --> hr
```

---

*Generado el 2026-06-30. Para el detalle de comportamiento exacto vs esperado de cada feature, ver [`mapa-features-comportamiento.md`](mapa-features-comportamiento.md).*
