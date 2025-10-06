import uuid
from fastapi import FastAPI, Depends, HTTPException, Body
import socketio
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, SessionLocal

# Create tables for all table definitions of ORM module
Base.metadata.create_all(bind=engine)

# --- Optimized in-memory user tracking ---
room_to_users = {}  # room_id -> set of usernames
sid_to_user = {}    # sid -> (room_id, username)

# FastAPI app
app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi")

# wrap the Socket.IO server into an ASGI application that can be run by uvicorn
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- REST Endpoints ---

@app.post("/chatrooms")
def create_chatroom(name: str, db: Session = Depends(get_db)):
    existing_room = db.query(models.Chatroom).filter(models.Chatroom.name == name).first()
    if existing_room:
        raise HTTPException(status_code=400, detail=f"Chatroom '{name}' already exists")
    
    room = models.Chatroom(name=name)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def save_and_broadcast_message(room_id: int, sender: str, content: str):
    """Save message to DB and broadcast to Socket.IO room."""
    db = SessionLocal()
    try:
        room = db.query(models.Chatroom).filter(models.Chatroom.id == room_id).first()
        if not room:
            return None

        msg = models.Message(sender=sender, content=content, chatroom=room)
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Broadcast asynchronously
        import asyncio
        asyncio.create_task(
            sio.emit("new_message", {
                "id": msg.id,
                "room_id": room_id,
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": str(msg.timestamp),
            }, room=str(room_id))
        )
        return msg
    finally:
        db.close()


@app.post("/chatrooms/{room_id}/messages")
async def create_message(room_id: int, payload: dict = Body(...)):
    """
    Create a message via REST and broadcast to connected clients.
    Expects JSON body: {"sender": "...", "content": "..."}
    """
    sender = payload.get("sender")
    content = payload.get("content")

    if not sender or not content:
        raise HTTPException(status_code=400, detail="Missing sender or content")

    msg = save_and_broadcast_message(room_id, sender, content)
    if not msg:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    return {
        "id": msg.id,
        "room_id": room_id,
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": str(msg.timestamp),
    }


@app.get("/chatrooms/{room_id}/messages")
def fetch_messages(room_id: int, db: Session = Depends(get_db)):
    room = db.query(models.Chatroom).filter(models.Chatroom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    return room.messages


@app.get("/chatrooms/{room_id}/users")
async def get_users_in_room(room_id: int):
    room_id = str(room_id)
    users = list(room_to_users.get(room_id, []))
    return {"room_id": room_id, "user_count": len(users), "users": users}


@app.get("/chatrooms")
def list_chatrooms(db: Session = Depends(get_db)):
    """
    List all chatrooms in the database
    """
    rooms = db.query(models.Chatroom).all()
    return [
        {"id": room.id, "name": room.name} for room in rooms
    ]

# --- Socket.IO Events ---

@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")


@sio.event
async def disconnect(sid):
    user = sid_to_user.pop(sid, None)
    if user:
        room_id, username = user
        if room_id in room_to_users:
            room_to_users[room_id].discard(username)
            if not room_to_users[room_id]:
                del room_to_users[room_id]
        print(f"Client {sid} disconnected from room {room_id}")
        await sio.emit("user_left", {"sid": sid, "username": username}, room=room_id)


@sio.event
async def join_room(sid, data):
    room_id = str(data.get("room_id"))
    username = data.get("username", f"user_{sid[:5]}")  # optional username

    sid_to_user[sid] = (room_id, username)
    if room_id not in room_to_users:
        room_to_users[room_id] = set()
    room_to_users[room_id].add(username)

    await sio.enter_room(sid, room_id)
    await sio.emit(
        "user_joined",
        {"sid": sid, "username": username},
        room=room_id
    )


@sio.event
async def send_message(sid, data):
    room_id = int(data.get("room_id"))
    sender = data.get("sender")
    message = data.get("message")

    msg = save_and_broadcast_message(room_id, sender, message)
    if not msg:
        await sio.emit("error", {"error": "Chatroom not found"}, to=sid)
