"""
Model Office - FastAPI backend
Aggregates job/status events from workers and broadcasts to browser via WebSocket.
Mirrors pixel-agents' event-driven architecture (typed JSON events over WS).
"""
import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Model Office")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []
        self.history: list[dict[str, Any]] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        # replay history so a late-joining browser sees current state
        for evt in self.history:
            await ws.send_json(evt)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: dict[str, Any]):
        self.history.append(event)
        if len(self.history) > 500:
            self.history.pop(0)
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def reset(self):
        self.history.clear()


manager = ConnectionManager()


class Event(BaseModel):
    type: str  # workerStatus | jobCreated | jobAssigned | jobDone | speak | reset
    worker_id: str | None = None
    job_id: str | None = None
    payload: dict[str, Any] = {}


@app.post("/api/events")
async def post_event(event: Event):
    """Producers (dispatcher.py, worker.py) push status events here."""
    await manager.broadcast(event.model_dump())
    return {"ok": True}


@app.post("/api/reset")
async def reset():
    manager.reset()
    await manager.broadcast({"type": "reset", "payload": {}})
    return {"ok": True}


class TaskRequest(BaseModel):
    task: str


@app.post("/api/task")
async def submit_task(req: TaskRequest):
    """Browser posts a task here -> dispatch (routing) + run workers (real model calls),
    all in the background so the request returns immediately and the WS stream
    carries the live status."""
    asyncio.create_task(_run_task(req.task))
    return {"ok": True}


async def _run_task(task: str):
    from dispatcher import dispatch
    from worker import run_all

    subtasks = await asyncio.to_thread(dispatch, task)
    await run_all(subtasks)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive / ignore client msgs
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve the pixel-office frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8787)
