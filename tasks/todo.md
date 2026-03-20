# Plan: Integrar OpenDataLoader PDF en pipeline RAG

## Estado actual vs propuesto

### RAG ACTUAL (pypdf)
```
Usuario sube PDF
    │
    ▼
pypdf.PdfReader (8 páginas max, 5.000 chars max)
    │
    ▼
LLM clasifica documento (~4.500 chars → Gemini)          ← 1 llamada LLM
    │
    ▼
Chunking: segmentos de 1.500 chars (corte mecánico)
    │
    ▼
Embeddings: BAAI/bge-m3 local (gratis) o Gemini/OpenAI
    │
    ▼
pgvector (tabla document_embeddings)
    │
    ▼
Consulta RAG: top 5 chunks × 500 chars = 2.500 chars     ← 1 llamada LLM (~3K chars)
```

**Problemas actuales:**
- Máximo 8 páginas, 5.000 chars → documentos largos pierden información
- pypdf no extrae tablas (las ignora o las rompe)
- Sin OCR → PDFs escaneados = vacío
- Chunks de 1.500 chars sin respetar estructura → corta tablas/párrafos a mitad
- Sin bounding boxes → no puedes citar "página X, sección Y"

---

### RAG PROPUESTO (OpenDataLoader)
```
Usuario sube PDF
    │
    ▼
OpenDataLoader convert() → Markdown + JSON con bounding boxes
  ├─ Modo local: 0.05s/página (texto simple)
  └─ Modo híbrido: 0.43s/página (tablas complejas, OCR, fórmulas)
    │
    ▼
Chunking inteligente: respetar headings, tablas completas, tipo de elemento
  (usa JSON metadata: type, heading_level, page_number)
    │
    ▼
LLM clasifica documento (mismo coste, pero con MEJOR texto)  ← 1 llamada LLM
    │
    ▼
Embeddings: BAAI/bge-m3 local (gratis) — MÁS chunks porque más texto
    │
    ▼
pgvector (misma tabla, añadir campos metadata)
    │
    ▼
Consulta RAG: top 5 chunks + metadata posicional              ← 1 llamada LLM (~3-5K chars)
```

---

## Comparativa de consumo de tokens

### Ingestión (por documento)
| Concepto | Actual (pypdf) | Propuesto (OpenDataLoader) |
|----------|---------------|---------------------------|
| Parsing PDF | 0 tokens (pypdf local) | 0 tokens (OpenDataLoader local) |
| Texto extraído | Max 5.000 chars (8 págs) | Doc completo (todas las págs) |
| Llamada clasificación LLM | ~4.500 chars input | ~4.500 chars input (mismo) |
| Embeddings (bge-m3 local) | ~3-4 chunks × 0 tokens | ~10-30 chunks × 0 tokens |
| Embeddings (Gemini/OpenAI) | ~3-4 chunks × ~500 tok c/u | ~10-30 chunks × ~500 tok c/u |
| **Total tokens ingestión** | **~1.500 tokens** | **~1.500 tokens** (mismo) |
| **Total si Gemini embeddings** | **~3.500 tokens** | **~16.500 tokens** (+4.7x) |

### Consulta RAG (por pregunta)
| Concepto | Actual | Propuesto |
|----------|--------|-----------|
| Embedding query | 1 embedding (~100 tok) | 1 embedding (~100 tok) |
| Contexto al LLM | 5 × 500 chars = ~800 tok | 5 × 800 chars = ~1.300 tok |
| System prompt + pregunta | ~500 tok | ~600 tok |
| **Total por consulta** | **~1.400 tokens** | **~2.000 tokens** (+43%) |

### Conclusión de costes
| Escenario | Actual | Propuesto | Diferencia |
|-----------|--------|-----------|------------|
| **Embeddings locales (bge-m3)** | 1.500 tok/doc | 1.500 tok/doc | **IGUAL** |
| **Embeddings Gemini** | 3.500 tok/doc | 16.500 tok/doc | +370% ingestión |
| **Consulta RAG** | 1.400 tok/query | 2.000 tok/query | +43% por query |
| **Calidad respuesta** | Baja (texto roto) | Alta (estructura intacta) | **Mucho mejor** |

