# Lessons Learned

## asyncio en LangGraph tools
- **Pattern**: `@tool` functions que usan `asyncio.get_event_loop().run_until_complete()` o `asyncio.run()` fallan en LangGraph porque se ejecutan en threads sin event loop o con loop diferente al de SQLAlchemy.
- **Fix**: Hacer los `@tool` directamente `async def` y usar `await`. LangGraph soporta async tools nativamente.
- **Also**: Los nodos del grafo (`*_agent_node`) deben ser `async def` y usar `ainvoke()` en vez de `invoke()`.

## Categorias de documentos en frontend
- **Pattern**: El frontend filtra documentos por `category` (excels, informes, contratos, etc.). Si el backend guarda con una categoria incorrecta, el documento no aparece en la carpeta esperada.
- **Fix**: Verificar que la categoria usada en el backend coincide con los IDs de carpeta del frontend (`documentos/page.tsx`).

## Electron empaqueta codigo al build time
- **Pattern**: Cambios en el codigo fuente no se reflejan en la app instalada hasta reempaquetar con `npx electron-builder --win`.
- **Fix**: Siempre reempaquetar despues de cambios en backend/agents.
