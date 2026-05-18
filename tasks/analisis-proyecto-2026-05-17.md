# Análisis Profundo — AutomatizaPyme

**Fecha**: 2026-05-17
**Objetivo**: Auditoría honesta del estado real del proyecto para decisiones de producto y negocio.

---

## TL;DR

AutomatizaPyme es un **ERP español completo con IA agentica e instalación local**, construido en solitario en ~4 meses, con **67.350 líneas de Python backend** y un frontend Next.js con **80+ páginas**. La amplitud funcional rivaliza con productos consolidados (Holded, Sage, A3) en muchas áreas, e incluye diferenciadores que **ninguno de ellos tiene**: empleados IA personalizables, sandbox generativo de UI, RAG con pipeline propio y workflows con NLP.

El proyecto **no es un prototipo**, es una plataforma productiva. La barrera para llegar a clientes pagantes no es técnica — es comercial. El mayor riesgo estructural es la dependencia de LLMs cloud, que rompe la promesa "local-first" pura en un nicho de clientes (ciberseguridad/legal) donde precisamente eso vendería.

---

## 1. Volumen real

| Métrica | Valor |
|---|---|
| LOC backend Python | 67.350 |
| LOC frontend TS/TSX | ~50.000 (estimación, 1.156 sólo en `lib/api`) |
| Agentes de dominio | 13 |
| Servicios backend | 25 módulos |
| Rutas API (`/api/v1/routes/`) | 48+ |
| Modelos de BD | 23 |
| Migraciones Alembic | 30+ |
| Páginas frontend (`/dashboard/*`) | 80+ |
| Módulos API frontend (`lib/api/`) | 40+ |
| Tests backend (pytest) | 113 |
| Tests E2E (Playwright) | scaffolding + 3 smoke (commit 271268e) |
| Tests frontend (Vitest + a11y) | configurados |

Esto **no es un proyecto pequeño**. La superficie funcional es la de un equipo de 3–5 personas durante 12–18 meses en una startup productiva.

---

## 2. Capacidades operativas (qué funciona hoy)

### 2.1 ERP funcional completo

| Área | Estado | Detalle |
|---|---|---|
| Facturación | ✅ Producción | Invoices, lines, series, presupuestos, recurrentes, conversión cotización→factura |
| Ventas | ✅ Producción | Sales orders, albaranes (con reversa de stock — commit 7a287a3) |
| Compras | ✅ Producción | Purchase orders, facturas de compra, proveedores |
| POS | ✅ Producción | Punto de venta integrado (modelo `pos.py`, rutas `pos.py`) |
| Inventario | ✅ Producción | Stock items + extensiones (migración 0024) |
| Clientes/CRM | ✅ Producción | Oportunidades, actividades, pipeline, portal de clientes |
| Contabilidad | ✅ Producción | Libro diario, P&G, balance, cuadro de cuentas, activos fijos |
| Banca | ✅ Producción | Movimientos, saldos, conciliación, resumen financiero |
| Tesorería | 🟡 Beta | Cashflow, pagos/cobros, remesas |
| HR | ✅ Producción | Empleados, nóminas (cálculo + aprobación), contratos |
| Reclutamiento | ✅ Producción | Posiciones, CVs, análisis IA con scoring |
| Calendar | ✅ Producción | Eventos, citas, reservas |
| Proyectos | ✅ Producción | Projects + members + tasks |

### 2.2 IA diferenciadora (lo que nadie más tiene)

