from .common import (
    UUID,
    Base,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class SocialAccount(Base):
    """Cuenta de red social conectada por un tenant vía OAuth."""

    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)          # instagram | facebook | linkedin | twitter
    account_id = Column(String(255), nullable=False)        # ID devuelto por la plataforma
    account_name = Column(String(255), nullable=True)       # nombre legible (@handle o nombre de página)
    access_token = Column(Text, nullable=False)             # cifrado con TENANT_ENCRYPTION_KEY
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    posts = relationship("ScheduledPost", back_populates="social_account", cascade="all, delete-orphan")


class Campaign(Base):
    """Agrupación lógica de posts bajo un objetivo común."""

    __tablename__ = "marketing_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    posts = relationship("ScheduledPost", back_populates="campaign", cascade="all, delete-orphan")


class ScheduledPost(Base):
    """Post individual destinado a una cuenta social, programado o publicado."""

    __tablename__ = "scheduled_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True)
    social_account_id = Column(UUID(as_uuid=True), ForeignKey("social_accounts.id"), nullable=False)
    platform = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    # null = publicar inmediatamente al crear
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    # draft | scheduled | published | failed
    status = Column(String(50), nullable=False, default="draft", index=True)
    platform_post_id = Column(String(255), nullable=True)  # ID del post en la plataforma
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    campaign = relationship("Campaign", back_populates="posts")
    social_account = relationship("SocialAccount", back_populates="posts")