> **Con embeddings locales (tu config por defecto), el coste de tokens es PRÁCTICAMENTE IGUAL.**
> La diferencia real está en la CALIDAD, no en el coste.
> Si usas Gemini embeddings, más coste en ingestión porque generas más chunks (pero mejores).

---

## Workflow detallado paso a paso

### FASE 1: Ingestión de documentos

```
1. Usuario sube PDF via frontend → /api/v1/documents/upload
2. Backend guarda archivo en disco (ya existe)
3. NUEVO — OpenDataLoader parsea el PDF:
   opendataloader_pdf.convert(
       input_path=["ruta/archivo.pdf"],
       output_dir="temp/parsed/",
       format="markdown,json"
   )
4. Lee markdown (texto limpio con tablas intactas)
5. Lee JSON (metadata: bounding boxes, tipos, páginas)
6. Chunking inteligente:
   - Recorre elementos del JSON
   - Agrupa por secciones (heading → contenido hasta siguiente heading)
   - Tablas siempre como chunk completo (nunca cortadas)
   - Cada chunk: text + page_number + element_type + bbox
7. Genera embeddings por chunk (bge-m3 local, sin coste)
8. Guarda en document_embeddings con metadata extra
9. Clasifica documento con LLM (igual que ahora)
10. Limpia archivos temporales
```

### FASE 2: Consulta RAG

```
1. "¿Cuál es el total de la factura de Empresa X?"
2. Embedding de la pregunta (bge-m3 local)
3. Top 5 chunks por cosine distance en pgvector (igual que ahora)
4. MEJORA: cada chunk ahora tiene:
   - Texto bien formateado (tablas intactas)
   - Número de página de origen
   - Tipo de elemento (tabla, párrafo, heading)
5. LLM responde + puede citar "Página 3, tabla de totales"
```

### FASE 3 (opcional): Modo híbrido

```
- Solo si se detectan tablas complejas o PDFs escaneados
- Requiere: opendataloader-pdf-hybrid como servicio
- En Electron: levantar como proceso hijo
- +90% precisión en tablas complejas
```

---

## Plan de implementación

### Paso 1: Dependencia
- [ ] Añadir `opendataloader-pdf` a requirements.txt
- [ ] Verificar Java 11+ disponible

### Paso 2: Servicio de parsing
- [ ] Crear `backend/app/services/pdf_parser.py`
  - `parse_pdf(path) -> ParsedDocument` (markdown + JSON + metadata)
  - Fallback a pypdf si JVM no disponible

### Paso 3: Chunking inteligente
- [ ] Crear `backend/app/services/smart_chunker.py`
  - Respetar límites de sección/heading
  - Tablas como chunks atómicos
  - Metadata por chunk (page, type, bbox)

### Paso 4: Modificar documents_agent.py
- [ ] Reemplazar pypdf por pdf_parser
  - Quitar límite de 8 páginas / 5.000 chars
  - Usar markdown para clasificación
  - Usar chunks inteligentes para embeddings

### Paso 5: Ampliar modelo document_embeddings
- [ ] Migración: añadir `page_number`, `element_type`, `bounding_box`
- [ ] Actualizar modelo SQLAlchemy

### Paso 6: Mejorar RAG agent
- [ ] rag_agent.py: incluir metadata en respuestas (citas con página)

### Paso 7: Config Electron
- [ ] Java en bundle portable o documentar requisito
- [ ] Opcional: hybrid backend como proceso hijo

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| JVM no disponible | Fallback a pypdf (degradación elegante) |
| Más chunks = más BD | pgvector maneja miles de vectores sin problema |
| Parsing más lento | Async, no bloquea UI |
| Java como dependencia extra | Bundlear JRE portable (~50MB) o requerir instalación |
| Hybrid mode complejo | Empezar solo con modo local; hybrid es fase 3 |
