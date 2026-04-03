from fastapi import APIRouter

from app.api.v1.routes import (
    accounting,
    admin,
    advisory,
    ai_employees,
    approvals,
    generative_ui,
    hr_documents,
    messaging,
    recruitment,
    scanner,
    auth,
    banking,
    crm,
    documents,
    erp,
    hr,
    integrations,
    projects,
    quotes,
    reports,
    skills,
    tasks,
    templates,
    tenant,
    workflows,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(integrations.router)
api_router.include_router(documents.router)
api_router.include_router(erp.router)
api_router.include_router(crm.router)
api_router.include_router(banking.router, prefix="/banking")
api_router.include_router(hr.router)
api_router.include_router(projects.router)
api_router.include_router(accounting.router)
api_router.include_router(advisory.router)
api_router.include_router(workflows.router)
api_router.include_router(skills.router)
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(reports.router)
api_router.include_router(tenant.router)
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(ai_employees.router)
api_router.include_router(recruitment.router, prefix="/recruitment", tags=["recruitment"])
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
api_router.include_router(messaging.router)
api_router.include_router(hr_documents.router)
api_router.include_router(generative_ui.router)
