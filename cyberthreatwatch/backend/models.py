# ======================================================
# backend/models.py
# Async-ready SQLAlchemy Models for CyberThreatWatch
# ======================================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

# =====================================================
# 🔹 Role Enum
# =====================================================
class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    SOC1 = "soc1"
    SOC2 = "soc2"
    SOC3 = "soc3"
    STUDENT = "student"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


# =====================================================
# 🔹 User Model
# =====================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Fleet and SOC role relationships
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=True)
    soc_role_id = Column(Integer, ForeignKey("soc_roles.id"), nullable=True)

    # Relationships
    fleet = relationship("Fleet", back_populates="users")
    soc_role = relationship("SOCRole", back_populates="users")
    work_logs = relationship("WorkLog", back_populates="user", cascade="all, delete-orphan")
    actions = relationship("SensitiveAction", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


# =====================================================
# 🔹 Fleet Model (Teams for business/enterprise)
# =====================================================
class Fleet(Base):
    __tablename__ = "fleets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="fleet")


# =====================================================
# 🔹 SOC Roles Model (Enterprise)
# =====================================================
class SOCRole(Base):
    __tablename__ = "soc_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # SOC1, SOC2, SOC3, etc.
    description = Column(Text, nullable=True)

    # Relationships
    users = relationship("User", back_populates="soc_role")


# =====================================================
# 🔹 Work Log (Clock-in/Clock-out)
# =====================================================
class WorkLog(Base):
    __tablename__ = "work_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    clock_in = Column(DateTime, default=datetime.utcnow)
    clock_out = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="work_logs")


# =====================================================
# 🔹 Sensitive Actions (Screenshots, Recordings, Document Access)
# =====================================================
class SensitiveAction(Base):
    __tablename__ = "sensitive_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String, nullable=False)  # "screenshot", "recording", "document_open"
    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    alert_sent = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="actions")


# =====================================================
# 🔹 Subscription Plans (Student/Business/Enterprise)
# =====================================================
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_type = Column(String, nullable=False)  # "student", "business", "enterprise"
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscriptions")


# =====================================================
# 🔹 Audit Log (Admin Monitoring)
# =====================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # e.g., "clock_in", "screenshot_taken"
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


# =====================================================
# 🔹 SIEM Log (Security Information & Event Management)
# =====================================================
class SIEMLog(Base):
    __tablename__ = "siem_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source_ip = Column(String, nullable=False)
    destination_ip = Column(String, nullable=True)
    username = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # Low, Medium, High, Critical
    message = Column(Text, nullable=False)
    log_metadata = Column("metadata", JSON, nullable=True)  # Avoid reserved word conflict
