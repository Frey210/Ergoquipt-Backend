from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict, Any
import json
import uuid

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages
            message_data = json.loads(data)
            
            # You can add message handling logic here
            # For example: session updates, real-time data, etc.
            
            # Echo back for now
            await manager.send_personal_message(f"Message received: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Utility function to broadcast session updates
async def broadcast_session_update(session_id: uuid.UUID, update_type: str, data: Dict[str, Any]):
    message = {
        "type": "session_update",
        "session_id": str(session_id),
        "update_type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(json.dumps(message))

# Utility function to broadcast trial data
async def broadcast_trial_data(session_id: uuid.UUID, trial_data: Dict[str, Any]):
    message = {
        "type": "trial_data",
        "session_id": str(session_id),
        "trial_data": trial_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(json.dumps(message))