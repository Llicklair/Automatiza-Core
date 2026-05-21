"""Marketplace de workflows (F3.10) — catálogo + import/export YAML.

API pública:
  - `list_templates(db, category=None)`     — devuelve el catálogo.
  - `get_template(db, slug)`                 — detalle por slug.
  - `install_template(db, tenant_id, slug)`  — instancia un Workflow real
                                               del tenant a partir de la
                                               plantilla.
  - `export_workflow_to_yaml(workflow)`      — serializa un Workflow del
                                               tenant a YAML para compartir.
  - `import_yaml_as_workflow(db, tenant_id, yaml_str)` — crea Workflow
                                               desde YAML pegado por el
                                               usuario.
  - `seed_official_templates(db)`            — inserta las plantillas
                                               oficiales (idempotente).
"""

from app.services.workflow_marketplace.catalog import (
    get_template,
    install_template,
    list_templates,
)
from app.services.workflow_marketplace.io_yaml import (
    WorkflowYamlError,
    export_workflow_to_yaml,
    import_yaml_as_workflow,
)
from app.services.workflow_marketplace.seed import seed_official_templates

__all__ = [
    "WorkflowYamlError",
    "export_workflow_to_yaml",
    "get_template",
    "import_yaml_as_workflow",
    "install_template",
    "list_templates",
    "seed_official_templates",
]
