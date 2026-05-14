"""Metering — contadores mensuales de uso (OPS.OVR + OPS.CRON)."""

from sqlalchemy import UniqueConstraint

from .common import (
    UUID,
    Base,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
)


class InteractionUsage(Base):
    """Contador mensual de interacciones con `run_agent()` por tenant.

    Incrementa 1 por cada invocación de un agente LLM (no por tool_call interno
    y no por cron — esos van en `CronExecutionUsage`).

    Política de overage (OPS.OVR):
      - Banner suave al llegar a 450 (90% del cupo Pro de 500).
      - Banner amarillo + activación de overage al llegar a 500.
      - Cobro de 0,05€ + IVA por interacción adicional.
      - Hard cap a 1000 interacciones extra/mes — > requiere confirmación.
      - **Nunca bloquea operaciones fiscales** — la facturación y presentación
        AEAT siguen siendo viables aunque se supere el cap.
    """

    __tablename__ = "interaction_usage"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", "month", name="uq_interaction_usage_tenant_period"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    overage_count = Column(Integer, nullable=False, default=0)
    last_recorded_at = Column(DateTime(timezone=True), nullable=True)


class CronExecutionUsage(Base):
    """Contador mensual de ejecuciones de workflows cron por tenant.

    Caps escalados por tier (OPS.CRON):
      - Pro: 200/mes flat.
      - Gestoría: 200 × N empresas activas hasta tope 2000/mes.

    Si se alcanza el cap, las ejecuciones cron se pausan hasta el siguiente mes.
    El usuario puede ejecutar el workflow manualmente (no cuenta para este cap).
    """

    __tablename__ = "cron_execution_usage"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", "month", name="uq_cron_usage_tenant_period"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    last_recorded_at = Column(DateTime(timezone=True), nullable=True)
