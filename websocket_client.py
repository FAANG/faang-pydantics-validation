import asyncio
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")

clients: Set[WebSocket] = set()


async def broadcast(message: dict) -> None:
    data = json.dumps(
        {**message, "ts": datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False,
    )
    dead = []
    for ws in list(clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    fd, tmp = tempfile.mkstemp(prefix="up_", suffix=f"_{file.filename or 'file'}")
    os.close(fd)

    size = 0
    with open(tmp, "wb") as out:
        while True:
            chunk = await file.read(1 << 20)  # 1 MiB
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)
    await file.close()

    asyncio.create_task(process_file(tmp, file.filename or "file", size))
    return {"status": "queued", "filename": file.filename, "size": size}


async def process_file(path: str, filename: str, total: int):
    try:
        await broadcast({"type": "status", "msg": f"Started {filename}", "size": total})
        sha, done = hashlib.sha256(), 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                sha.update(chunk)
                done += len(chunk)
                pct = round(done * 100 / max(1, total), 1)
                await broadcast({"type": "progress", "percent": pct, "processed": done})
                await asyncio.sleep(0)
        await broadcast({"type": "result", "filename": filename, "size": total, "sha256": sha.hexdigest()})
        await broadcast({"type": "status", "msg": "Done"})
    except Exception as e:
        await broadcast({"type": "error", "detail": str(e)})
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
