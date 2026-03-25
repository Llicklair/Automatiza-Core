"""
Reports API package.

Assembles the main router from sub-modules:
  - snapshot:    company snapshot GET/POST + report CRUD (list, download, delete)
  - fiscal:      fiscal snapshot GET/POST + modelo 303 + libro registro
  - specialized: cashflow + delinquency + compliance RGPD
"""

from fastapi import APIRouter

from .fiscal import router as fiscal_router
from .snapshot import router as snapshot_router
from .specialized import router as specialized_router

router = APIRouter(prefix="/reports", tags=["reports"])

router.include_router(snapshot_router)
router.include_router(fiscal_router)
router.include_router(specialized_router)
