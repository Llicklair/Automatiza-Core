from fastapi import APIRouter

from app.api.v1.routes import (
    accounting,
    admin,
    advisory,
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
    crm,
    documents,
    erp,
    generative_ui,
    hr,
    hr_documents,
    import_bulk,
    integrations,
    llm_usage,
    messaging,
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
    system,
    tasks,
    telemetry,
    templates,
    tenant,
    users,
    verifactu_config,
    verify,
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
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(reports.router)
api_router.include_router(analytics.router)
api_router.include_router(tenant.router)
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(ai_employees.router)
api_router.include_router(recruitment.router, prefix="/recruitment", tags=["recruitment"])
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
api_router.include_router(messaging.router)
api_router.include_router(hr_documents.router)
api_router.include_router(generative_ui.router)
api_router.include_router(users.router)
api_router.include_router(system.router)
api_router.include_router(llm_usage.router)
api_router.include_router(search.router)
api_router.include_router(portal.router)
api_router.include_router(import_bulk.router)
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(calendar.router)
api_router.include_router(client_portal.router)
api_router.include_router(verify.router)
api_router.include_router(telemetry.router)
api_router.include_router(backup_local.router)
api_router.include_router(onboarding_regap.router)
api_router.include_router(onboarding_wizard.router)
api_router.include_router(autonomy.router)
api_router.include_router(notifications.router)
api_router.include_router(verifactu_config.router)
api_router.include_router(presentacion_asistida.router)
api_router.include_router(modelos_aeat.router)
api_router.include_router(pos.router)
