"""Persistencia del consumo LLM agregado por tenant/mes/agente/proveedor.

Snapshot de `services/llm_usage_tracker` (dict en memoria). El tracker sigue
siendo la fuente viva; esta tabla guarda valores ABSOLUTOS por
(tenant, month, agent, provider) que se vuelcan al apagar / periódicamente y se
recargan al arrancar, para que el dashboard de consumo sobreviva a los reinicios
del backend de escritorio.
"""

from sqlalchemy import UniqueConstraint

from .common import (
    UUID,
    Base,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    utcnow,
    uuid,
)


class LlmUsageMonthly(Base):
    __tablename__ = "llm_usage_monthly"
    __table_args__ = (UniqueConstraint("tenant_id", "month", "agent", "provider", name="uq_llm_usage_monthly_dims"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month = Column(String(7), nullable=False, index=True)  # "YYYY-MM"
    agent = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    calls = Column(Integer, nullable=False, default=0)
    tokens_in = Column(BigInteger, nullable=False, default=0)
    tokens_out = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
