"""El catálogo de skills de UI/provisioning debe ser 100% ejecutable.

Antes coexistían dos catálogos divergentes (employee_crud vs agent_tools/ai_team)
y 12 de 17 skills de UI ("hr.generate_payroll", "email.send", "excel.export"…)
apuntaban a tools inexistentes: el compiler las descartaba en silencio y el
empleado IA no podía ejecutarlas pese a que la UI las ofrecía. Este test bloquea
esa regresión.
"""

from app.agents.tool_registry import get_tool_for_employee
from app.services.ai.employee_crud import _KNOWN_SKILLS, _SKILL_LABELS


def test_every_ui_skill_resolves_to_a_real_tool():
    """Cada clave del catálogo debe resolver a una @tool registrada."""
    unresolved = []
    for key in _SKILL_LABELS:
        try:
            get_tool_for_employee(key)
        except KeyError:
            unresolved.append(key)
    assert not unresolved, f"Skills de UI sin tool ejecutable (fantasma): {unresolved}"


def test_known_skills_match_labels():
    """_KNOWN_SKILLS deriva de _SKILL_LABELS: employee_provisioning indexa
    _SKILL_LABELS[s] y lanzaría KeyError si hubiera una clave sin etiqueta."""
    assert set(_KNOWN_SKILLS) == set(_SKILL_LABELS)