| Capacidad | Estado | Detalle |
|---|---|---|
| **Empleados IA personalizables** | ✅ Producción | Crear agentes con nombre/rol/dominio/system_prompt + 45 skills del catálogo. Tabla `ai_employees` + `agent_skills`. Budget guard por empleado. |
| **Sandbox generativo de UI** | ✅ Producción | Genera interfaces HTML/CSS desde lenguaje natural (`/sandbox`, modelo `generative_ui`) |
| **Workflows con NLP** | ✅ Producción | Parser de lenguaje natural a workflow (`services/workflow/_nlp.py`), scheduler, recovery, condiciones |
| **Pipeline RAG propio** | ✅ Producción | OpenDataLoader (Java) → clasificación regex (90% sin LLM) → smart chunker → BAAI/bge-m3 → pgvector. **Esto es ingeniería de nivel producto, no PoC.** |
| **HR Documents generados por IA** | ✅ Producción | Contratos, cartas, certificados con plantillas |
| **CV Analysis con scoring** | ✅ Producción | Scoring de compatibilidad candidato↔posición |
| **Coordinador (orchestrator)** | ✅ Producción | Classify → Plan → Validate → Dispatch (LangGraph). 14 dispatchers por dominio. |
| **Orquestador (scheduler workflows)** | ✅ Producción | APScheduler + cron + event triggers + idempotencia |
| **Autonomía configurable** | ✅ Producción | Por tenant, qué puede hacer la IA sin aprobación humana |
| **Generative UI (LLM streaming)** | 🟡 Beta | Componentes dinámicos con `generative_ui` model |
| **Approvals fiscales** | ✅ Producción | Workflow de aprobación humana para operaciones fiscales (migración 0013) |

### 2.3 Compliance fiscal español — **EL MOAT REAL**

Esto es lo que ninguna competencia internacional puede replicar rápido. Construir esto correctamente lleva 6–12 meses de un equipo experto.

| Compliance | Estado | Detalle |
|---|---|---|
| **Verifactu** | ✅ Producción | 4 migraciones (0011 chain, 0018 backfill flag, 0023 config). Cadena de hash, configuración por tenant, ruta `verifactu_config.py` |
| **WORM Audit Trail** | ✅ Producción | Migración 0012 — audit log inmutable, write-once requerido por AEAT |
| **Fiscal Approval Log** | ✅ Producción | Migración 0013 — registro de quién aprobó cada operación fiscal |
| **Modelos AEAT** | ✅ Producción | Ruta `modelos_aeat.py` + `services/presentacion/` para presentación asistida |
| **REGAP** | ✅ Producción | Onboarding REGAP + status por tenant (migración 0019) |
| **BOE / Compliance queries** | ✅ Producción | Agent `compliance` + tool `check_boe_news`, `fiscal_query` |
| **Facturae** | ⚪ No confirmado | Verificar si exporta formato Facturae oficial |
| **TicketBAI / regionales** | ❌ No | País Vasco / Navarra requerirían adaptación |

### 2.4 Infraestructura y plataforma

| Componente | Estado | Notas |
|---|---|---|
| Multi-tenancy estricto | ✅ Producción | `tenant_id: UUID` en todos los modelos, filtros automáticos en endpoints |
| Multi-idioma (i18n) | ✅ Producción | `services/i18n/`, ruta de configuración `/configuracion/idioma` |
| Backup local | ✅ Producción | `services/backup/`, ruta `backup_local.py`, migración 0017 |
| Audit log + domain events | ✅ Producción | Trazabilidad completa |
| Cifrado credenciales | ✅ Producción | PBKDF2 (100k) + Fernet para tokens OAuth |
| Rate limiting | ✅ Producción | slowapi en endpoints de auth |
| Prompt injection guard | ✅ Producción | `prompt_sanitizer.py` |
| Security headers + CSP | ✅ Producción | X-Content-Type, HSTS, Frame-Options |
| JWT + refresh tokens | ✅ Producción | 60min access + 30d refresh |
| OAuth Google/Microsoft | ✅ Producción | Gmail, Outlook, Drive, OneDrive |
| LLM usage metering | ✅ Producción | Modelo `metering`, ruta `llm_usage.py` |
| Observabilidad opcional | 🟡 Opcional | Langfuse integrado pero opt-in |
| Firma digital | ✅ Producción | Configuración en `/configuracion/firma-digital` |
| Importación masiva | ✅ Producción | `import_bulk.py` para migración inicial de clientes |
| Onboarding wizard | ✅ Producción | `onboarding_wizard.py` + bienvenida con simulación-303 |
| Generación PDFs | ✅ Producción | `services/pdf/` + `services/pdf_reports/` (xhtml2pdf, weasyprint) |
| Generación DOCX | ✅ Producción | docxtpl, python-docx, mammoth, htmldocx |

### 2.5 Capa desktop (Electron)

Esto es donde el proyecto demuestra ambición real:

