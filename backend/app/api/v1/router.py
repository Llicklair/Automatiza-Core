from fastapi import APIRouter, Depends

from app.core.plan_gate import require_plan

_PRO = [Depends(require_plan("pro"))]
_GESTORIA = [Depends(require_plan("gestoria"))]

from app.api.v1.routes import (
    accounting,
    admin,
    advisory,
    aeat_presentation,
    ai_employees,
    alerts,
    analytics,
    approvals,
    auth,
    autonomy,
    backup_local,
    banking,
    calendar,
    client_portal,
    collections,
    crm,
    documents,
    email_marketing,
    erp,
    generative_ui,
    hr,
    hr_documents,
    import_bulk,
    integrations,
    license,
    llm_usage,
    marketing,
    marketplace,
    messaging,
    metrics,
    modelos_aeat,
    notifications,
    onboarding_regap,
    onboarding_wizard,
    portal,
    pos,
    presentacion_asistida,
    projects,
    quotes,
    recruitment,
    reports,
    scanner,
    search,
    signing,
    system,
    tasks,
    telemetry,
    templates,
    tenant,
    treasury,
    users,
    warehouses,
    workflows,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(integrations.router, dependencies=_PRO)
api_router.include_router(documents.router, dependencies=_PRO)
api_router.include_router(erp.router)
api_router.include_router(crm.router, dependencies=_PRO)
api_router.include_router(banking.router, prefix="/banking", dependencies=_PRO)
api_router.include_router(treasury.router, dependencies=_PRO)
api_router.include_router(collections.router, dependencies=_PRO)
api_router.include_router(marketplace.router)
api_router.include_router(signing.router)
api_router.include_router(hr.router, dependencies=_PRO)
api_router.include_router(projects.router)
api_router.include_router(accounting.router, dependencies=_PRO)
api_router.include_router(advisory.router)
api_router.include_router(workflows.router)
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(reports.router, dependencies=_PRO)
api_router.include_router(analytics.router, dependencies=_PRO)
api_router.include_router(tenant.router)
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(ai_employees.router)
api_router.include_router(recruitment.router, prefix="/recruitment", tags=["recruitment"], dependencies=_PRO)
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
api_router.include_router(messaging.router)
api_router.include_router(hr_documents.router, dependencies=_PRO)
api_router.include_router(generative_ui.router)
api_router.include_router(users.router)
api_router.include_router(warehouses.router)
api_router.include_router(system.router)
api_router.include_router(llm_usage.router)
api_router.include_router(search.router)
api_router.include_router(portal.router, dependencies=_GESTORIA)
api_router.include_router(import_bulk.router)
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"], dependencies=_PRO)
api_router.include_router(calendar.router)
api_router.include_router(client_portal.router, dependencies=_GESTORIA)
api_router.include_router(telemetry.router)
api_router.include_router(backup_local.router)
api_router.include_router(onboarding_regap.router)
api_router.include_router(onboarding_wizard.router)
api_router.include_router(autonomy.router)
api_router.include_router(notifications.router)
api_router.include_router(presentacion_asistida.router, dependencies=_PRO)
api_router.include_router(modelos_aeat.router, dependencies=_PRO)
api_router.include_router(aeat_presentation.router, dependencies=_PRO)
api_router.include_router(pos.router)
api_router.include_router(marketing.router, dependencies=_GESTORIA)
api_router.include_router(email_marketing.router, dependencies=_PRO)
api_router.include_router(metrics.router)
api_router.include_router(license.router)
