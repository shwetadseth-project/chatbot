# Real-Time Chatroom Backend (FastAPI + Socket.IO + In-Memory SQLite)

This is a simple real-time chatroom backend using FastAPI, Socket.IO, and SQLAlchemy.
All data is stored in a SQLite database file (`chat.db`), which persists across server restarts.

---

## 🚀 Run the server

```bash
poetry env activate
poetry install
uvicorn app.app:socket_app --reload
```

## 🧪 Run Tests

```bash
poetry run pytest test_events.py
```

---

## 📝 REST API Endpoints

The backend provides the following REST API endpoints:

### 1. Create Chatroom

**POST** `/chatrooms`

* **Description:** Create a new chatroom.
* **Request Body:** JSON with the chatroom name:

```json
{
  "name": "Room Name"
}
```

* **Response:** Chatroom object.
* **Error:** Returns a message if the chatroom already exists.

---

### 2. Fetch Messages in a Chatroom

**GET** `/chatrooms/{room_id}/messages`

* **Description:** Retrieve all messages from a specific chatroom.
* **Response:** List of messages with sender and timestamp.

---

### 3. Get Users in a Chatroom

**GET** `/chatrooms/{room_id}/users`

* **Description:** Get a list of currently connected users in a chatroom.
* **Response:** JSON object with user details.

---

### 4. List All Chatrooms

**GET** `/chatrooms`

* **Description:** Get a list of all available chatrooms.
* **Response:** List of chatroom objects.

---

### 5. Send a Message

**POST** `/chatrooms/{room_id}/messages`

* **Description:** Send a message to a chatroom.
* **Request Body:** JSON with the sender name and message:

```json
{
  "sender": "User Name",
  "message": "Hello everyone!"
}
```

* **Response:** Message object with timestamp.

---

### 📂 Bruno Collection

A Bruno collection named `chatroom_rest_api_collection` has been added for testing these REST API endpoints.


## 🔄 Real-Time Features (Socket.IO)

* Clients connect using Socket.IO for real-time updates.
* **Events:**

  * `join_room`: Join a specific chatroom
  * `send_message`: Broadcast a message to the room
  * `user_joined`: Notify when a user joins
  * `new_message`: Notify when a message is sent

---

## 📝 Notes

* SQLite database persists across restarts (`chat.db`).
* Socket.IO enables real-time chat between connected clients in rooms.