- **postgres-manager.js**: gestiona PostgreSQL portable (no Docker, no instalación system-wide)
- **python-manager.js**: gestiona Python embebido para el backend
- **jre-manager.js**: descarga Adoptium JRE 21 automáticamente para OpenDataLoader
- **network-utils.js**: lógica de red local
- **sync.js**: sincronización de cambios al exe ya instalado (commit hot-reload)
- **service-manager.js**: gestiona servicios del sistema
- **tray-manager.js**: bandeja del sistema
- **splash.html**: pantalla de carga

Resultado: instalable como un .exe que **no requiere Docker, ni Postgres preinstalado, ni Python, ni Java en el sistema del cliente**. Plug-and-play real. Esto es trabajo de empaquetado serio.

---

## 3. Stack técnico (real, verificado)

### Backend
- Python 3.11
- FastAPI 0.115
- SQLAlchemy 2.0 (async) + asyncpg + psycopg2-binary
- Alembic 1.13
- PostgreSQL 15 + pgvector
- LangGraph 0.2 + LangChain core 0.3
- langchain-openai 0.2, langchain-anthropic 0.3, langchain-groq 0.2, langchain-huggingface 0.1
- sentence-transformers 3.0
- Celery 5.3 + Redis 5 + APScheduler 3.10 + croniter (tres motores async coexistiendo)
- Pydantic 2.9 + pydantic-settings
- python-jose + PyJWT + passlib + bcrypt
- cryptography 43, slowapi
- xhtml2pdf, markdown-it-py, docxtpl, mammoth, htmldocx, python-docx
- pandas 2.2, openpyxl 3.1
- langfuse (observabilidad opcional)

### Frontend
- Next.js 14 + React 18 + TypeScript
- Zustand 4 (estado)
- Tailwind 3 + Radix UI completo (Avatar, Dialog, Dropdown, Label, Popover, ScrollArea, etc.)
- ReactFlow (editor visual de workflows)
- Recharts (gráficos)
- Sonner (toasts)
- Vitest + Playwright + @testing-library + axe-core (a11y)

### Desktop
- Electron
- PostgreSQL portable
- Python embebido
- JRE 21 portable (Adoptium) bajo demanda

### LLMs soportados
- **Claude Code CLI** (default desarrollo — usa suscripción Pro/Max via CLI)
- Anthropic (default producción) — Claude Sonnet 4.6 / Opus 4.6
- Gemini 2.5 Flash (alternativa barata)
- OpenAI GPT-4o-mini
- Groq Llama 3.3 70B
- OpenRouter (multi-modelo)
- **Ollama: eliminado** (confirmado en README)

### Embeddings
- BAAI/bge-m3 (HuggingFace, local, offline, multilingüe, 600MB)
- Gemini Embeddings (alternativa cloud)

---

## 4. Madurez por área

| Área | Madurez | Justificación |
|---|---|---|
| Facturación + Verifactu | ✅✅✅ Producción | Cadena de hash, audit WORM, backfill, config por tenant. Production-grade. |
| Contabilidad española | ✅✅✅ Producción | Libro diario, P&G, balance, activos. Cumple criterios PGC. |
| ERP core (clientes/productos/ventas) | ✅✅✅ Producción | Multi-tenant, validado, migraciones limpias |
| RAG + embeddings | ✅✅✅ Producción | Pipeline serio con OpenDataLoader + clasificación mecánica + smart chunker |
| Empleados IA + skills | ✅✅ Beta-Plus | Funcional, tests de routing (`test_routing_seam.py`) cubren 7 costuras críticas |
| Workflows + scheduler | ✅✅ Beta-Plus | APScheduler + recovery + NLP parser, pero falta hardening de edge cases |
| HR + nóminas | ✅✅ Beta-Plus | Cálculo IRPF + SS, aprobación. Falta auditoría de cálculos vs Hacienda real. |
| Compliance (BOE, modelos AEAT) | ✅✅ Beta | Funciona pero la fiabilidad fiscal requiere validación con asesor humano |
| POS | ✅ Beta | Construido, no certificable como TPV oficial |
| Sandbox Generativo UI | 🟡 Experimental | Funciona pero seguridad de HTML generado pendiente de hardening |
| Generative UI (componentes dinámicos) | 🟡 Experimental | Migración 0024, modelo presente, alcance limitado |
| Coverage tests | 🟡 Bajo | 113 tests para 67K LOC ≈ 0.17%. El seam de routing está cubierto, el resto no. |
| Documentación de usuario final | ❌ Ausente | No hay docs de cliente — solo README técnico |
| Marketing / Landing | ❌ Ausente | No hay sitio público |

