"""
WebSocket endpoints for real-time communication.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from backend.core.websocket import websocket_manager, EventType
from backend.core.auth import decode_access_token
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: str,
    token: str = Query(None, description="JWT token for authentication (optional)")
):
    """
    WebSocket endpoint for real-time updates.
    
    Supports:
    - Generation progress updates
    - Training progress updates
    - Streaming content chunks
    - Heartbeat mechanism
    
    Args:
        websocket: WebSocket connection
        room_id: Room identifier (e.g., job_id, user_id)
        token: Optional JWT token for authentication
    """
    # Authenticate if token provided
    authenticated = False
    user_data = None
    
    if token:
        user_data = decode_access_token(token)
        if user_data:
            authenticated = True
            logger.info(f"Authenticated WebSocket connection for room '{room_id}'")
        else:
            logger.warning(f"Invalid token for WebSocket connection to room '{room_id}'")
    
    # Connect with authentication status
    await websocket_manager.connect(
        websocket, 
        room_id=room_id,
        metadata={"user": user_data} if user_data else None,
        authenticated=authenticated
    )
    
    try:
        # Send connection confirmation
        await websocket_manager.send_personal_message({
            "type": "connection.established",
            "data": {
                "room_id": room_id,
                "authenticated": authenticated
            },
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        while True:
            # Receive messages from client (for bidirectional communication)
            try:
                data = await websocket.receive_text()
                
                # Parse message
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    # Handle ping/pong for connection keepalive
                    if message_type == "ping":
                        await websocket_manager.send_personal_message({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }, websocket)
                    elif message_type == "subscribe":
                        # Client wants to subscribe to additional rooms
                        additional_rooms = message.get("rooms", [])
                        for room in additional_rooms:
                            await websocket_manager.connect(websocket, room_id=room, authenticated=authenticated)
                    elif message_type == "unsubscribe":
                        # Client wants to unsubscribe from rooms
                        rooms_to_remove = message.get("rooms", [])
                        for room in rooms_to_remove:
                            if room in websocket_manager.connection_rooms.get(websocket, set()):
                                websocket_manager.active_connections.get(room, set()).discard(websocket)
                                websocket_manager.connection_rooms[websocket].discard(room)
                    else:
                        logger.debug(f"Received message from room '{room_id}': {message_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from room '{room_id}': {data}")
                    
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error processing message from room '{room_id}': {e}")
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Error processing message"},
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected from room '{room_id}'")
    except Exception as e:
        logger.error(f"WebSocket error in room '{room_id}': {e}", exc_info=True)
        websocket_manager.disconnect(websocket)

