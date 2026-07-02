"""Registro de alertas automáticas disparadas por el scheduler."""

from .common import UUID, Base, Boolean, Column, DateTime, ForeignKey, String, utcnow, uuid


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type = Column(String(50), nullable=False)  # overdue_invoice | due_soon_invoice | low_stock | pending_payroll
    entity_id = Column(String(100), nullable=False)  # UUID del objeto alertado
    entity_label = Column(String(255), nullable=False)  # texto legible para la UI
    severity = Column(String(20), nullable=False, default="warning")  # info | warning | error
    sent_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    notified_ws = Column(Boolean, nullable=False, default=False)