---

## 5. Fortalezas reales

1. **Compliance fiscal español como moat técnico**. Verifactu + WORM audit + presentación asistida AEAT es una barrera de entrada significativa para competidores internacionales (Holded internacional, Odoo SaaS, Zoho). Tres años de ventaja técnica real.

2. **Empaquetado desktop honesto**. La capa Electron con Postgres/Python/JRE portables resuelve el problema #1 de adopción de ERP en pymes: instalación. Esto es trabajo de meses bien hecho.

3. **Pipeline RAG diseñado, no improvisado**. Clasificación mecánica (regex) antes de LLM ahorra 90% de tokens. Smart chunker respeta estructura. Citas con página exacta. Esto es ingeniería de producto.

4. **Catálogo de 45 skills + empleados IA**. La feature de empleados personalizables tiene producto real detrás (catálogo cerrado pero amplio, budget guard, instruct flow, activity feed). No es maquillaje.

5. **Arquitectura limpia y disciplinada**. ARCHITECTURE.md + CLAUDE.md + el contrato `run_agent()` muestran que se ha pensado en escalabilidad de código. La capa de routes → services → agents → models está respetada.

6. **Stack moderno y coherente**. FastAPI async + SQLAlchemy 2 async + Next 14 + LangGraph + pgvector es la combinación correcta para esta clase de producto en 2025–2026.

7. **Multi-tenancy real desde día 1**. No es retrofit. Todos los modelos tienen `tenant_id`, todas las rutas filtran.

8. **Tests del seam crítico de routing** (`test_routing_seam.py`). Cubre 7 costuras donde rompe el flujo modal→parse-nl→blueprint→NodeEngine→dispatcher→AIEmployee. Trabajo de ingeniero senior.

---

## 6. Brechas y limitaciones honestas

### 6.1 Técnicas

1. **"Local-first" tiene asterisco grande**: los datos en reposo viven en local, pero **cada inferencia LLM va a la nube** (Anthropic/Gemini/OpenAI). Para vender a ciberseguridad/legal/sanidad esto es bloqueante. Ollama fue eliminado del soporte.

2. **Cobertura de tests baja** (113 tests / 67K LOC). Riesgo de regresiones en módulos no cubiertos al refactorizar.

3. **Tres motores async coexistiendo** (Celery + APScheduler + TaskRunner asyncio). Complejidad operativa. Documentado pero frágil.

4. **Pre-producción sin cliente real**. La promesa de Verifactu funciona en tests pero no se ha sometido a un cierre fiscal real con AEAT.

5. **Drift de documentación**. README dice 9 agentes en la tabla, hay 13. README dice 7 archivos de test, hay 113. Hay otros desajustes menores. Esto se corrige con la reescritura.

6. **No hay separación clara prod vs dev**. El default `claude_code` para LLM va con la suscripción del desarrollador, no del cliente final. El cliente debe configurar su API key. Esto requiere onboarding cuidadoso.

7. **Coverage E2E es scaffold + 3 smoke tests** (commit 271268e, 2026-05-17 hoy). Las regresiones UI son riesgo real.

8. **Generative UI sandbox sin auditar HTML**: si la feature acepta HTML del LLM y lo renderiza, hay potencial XSS si no sanitiza. Verificar `dompurify` está en deps frontend (sí, `@types/dompurify` aparece).

### 6.2 Comerciales

1. **Cero clientes pagantes a fecha 2026-05-17**. 4 meses de desarrollo, 0 ingresos.

2. **Sin marketing ni presencia pública**. No hay landing, no hay SEO, no hay redes sociales activas vinculadas. Los leads (Correcta + bodega Argentina) llegaron por contacto directo, no por canal.

3. **Sin precio definido**. No hay tarifa pública, no hay flow de pago (la app valida licencia contra VPS pero no se ve flow de subscripción ni cobro).

4. **Solo dev**. Carga de mantenimiento de 67K LOC + 80 páginas + Electron + Postgres portable + Java + Python embebido = insostenible para una persona si crece la base de clientes.

