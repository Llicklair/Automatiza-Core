"""Prueba empírica: ¿los model_validator asignados a atributos _privados en
Pydantic v2 están activos o son letra muerta?

Hipótesis: en Pydantic v2, un atributo de clase cuyo nombre empieza por '_'
se trata como PrivateAttr y el model_validator NUNCA se registra → el rango de
fechas/horas no se valida → rangos invertidos son aceptados silenciosamente.

Sin BD, sin Postgres, sin fixtures de estado compartido.
Solo importamos los schemas y construimos instancias con rangos invertidos.

Semántica de las aserciones (cada test usa pytest.raises(ValidationError)):
  - Un test que PASA aquí  = validador ACTIVO (rango invertido rechazado).
  - Un test que FALLA aquí = validador MUERTO (rango invertido aceptado en
                             silencio → bug).

Resultado empírico: 8/8 pasan → los validadores están ACTIVOS. Pydantic v2
registra el model_validator aunque el atributo lleve prefijo '_'; la hipótesis
de "letra muerta" queda refutada. El test queda como red de regresión.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectTaskCreate,
    ProjectTaskUpdate,
)
from app.api.v1.schemas.crm import (
    EventCreate,
    EventUpdate,
    ReservationCreate,
    ReservationUpdate,
)

# Fechas/horas de referencia para proyectos (datetime)
START_DT = datetime(2025, 1, 10, 9, 0)
END_DT_BEFORE_START = datetime(2025, 1, 5, 9, 0)  # 5 días ANTES de start → rango invertido

# Horas de referencia para CRM (datetime, ambos required)
START_TM = datetime(2025, 3, 1, 10, 0)
END_TM_BEFORE_START = datetime(2025, 3, 1, 8, 0)  # 2 h ANTES de start → rango invertido

CLIENT_ID = uuid4()
RESOURCE_ID = uuid4()


# ---------------------------------------------------------------------------
# projects.py — 4 clases
# ---------------------------------------------------------------------------

class TestProjectCreateDateValidator:
    """ProjectCreate._validate_dates = model_validator(mode='after')(_check_date_range)"""

    def test_inverted_range_raises(self):
        """due_date < start_date debe levantar ValidationError."""
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="Test project",
                start_date=START_DT,
                due_date=END_DT_BEFORE_START,
            )


class TestProjectUpdateDateValidator:
    """ProjectUpdate._validate_dates = model_validator(mode='after')(_check_date_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            ProjectUpdate(
                start_date=START_DT,
                due_date=END_DT_BEFORE_START,
            )


class TestProjectTaskCreateDateValidator:
    """ProjectTaskCreate._validate_dates = model_validator(mode='after')(_check_date_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            ProjectTaskCreate(
                title="My task",
                start_date=START_DT,
                due_date=END_DT_BEFORE_START,
            )


class TestProjectTaskUpdateDateValidator:
    """ProjectTaskUpdate._validate_dates = model_validator(mode='after')(_check_date_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            ProjectTaskUpdate(
                start_date=START_DT,
                due_date=END_DT_BEFORE_START,
            )


# ---------------------------------------------------------------------------
# crm.py — 4 clases
# ---------------------------------------------------------------------------

class TestEventCreateRangeValidator:
    """EventCreate._validate_range = model_validator(mode='after')(_check_event_range)"""

    def test_inverted_range_raises(self):
        """end_time < start_time debe levantar ValidationError."""
        with pytest.raises(ValidationError):
            EventCreate(
                title="Meeting",
                start_time=START_TM,
                end_time=END_TM_BEFORE_START,
            )


class TestEventUpdateRangeValidator:
    """EventUpdate._validate_range = model_validator(mode='after')(_check_event_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            EventUpdate(
                start_time=START_TM,
                end_time=END_TM_BEFORE_START,
            )


class TestReservationCreateRangeValidator:
    """ReservationCreate._validate_range = model_validator(mode='after')(_check_event_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            ReservationCreate(
                client_id=CLIENT_ID,
                start_time=START_TM,
                end_time=END_TM_BEFORE_START,
            )


class TestReservationUpdateRangeValidator:
    """ReservationUpdate._validate_range = model_validator(mode='after')(_check_event_range)"""

    def test_inverted_range_raises(self):
        with pytest.raises(ValidationError):
            ReservationUpdate(
                start_time=START_TM,
                end_time=END_TM_BEFORE_START,
            )
