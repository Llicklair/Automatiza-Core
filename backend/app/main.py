"""Aplicación principal FastAPI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s arrancando", settings.APP_NAME, settings.APP_VERSION)
    yield
    logger.info("Cerrando aplicación")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SaaS de automatización administrativa multiagente para PYMEs",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS — en producción, restringir a dominio del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todos los orígenes temporalmente para development local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.ws.notifications import router as ws_router

app.include_router(api_router)
app.include_router(ws_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. El equipo ha sido notificado."},
    )


@app.get("/health", tags=["system"])
async def health_check():
    return JSONResponse({"status": "ok", "version": settings.APP_VERSION})


@app.get("/", tags=["system"])
async def root():
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}
