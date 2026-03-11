import os
import uuid
from pydantic import BaseModel
from sqlalchemy.future import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument
from app.core.config import settings

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
import pandas as pd

class ExcelAgentResult(BaseModel):
    success: bool
    action: str
    output_message: str
    error: str | None = None

def _get_llm():
    return ChatOllama(
        model="llama3.2",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )

SYSTEM_PROMPT = """Eres un experto en Pandas y automatización de datos. 
Tu tarea es escribir un bloque de código Python que procese archivos Excel/CSV y genere un nuevo archivo de resultado.
Solo puedes usar la librería `pandas` y la librería estándar de Python.
Dispones de las siguientes variables globales en tu entorno de ejecución:
- `INPUT_FILES`: un diccionario donde las claves son los nombres de archivo y los valores son las rutas absolutas donde están esos archivos. Ej: {"ventas.xlsx": "/ruta/a/ventas.xlsx"}
- `OUTPUT_PATH`: ruta absoluta donde debes guardar el archivo Excel final (.xlsx) con el resultado usando `df.to_excel(OUTPUT_PATH, index=False)`.

INSTRUCCIONES CRÍTICAS:
1. Devuelve ÚNICAMENTE código Python, sin usar bloques de formato markdown como ```python ni ```. Solo texto plano ejecutable.
2. No uses print(). Todo el procesamiento debe acabar guardando el dataframe en OUTPUT_PATH.
3. No intentes importar librerías ajenas a `pandas`.
4. El usuario te indicará qué quiere hacer. Busca en `INPUT_FILES` si menciona algún archivo.
5. El código debe ser tolerante a errores, pero directo a la solución.
"""

async def run_excel_agent(user_intent: str, tenant_id: str, task_id: str) -> ExcelAgentResult:
    import re
    # 1. Fetch available files
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TenantDocument).where(TenantDocument.tenant_id == uuid.UUID(tenant_id)))
        docs = result.scalars().all()

    input_files = {}
    for doc in docs:
        if doc.file_path and os.path.exists(doc.file_path):
            if doc.file_name.lower().endswith(('.xlsx', '.csv', '.xls')):
                input_files[doc.file_name.lower()] = doc.file_path

    if not input_files:
        return ExcelAgentResult(
            success=False,
            action="failed",
            output_message="No hay archivos Excel o CSV en el sistema para esta empresa.",
            error="Faltan archivos"
        )
    
    # Generate an output path
    output_dir = os.path.dirname(list(input_files.values())[0])
    output_filename = f"resultado_ia_{task_id[:8]}.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # 2. Ask LLM to generate the python script
    llm = _get_llm()
    prompt = f"""Archivos disponibles en INPUT_FILES: {list(input_files.keys())}
    OUTPUT_PATH: {output_path}
    
    Petición del usuario: {user_intent}
    
    Genera el código Python para procesar esto. Recuerda, SOLO el código en texto plano, sin formato de markdown:
    """

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
    
    try:
        response = await llm.ainvoke(messages)
        code = response.content.strip()
        
        # Clean markdown if ollama wraps it
        if code.startswith("```"):
            code = re.sub(r"^```(?:python)?\n?", "", code)
            code = re.sub(r"\n?```$", "", code)
            
        print("[EXCEL_AGENT] Código generado:\n", code)
        
        # 3. Execute the code locally
        exec_globals = {
            "INPUT_FILES": input_files,
            "OUTPUT_PATH": output_path,
            "pd": pd,
        }
        
        # Security Note: exec() is dangerous in prod, this is a prototype sandbox
        exec(code, exec_globals)
        
        if not os.path.exists(output_path):
            return ExcelAgentResult(
                success=False,
                action="failed",
                output_message="El código se ejecutó pero no generó ningún archivo de resultado.",
                error="Archivo no generado"
            )
            
        # 4. Save the result as a new Document in DB so user can download it
        async with AsyncSessionLocal() as db:
            new_doc = TenantDocument(
                tenant_id=uuid.UUID(tenant_id),
                task_id=uuid.UUID(task_id),
                file_name=output_filename,
                file_path=output_path,
                file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                file_size=os.path.getsize(output_path),
                category="informes",
                status="completed",
                parsed_content=f"Generado por IA para la petición: {user_intent}",
            )
            db.add(new_doc)
            await db.commit()
            
        return ExcelAgentResult(
            success=True,
            action="excel_generated",
            output_message=f"Archivo {output_filename} generado correctamente combinando datos."
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ExcelAgentResult(
            success=False,
            action="failed",
            output_message=f"Error durante la ejecución del script de datos: {e}",
            error=str(e)
        )
