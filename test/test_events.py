import asyncio
import socketio
import aiohttp
import pytest

BASE_URL = "http://localhost:8000"
ROOM_ID = 1  # Using integer to match your FastAPI endpoint

# --- Helper to attach events dynamically ---
def attach_events(sio, client_name):
    @sio.event
    def connect():
        print(f"{client_name} connected")

    @sio.event
    def disconnect():
        print(f"{client_name} disconnected")

    @sio.event
    def user_joined(data):
        print(f"{client_name} sees user joined:", data)

    @sio.event
    def user_left(data):
        print(f"{client_name} sees user left:", data)

    @sio.event
    def new_message(data):
        print(f"{client_name} got message:", data)


@pytest.mark.asyncio
async def test_user_sends_message():
    sio1 = socketio.AsyncClient()
    sio2 = socketio.AsyncClient()
    attach_events(sio1, "Client1")
    attach_events(sio2, "Client2")

    await sio1.connect(BASE_URL)
    await sio2.connect(BASE_URL)

    # Both clients join the same room
    await sio1.emit("join_room", {"room_id": ROOM_ID, "username": "Client1"})
    await sio2.emit("join_room", {"room_id": ROOM_ID, "username": "Client2"})
    await asyncio.sleep(0.2)

    # Send messages
    await sio1.emit("send_message", {"room_id": ROOM_ID, "sender": "Client1", "message": "Hello everyone!"})
    await sio2.emit("send_message", {"room_id": ROOM_ID, "sender": "Client2", "message": "Hi Client1!"})
    await asyncio.sleep(0.2)

    await sio1.disconnect()
    await sio2.disconnect()


@pytest.mark.asyncio
async def test_user_disconnect():
    sio1 = socketio.AsyncClient()
    sio2 = socketio.AsyncClient()
    attach_events(sio1, "Client1")
    attach_events(sio2, "Client2")

    await sio1.connect(BASE_URL)
    await sio2.connect(BASE_URL)

    # Both clients join the same room
    await sio1.emit("join_room", {"room_id": ROOM_ID, "username": "Client1"})
    await sio2.emit("join_room", {"room_id": ROOM_ID, "username": "Client2"})
    await asyncio.sleep(0.2)  # let server process

    # Check users via REST API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/chatrooms/{ROOM_ID}/users") as resp:
            data = await resp.json()
            assert data["user_count"] == 2
            print("Users before disconnect:", data["users"])

    # Disconnect Client2
    await sio2.disconnect()
    await asyncio.sleep(0.2)

    # Check users again
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/chatrooms/{ROOM_ID}/users") as resp:
            data = await resp.json()
            assert data["user_count"] == 1
            print("Users after Client2 disconnect:", data["users"])

    await sio1.disconnect()
    await asyncio.sleep(0.1)
