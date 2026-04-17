"""Servicios de dominio para gestión documental."""

from app.services.documents.classifier import RuleClassification, classify_by_rules
from app.services.documents.docx_html_save import save_html_as_docx
from app.services.documents.docx_preview import docx_to_preview_html
from app.services.documents.scanner import confirm_delivery, record_movement, scan_product
from app.services.documents.service import (
    auto_classify_category,
    auto_classify_tabular,
    delete_contract_template,
    delete_document,
    export_all,
    extract_zip_entries,
    generate_contract_from_template,
    get_contract_template,
    get_document,
    import_tabular_file,
    list_contract_templates,
    list_documents,
    parse_tabular_file,
    prepare_download,
    preview_contract_html,
    save_contract_html,
    save_contract_html_and_update,
    scan_single,
    update_content,
    upload_bulk,
    upload_contract_template,
    upload_single,
    validate_upload,
)
from app.services.documents.smart_chunker import Chunk, smart_chunk

__all__ = [
    # service (includes re-exports from _file_ops, _contracts, _tabular)
    "auto_classify_category",
    "auto_classify_tabular",
    "delete_contract_template",
    "delete_document",
    "export_all",
    "extract_zip_entries",
    "generate_contract_from_template",
    "get_contract_template",
    "get_document",
    "import_tabular_file",
    "list_contract_templates",
    "list_documents",
    "parse_tabular_file",
    "prepare_download",
    "preview_contract_html",
    "save_contract_html",
    "save_contract_html_and_update",
    "scan_single",
    "update_content",
    "upload_bulk",
    "upload_contract_template",
    "upload_single",
    "validate_upload",
    # classifier
    "classify_by_rules",
    "RuleClassification",
    # scanner
    "scan_product",
    "record_movement",
    "confirm_delivery",
    # docx
    "docx_to_preview_html",
    "save_html_as_docx",
    # smart_chunker
    "smart_chunk",
    "Chunk",
]