5. **Producto demasiado ancho**. La estrategia ganadora para solo founder es **vertical estrecho**. Tener "todo" suena bien pero implica que ninguna feature es la mejor de su categoría.

### 6.3 De producto

1. **No hay Facturae export confirmado** — verificar.
2. **No hay TicketBAI** — corta País Vasco / Navarra.
3. **No hay integración con bancos PSD2 reales** — la app dice "PSD2" pero hay que validar si conecta con BBVA/Santander API o sólo importa CSV/MT940.
4. **No hay marketplace de skills** — los 45 skills son cerrados. Un cliente no puede añadir el suyo sin que tú toques código.
5. **Sin app móvil** — solo desktop + web.

---

## 7. Posicionamiento real en el mercado

### Competidores directos

| Competidor | Fortaleza | Tu ventaja | Su ventaja |
|---|---|---|---|
| **Holded** | ERP cloud español líder | Local-first + IA agentic + sandbox | Marca, equipo, integraciones, marketplace |
| **Sage 50/200** | Compatible asesorías | Más moderno, IA real | Compatibilidad asesorías tradicional |
| **Contasol** | Asesorías | UI moderna, multi-tenant, cloud-ready | Penetración masiva en asesorías |
| **A3 (Wolters Kluwer)** | Profesional contable | Precio, IA | Certificaciones, soporte profesional |
| **Odoo** | Open source modular | Vertical España, IA, local-first | Comunidad masiva, módulos infinitos |
| **Quipu** | Pymes simples | Mucho más capable | Onboarding rápido, marca |
| **Factorial** | HR + finanzas | Más amplio | Foco HR profundo, financiación |

### Donde NO compites

- Mercado masivo SaaS pyme genérico (Holded gana siempre)
- Asesorías tradicionales (necesitan integraciones legacy)
- Empresas grandes (necesitan SAP/Oracle, no compites)

### Donde SÍ compites (nicho viable)

1. **Asesorías fiscales/laborales medianas (10–50 clientes finales)**. Pagan €100–300/mes por software pro. Verifactu + presentación asistida + multi-tenant + IA es vendible.
2. **Pymes con datos sensibles**: ciber, legal, salud privada, auditoras. Pitch local-first + DPA Anthropic, target €150–400/mes.
3. **Bodegas, fabricantes pequeños con flujo específico**: necesitan adaptación (€3–8k setup), licencia €200/mes. Servicios + producto.
4. **Empresas que quieren "su propio equipo de IA"**: posicionas Empleados IA como diferencial, no como feature. Target €200–500/mes por las 10–20 personas-IA que reemplazan tareas.

### Donde podrías ser único

**Asesorías + IA + local-first** es un cuadrante vacío:
- Holded/Quipu = cloud, sin IA real
- Sage/Contasol = local, sin IA, anticuados
- Tú = local + IA agentic + español + compliance

Es un mercado de ~30.000 asesorías en España. Capturar 50 clientes a €150/mes = €7.500 MRR = €90.000 ARR. Negocio real solo-founder.

---

## 8. Vectores de monetización viables (ordenados por probabilidad de éxito)

### V1 — Asesorías fiscales/laborales pequeñas-medianas (RECOMENDADO)
- **Pitch**: "El A3 del futuro, con IA que clasifica documentos, redacta nóminas y presenta modelos por ti".
- **Target**: 30.000 asesorías en España, foco en 5–20 empleados
- **ARPU**: €150–300/mes
- **Setup**: €500–1.500
- **CAC**: alto (telemarketing + demo)
- **Camino mínimo viable**: 30 demos → 5 clientes → €1.000 MRR en 90 días

### V2 — Pymes con datos sensibles (Correcta-like)
- **Pitch**: "ERP español con IA que NO sube tus datos a la nube de un americano"
- **Target**: 5.000 pymes ciber/legal/sanidad/auditoría
- **ARPU**: €200–500/mes
- **Setup**: €1.000–3.000
- **CAC**: medio (LinkedIn + eventos sectoriales como OAP Valencia)
- **Bloqueante**: necesitas reintegrar LLM local (Ollama o similar) o pitch honesto con DPA. Sin esto, no eres creíble en demo técnica.

