"""Regresión: el portal admin "ver como empleado" salía EN BLANCO.

Causa: `LeaveRequestResponse` (y `AttendanceResponse`) no llevaban
`model_config = ConfigDict(from_attributes=True)`, así que
`LeaveRequestResponse.model_validate(orm_leave)` en `_build_portal_payload`
lanzaba ValidationError → GET /portal/as/{id} daba 500 para cualquier empleado
con ≥1 solicitud de vacaciones → el front lo tragaba y el panel quedaba mudo.
"""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.api.v1.schemas.hr import AttendanceResponse, LeaveRequestResponse
from app.db.models.hr import Attendance, LeaveRequest


def _orm(model, **attrs):
    obj = model()
    for key, value in attrs.items():
        setattr(obj, key, value)
    return obj


def test_leave_request_response_validates_from_orm_instance():
    lr = _orm(
        LeaveRequest,
        id=uuid4(),
        employee_id=uuid4(),
        leave_type="vacaciones",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        status="pending",
        notes=None,
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    dto = LeaveRequestResponse.model_validate(lr)
    assert dto.leave_type == "vacaciones"
    assert dto.status == "pending"


def test_attendance_response_validates_from_orm_instance():
    att = _orm(
        Attendance,
        id=uuid4(),
        employee_id=uuid4(),
        clock_in=datetime(2026, 6, 1, 9, tzinfo=UTC),
        clock_out=None,
        date=date(2026, 6, 1),
        notes=None,
    )
    dto = AttendanceResponse.model_validate(att)
    assert dto.clock_out is None
