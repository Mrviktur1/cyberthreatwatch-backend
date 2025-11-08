from fastapi import APIRouter, WebSocket
from typing import List
import asyncio

router = APIRouter(prefix="/status", tags=["Status"])

# ======================================================
# 🌐 Active Loader Connections
# ======================================================
active_loader_connections: List[WebSocket] = []


@router.get("/")
def check_status():
    """
    Simple health check for frontend loader.
    The frontend can ping this before connecting via WebSocket.
    """
    return {"ready": True, "message": "Backend is online and responding ✅"}


@router.websocket("/ws/loader")
async def websocket_loader(websocket: WebSocket):
    """
    WebSocket endpoint for real-time backend initialization updates.
    The frontend uses this to animate the 5D CyberThreatWatch loader.
    """
    await websocket.accept()
    active_loader_connections.append(websocket)

    try:
        # Simulated system initialization steps
        steps = [
            ("Connecting to database...", 20),
            ("Loading users & roles...", 40),
            ("Loading worklogs...", 60),
            ("Checking subscriptions...", 80),
            ("Finalizing...", 95),
        ]

        for step, progress in steps:
            await websocket.send_json({"step": step, "progress": progress})
            await asyncio.sleep(0.8)  # simulate backend load delay

        # Final ready signal
        await websocket.send_json({"step": "Backend ready ✅", "progress": 100, "ready": True})

    except Exception as e:
        print(f"Loader WebSocket error: {e}")

    finally:
        if websocket in active_loader_connections:
            active_loader_connections.remove(websocket)
        await websocket.close()
