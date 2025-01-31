from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio

app = FastAPI()

reminders = {}

class Reminder(BaseModel):
    title: str
    description: str
    creation_date: datetime
    reminder_datetime: datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get_home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reminder App</title>
    </head>
    <body>
        <h1>Reminder App</h1>
        <form id="reminder-form">
            <label for="title">Title:</label><br>
            <input type="text" id="title" name="title"><br>
            <label for="description">Description:</label><br>
            <input type="text" id="description" name="description"><br>
            <label for="creation_date">Creation Date:</label><br>
            <input type="datetime-local" id="creation_date" name="creation_date"><br>
            <label for="reminder_datetime">Reminder Date and Time:</label><br>
            <input type="datetime-local" id="reminder_datetime" name="reminder_datetime"><br><br>
            <button type="button" onclick="addReminder()">Add Reminder</button>
        </form>

        <h2>Real-Time Notifications</h2>
        <ul id="notifications"></ul>

        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");

            ws.onmessage = function(event) {
                const notifications = document.getElementById("notifications");
                const newNotification = document.createElement("li");
                newNotification.textContent = event.data;
                notifications.appendChild(newNotification);
            };

            function addReminder() {
                const title = document.getElementById("title").value;
                const description = document.getElementById("description").value;
                const creationDate = document.getElementById("creation_date").value;
                const reminderDatetime = document.getElementById("reminder_datetime").value;

                fetch("/add_reminder/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        title: title,
                        description: description,
                        creation_date: creationDate,
                        reminder_datetime: reminderDatetime
                    })
                }).then(response => response.json())
                .then(data => {
                    alert("Reminder added successfully: " + data.id);
                }).catch(error => {
                    console.error("Error adding reminder:", error);
                });
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/add_reminder/")
async def add_reminder(reminder: Reminder):
    # Store the reminder
    reminder_id = len(reminders) + 1
    reminders[reminder_id] = reminder
    return {"message": "Reminder added successfully", "id": reminder_id}

@app.get("/get_reminders/")
async def get_reminders():
    return reminders

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def check_reminders():
    while True:
        now = datetime.now()
        due_reminders = [
            (id, reminder)
            for id, reminder in reminders.items()
            if reminder.reminder_datetime <= now
        ]
        for id, reminder in due_reminders:
            message = (
                f"Reminder Triggered! \n Title: {reminder.title} \n Description: {reminder.description}"
            )
            await manager.send_message(message)
            del reminders[id]
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_reminders())

    