### V3 — Servicios + producto para verticales raros (bodega Argentina)
- **Pitch**: caso a caso. "Te adapto el ERP a tu sector y te lo licencio"
- **ARPU**: €200–400/mes + €3.000–8.000 setup
- **CAC**: bajo (los clientes ya te encuentran)
- **Margen**: alto en setup, recurrente bajo si no cierras volumen
- **Riesgo**: cada cliente es un fork; complejidad operativa explota a partir de 5

### V4 — White-label para integradores
- Vender la plataforma a integradores que tienen su cartera de pymes
- ARPU al integrador: €500–1.500/mes (luego él vende a sus clientes finales)
- Pocas operaciones, alto ticket
- Requiere madurez de producto que aún no tienes

### V5 — Marketplace de skills (futuro lejano)
- Otros devs construyen skills, tú cobras 30%
- No viable sin masa crítica (>200 clientes)

### Lo que NO recomiendo

- **Gratuito**: garantiza tu peor miedo ("nadie lo usa") porque sin promoción nadie te encuentra, y si te encuentran, los datos fiscales en software no mantenido son un problema
- **Pago único**: trampa con Verifactu (regulación cambia anualmente)
- **SaaS horizontal pyme genérico**: cementerio de productos así

---

## 9. Plan de acción 90 días (si decides seguir)

Este plan asume que la decisión es **seguir e intentar monetizar**, no abandonar.

### Días 1–7 — Validación
- [ ] Cero código nuevo
- [ ] Reactivar Correcta con email del pitch ajustado (matiz local-first honesto)
- [ ] Llamar a la bodega Argentina para call de descubrimiento
- [ ] Llamar a 20 asesorías fiscales pequeñas en Valencia (cold + LinkedIn)
- [ ] Objetivo: 5 conversaciones concretas, no ventas

### Días 8–30 — Cierre piloto
- [ ] 3 pilotos con condiciones: 2 meses gratis + feedback semanal + €X/mes después
- [ ] Documentar fricción de onboarding real
- [ ] Decidir el vertical: asesorías vs ciber vs bodegas

### Días 31–60 — Producto del vertical elegido
- [ ] Si vertical = asesorías: reforzar gestión multi-cliente, Facturae export, modelos AEAT específicos
- [ ] Si vertical = ciber: reintegrar Ollama o llama.cpp para LLM local de verdad
- [ ] Si vertical = bodegas: AFIP WSFE + lotes/trazabilidad
- [ ] **No tocar nada fuera del vertical** durante este sprint

### Días 61–90 — Cierre comercial
- [ ] Convertir 2 de los 3 pilotos a pago real
- [ ] Documentación de usuario final (no técnica) para el vertical
- [ ] Landing simple (puede ser una página) + formulario de contacto
- [ ] Decisión: si MRR > €500 → seguir. Si MRR = 0 → revisar pivote o cerrar dignamente.

---

## 10. Conclusión honesta

El proyecto **no es un fracaso técnico**, ni siquiera cerca. Es uno de los productos individuales más completos y bien construidos que he visto en este vertical. La amplitud y la calidad de empaquetado están muy por encima del solo-founder español medio.

El problema **no es el producto**, es la **distribución**. El producto sabe demasiado y ha vendido demasiado poco. 4 meses sin clientes no es señal de "no funciona", es señal de "nadie sabe que existe".

La decisión real ahora no es "vender o regalar". Es:

- **¿Quieres vender esto?** → V1 o V2, 30 días de ventas duras, decidir con datos.
- **¿No quieres vender pero te importa que exista?** → Open source MIT en GitHub, sin promesa de soporte. La comunidad lo encuentra si encuentra valor.
- **¿No quieres ninguna de las dos?** → Pausa indefinida. El código no se va a ningún lado. Capitalizas el aprendizaje técnico (LangGraph, async SQLA, Electron empaquetado, pgvector, RAG) en otro trabajo. Eso vale €45–70k/año en España como senior.

Las tres son honorables. Lo que **no** es honorable es decidir desde el agotamiento sin haber dado al producto su oportunidad comercial.

---

*Auditoría hecha con análisis directo del código en `backend/app/`, `frontend/src/`, `desktop/`, `tasks/`, y `README.md` actual.*
