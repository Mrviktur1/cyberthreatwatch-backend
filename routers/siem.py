# backend/routers/siem.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from datetime import datetime

from database import get_db
from logger import logger
from supabase_client import supabase
from auth import require_roles
from models import User, RoleEnum, SIEMLog
from main import notify_admins  # ✅ Import WebSocket notifier

router = APIRouter(prefix="/siem", tags=["SIEM"])

# ======================================================
# Ingest raw SIEM log (Postgres + Supabase + WebSocket)
# ======================================================
@router.post("/ingest")
async def ingest_log(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Expected payload example:
    {
      "source": "host-01",
      "severity": "info",
      "log_ts": "2025-11-10T12:00:00Z",
      "raw": {...}  # JSON
    }
    """
    try:
        source = payload.get("source")
        severity = payload.get("severity", "info").lower()
        log_ts = payload.get("log_ts") or datetime.utcnow().isoformat()
        raw = payload.get("raw") or payload

        # -----------------------------
        # Insert into local Postgres
        # -----------------------------
        new_log = SIEMLog(
            source=source,
            severity=severity,
            timestamp=datetime.fromisoformat(log_ts),
            message=str(raw),
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)

        # -----------------------------
        # Insert into Supabase
        # -----------------------------
        insert_resp = supabase.table("siem_logs").insert({
            "source": source,
            "log_ts": log_ts,
            "severity": severity,
            "raw": raw,
            "processed": False
        }).execute()

        if hasattr(insert_resp, "error") and insert_resp.error:
            logger.error(f"Supabase ingest error: {insert_resp.error.message}")
            raise HTTPException(status_code=500, detail="Supabase ingest error")

        # -----------------------------
        # Lightweight detection rules → auto alert
        # -----------------------------
        raw_text = str(raw)
        alert_triggered = False

        if "failed password" in raw_text.lower() or "unauthorized" in raw_text.lower():
            alert_triggered = True
            supabase.table("siem_alerts").insert({
                "rule_id": None,
                "source": source,
                "severity": "high",
                "summary": "Suspicious login failure detected",
                "details": {"raw": raw}
            }).execute()

        # -----------------------------
        # 🚨 Real-Time Admin Notification via WebSocket
        # -----------------------------
        if severity in ["high", "critical"] or alert_triggered:
            await notify_admins({
                "type": "alert",
                "severity": severity.upper(),
                "source": source,
                "timestamp": log_ts,
                "summary": f"New {severity.upper()} alert from {source}",
                "details": raw
            })

        return {"status": "ok", "inserted_postgres_id": new_log.id}

    except Exception as e:
        db.rollback()
        logger.exception(f"Error ingesting log: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ======================================================
# Retrieve SIEM logs from Postgres (admin only)
# ======================================================
@router.get("/logs", response_model=List[dict])
def get_logs(limit: int = 100, severity: Optional[str] = None,
             db: Session = Depends(get_db),
             current_user=Depends(require_roles("admin"))):
    """
    Retrieve SIEM logs (admin only)
    """
    query = db.query(SIEMLog)
    if severity:
        query = query.filter(SIEMLog.severity == severity)
    logs = query.order_by(SIEMLog.timestamp.desc()).limit(limit).all()
    return [log.__dict__ for log in logs]


# ======================================================
# List latest alerts (Supabase)
# ======================================================
@router.get("/alerts")
def list_alerts(limit: int = 50, current_user: User = Depends(require_roles("admin", "soc1", "soc2", "soc3"))):
    resp = supabase.table("siem_alerts").select("*").order("created_at", desc=True).limit(limit).execute()
    if hasattr(resp, "error") and resp.error:
        raise HTTPException(status_code=500, detail="Supabase error")
    return resp.data or []


# ======================================================
# Acknowledge an alert
# ======================================================
@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, current_user: User = Depends(require_roles("admin", "soc1", "soc2", "soc3"))):
    resp = supabase.table("siem_alerts").update({"acknowledged": True}).eq("id", alert_id).execute()
    if hasattr(resp, "error") and resp.error:
        raise HTTPException(status_code=500, detail="Supabase error")
    return {"message": "Alert acknowledged"}
