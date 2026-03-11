"""
Agente RAG — Fase 3.

Funciones:
  1. Recibe una pregunta del usuario sobre sus documentos.
  2. Convierte la pregunta en un Vector (Embedding).
  3. Busca los N fragmentos más similares en la base de datos (pgvector).
  4. Pasa los fragmentos como contexto al LLM.
  5. El LLM responde basándose ÚNICAMENTE en esos fragmentos.
"""

import uuid

import sqlalchemy as sa
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.embeddings import DocumentEmbedding

# ─── LLM y Embeddings ────────────────────────────────────────────────────────

def _get_llm():
    return ChatOllama(
        model="llama3.2",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )

def _get_embedder():
    return OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=settings.OLLAMA_BASE_URL,
    )


# ─── Resultado del Agente ────────────────────────────────────────────────────

class RagAgentResult(BaseModel):
    success: bool
    answer: str
    sources_used: int
    source_names: list[str] = [] # Nombres de los archivos encontrados
    error: str | None = None


# ─── Función principal del agente ────────────────────────────────────────────

async def run_rag_agent(
    user_intent: str,
    tenant_id: str,
    top_k: int = 5
) -> RagAgentResult:
    """Busca fragmentos relevantes y responde la pregunta."""
    if not tenant_id:
        return RagAgentResult(success=False, answer="", sources_used=0, error="Tenant ID requerido")

    # 1. Generar embedding de la pregunta
    embedder = _get_embedder()
    try:
        # Pide una lista porque el base method embeddings(texts) lo espera, aqui mandamos 1
        query_vector = await embedder.aembed_query(user_intent)
    except Exception as e:
        return RagAgentResult(success=False, answer="", sources_used=0, error=f"Fallo al vectorizar pregunta: {e}")

    # 2. Búsqueda Híbrida: Nombres de archivo + Similitud Semántica
    retrieved_chunks = []
    source_names = set()
    try:
        from app.db.models.models import TenantDocument
        async with AsyncSessionLocal() as db:
            # 2.a Búsqueda literal en nombres de archivo (Search bar mode)
            stmt_files = sa.select(TenantDocument).where(
                TenantDocument.tenant_id == uuid.UUID(tenant_id),
                sa.or_(
                    TenantDocument.file_name.ilike(f"%{user_intent}%"),
                    TenantDocument.category.ilike(f"%{user_intent}%")
                )
            ).limit(2)
            res_files = await db.execute(stmt_files)
            found_docs = res_files.scalars().all()
            for fd in found_docs:
                source_names.add(fd.file_name)
                retrieved_chunks.append({
                    "doc_id": fd.id,
                    "text": f"Documento ENCONTRADO por nombre: {fd.file_name}. Categoría: {fd.category}. Contenido resumido: {fd.parsed_content[:500] if fd.parsed_content else 'N/A'}"
                })

            # 2.b Búsqueda de similitud en PGVector
            stmt_vector = sa.select(DocumentEmbedding).where(
                DocumentEmbedding.tenant_id == uuid.UUID(tenant_id)
            ).order_by(
                DocumentEmbedding.embedding.cosine_distance(query_vector)
            ).limit(top_k)
            
            res_vector = await db.execute(stmt_vector)
            best_matches = res_vector.scalars().all()
            
            for match in best_matches:
                # Recuperar nombre del documento para el usuario
                doc_name_stmt = sa.select(TenantDocument.file_name).where(TenantDocument.id == match.document_id)
                doc_name_res = await db.execute(doc_name_stmt)
                doc_name = doc_name_res.scalar()
                if doc_name:
                    source_names.add(doc_name)
                
                retrieved_chunks.append({
                    "doc_id": match.document_id,
                    "text": match.text_content
                })
    except Exception as e:
        return RagAgentResult(success=False, answer="", sources_used=0, error=f"Fallo en búsqueda híbrida: {e}")

    if not retrieved_chunks:
        answer = "No he encontrado ningún documento en tu base de datos que contenga información de utilidad para responder a esta pregunta."
        return RagAgentResult(success=True, answer=answer, sources_used=0)

    # 3. Construir contexto
    contexto_texto = ""
    for idx, c in enumerate(retrieved_chunks, 1):
        contexto_texto += f"\n--- Fragmento {idx} (Doc ID: {c['doc_id']}) ---\n{c['text']}\n"

    # 4. Formular Prompt y consultar LLM
    prompt = f"""Eres un asesor empresarial experto. Responde a la pregunta del usuario utilizando ÚNICAMENTE la información de los fragmentos de documentos proporcionados a continuación.
Si no puedes responder a la pregunta con la información proporcionada, indica amablemente que no tienes suficientes datos en los documentos archivados sin inventar respuestas.
Nunca menciones "fragmento" u "origen" explícitamente a menos que sea útil.

CONTEXTO EXTRAÍDO DE LOS DOCUMENTOS:
{contexto_texto}

PREGUNTA DEL USUARIO:
{user_intent}"""

    llm = _get_llm()
    try:
        messages = [
            SystemMessage(content="Eres un asistente contable y legal preciso que solo responde basado en los documentos adjuntos."),
            HumanMessage(content=prompt)
        ]
        response = await llm.ainvoke(messages)
        answer = response.content
    except Exception as e:
        return RagAgentResult(success=False, answer="", sources_used=0, error=f"Fallo en la inferencia del LLM: {e}")

    return RagAgentResult(
        success=True,
        answer=answer,
        sources_used=len(retrieved_chunks),
        source_names=list(source_names)
    )
