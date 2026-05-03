"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.hr.commands import (
    create_employee,
    delete_employee,
    update_employee,
    # payroll writes
    approve_payroll,
    create_payroll,
    create_payroll_auto,
    delete_payroll,
    generate_and_save_payroll_pdf,
    update_payroll,
    # employee doc writes
    delete_employee_document,
    upload_employee_document,
    # special docs
    generate_finiquito_pdf,
    generate_liquidacion_pdf,
    generate_registro_jornada,
)
from app.services.hr.queries import (
    UPLOAD_DIR,
    calc_payroll,
    get_employee,
    list_employees,
    # payroll reads
    build_payroll_pdf,
    download_payroll_pdf,
    list_payrolls,
    preview_payroll,
    # employee doc reads
    get_employee_document,
    list_employee_documents,
    read_document_file,
    # special docs
    load_employee_and_tenant,
)

__all__ = [
    "calc_payroll",
    "list_employees",
    "get_employee",
    "create_employee",
    "update_employee",
    "delete_employee",
    "list_payrolls",
    "preview_payroll",
    "build_payroll_pdf",
    "download_payroll_pdf",
    "create_payroll",
    "create_payroll_auto",
    "update_payroll",
    "delete_payroll",
    "approve_payroll",
    "generate_and_save_payroll_pdf",
    "get_employee_document",
    "list_employee_documents",
    "read_document_file",
    "upload_employee_document",
    "delete_employee_document",
    "load_employee_and_tenant",
    "generate_finiquito_pdf",
    "generate_liquidacion_pdf",
    "generate_registro_jornada",
    "UPLOAD_DIR",
]
