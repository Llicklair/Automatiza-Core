from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OpportunityBase(BaseModel):
    client_id: UUID
    title: str
    expected_value: float = 0.0
    stage: str = "new"

class OpportunityCreate(OpportunityBase):
    pass

class OpportunityUpdate(BaseModel):
    title: str | None = None
    expected_value: float | None = None
    stage: str | None = None

class OpportunityResponse(OpportunityBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ---- Nuevo: Expansión CRM ----

class ActivityBase(BaseModel):
    client_id: UUID | None = None
    opportunity_id: UUID | None = None
    type: str
    description: str
    metadata_json: dict | None = {}

class ActivityCreate(ActivityBase):
    pass

class ActivityResponse(ActivityBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    type: str = "meeting"
    location_or_link: str | None = None
    client_id: UUID | None = None

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReservationBase(BaseModel):
    client_id: UUID
    resource_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    status: str = "pending"
    notes: str | None = None

class ReservationCreate(ReservationBase):
    pass

class ReservationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

class ReservationResponse(ReservationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    type: str | None = None
    location_or_link: str | None = None
    client_id: UUID | None = None
