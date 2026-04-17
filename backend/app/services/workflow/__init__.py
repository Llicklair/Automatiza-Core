"""Workflow domain services — re-exports for backward compatibility."""

from app.services.workflow.activity import log_activity
from app.services.workflow.approval import cleanup_all, decide, list_pending
from app.services.workflow.service import (
    # CRUD & queries (native to service.py)
    create_workflow,
    delete_workflow,
    get_execution,
    get_execution_logs,
    get_workflow,
    list_executions,
    list_workflows,
    recent_completions,
    update_workflow,
    # Re-exported from _execution.py via service.py
    cancel_execution,
    execute_deterministic_steps,
    resume_execution,
    run_workflow,
    run_workflow_with_context,
    # Re-exported from _nlp.py via service.py
    fire_event,
    parse_natural_language,
    # Re-exported from _ui_graph.py via service.py
    generate_preview_nodes,
    plan_to_ui_graph,
)
from app.services.workflow.task import (
    cancel_task,
    cleanup_tasks,
    create_task,
    get_task,
    get_task_audit,
    list_tasks,
)
from app.services.workflow.task_dispatch import (
    cancel_task as cancel_task_dispatch,
    dispatch_node_engine,
    dispatch_orchestrator,
    dispatch_resume_node_engine,
    dispatch_resume_orchestrator,
)
from app.services.workflow.scheduler import (  # noqa: F401
    create_execution,
    create_task_for_execution,
    get_active_scheduled_workflows,
    get_last_execution,
    get_stuck_executions,
    has_active_execution,
    mark_executions_failed,
)
from app.services.workflow.task_runner import TaskRunner, task_runner

__all__ = [
    # activity
    "log_activity",
    # approval
    "list_pending",
    "decide",
    "cleanup_all",
    # service (workflow)
    "list_workflows",
    "create_workflow",
    "get_workflow",
    "update_workflow",
    "delete_workflow",
    "recent_completions",
    "get_execution",
    "list_executions",
    "get_execution_logs",
    "run_workflow",
    "run_workflow_with_context",
    "cancel_execution",
    "resume_execution",
    "parse_natural_language",
    "fire_event",
    "execute_deterministic_steps",
    "generate_preview_nodes",
    "plan_to_ui_graph",
    # task
    "create_task",
    "list_tasks",
    "get_task",
    "cancel_task",
    "cleanup_tasks",
    "get_task_audit",
    # task_dispatch
    "dispatch_orchestrator",
    "dispatch_resume_orchestrator",
    "dispatch_node_engine",
    "dispatch_resume_node_engine",
    "cancel_task_dispatch",
    # task_runner
    "TaskRunner",
    "task_runner",
]
