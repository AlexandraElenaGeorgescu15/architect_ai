"""
WebSocket manager for real-time communication.
Handles generation progress, training updates, and streaming events.
"""

from typing import Dict, Set, Optional, Callable, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
import asyncio
from datetime import datetime
from enum import Enum
import time

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""
    GENERATION_PROGRESS = "generation.progress"
    GENERATION_CHUNK = "generation.chunk"
    GENERATION_COMPLETE = "generation.complete"
    GENERATION_ERROR = "generation.error"
    TRAINING_PROGRESS = "training.progress"
    TRAINING_COMPLETE = "training.complete"
    TRAINING_ERROR = "training.error"
    JOB_STATUS = "job.status"
    HEARTBEAT = "heartbeat"


class WebSocketManager:
    """
    Manages WebSocket connections and event broadcasting.
    
    Supports:
    - Connection tracking
    - Room/namespace management
    - Event broadcasting
    - Heartbeat mechanism
    - Automatic reconnection handling
    """
    
    def __init__(self, heartbeat_interval: int = 30):
        """
        Initialize WebSocket manager.
        
        Args:
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
        """
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # room_id -> set of connections
        self.connection_rooms: Dict[WebSocket, Set[str]] = {}  # connection -> set of room_ids
        self.connection_metadata: Dict[WebSocket, Dict] = {}  # connection -> metadata
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}  # connection -> heartbeat task
        self.event_handlers: Dict[EventType, Set[Callable]] = {}  # event_type -> handlers
        self._heartbeat_running = False
    
    async def connect(
        self, 
        websocket: WebSocket, 
        room_id: str = "default", 
        metadata: Optional[Dict] = None,
        authenticated: bool = False
    ):
        """
        Accept a new WebSocket connection and add to room.
        
        Args:
            websocket: WebSocket connection
            room_id: Room identifier (e.g., job_id, user_id)
            metadata: Optional connection metadata
            authenticated: Whether connection is authenticated
        """
        await websocket.accept()
        
        # Add to room
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)
        
        # Track connection rooms
        if websocket not in self.connection_rooms:
            self.connection_rooms[websocket] = set()
        self.connection_rooms[websocket].add(room_id)
        
        # Store metadata
        self.connection_metadata[websocket] = metadata or {}
        self.connection_metadata[websocket]["connected_at"] = datetime.now().isoformat()
        self.connection_metadata[websocket]["authenticated"] = authenticated
        self.connection_metadata[websocket]["last_heartbeat"] = time.time()
        
        # Start heartbeat task
        self.heartbeat_tasks[websocket] = asyncio.create_task(
            self._heartbeat_loop(websocket)
        )
        
        logger.info(f"WebSocket connected to room '{room_id}' (total connections: {len(self.connection_rooms)})")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection from all rooms.
        
        Args:
            websocket: WebSocket connection to remove
        """
        # Cancel heartbeat task
        if websocket in self.heartbeat_tasks:
            self.heartbeat_tasks[websocket].cancel()
            del self.heartbeat_tasks[websocket]
        
        # Remove from all rooms
        if websocket in self.connection_rooms:
            for room_id in self.connection_rooms[websocket]:
                if room_id in self.active_connections:
                    self.active_connections[room_id].discard(websocket)
                    if not self.active_connections[room_id]:
                        del self.active_connections[room_id]
            del self.connection_rooms[websocket]
        
        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected (remaining connections: {len(self.connection_rooms)})")
    
    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        Heartbeat loop to keep connection alive and detect disconnections.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check if connection is still alive
                try:
                    await self.send_heartbeat(websocket)
                    self.connection_metadata[websocket]["last_heartbeat"] = time.time()
                except Exception as e:
                    logger.warning(f"Heartbeat failed for connection: {e}")
                    self.disconnect(websocket)
                    break
        except asyncio.CancelledError:
            # Task was cancelled (connection closed)
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
            self.disconnect(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to a specific connection.
        
        Args:
            message: Message dictionary
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_room(self, message: dict, room_id: str):
        """
        Broadcast message to all connections in a room.
        
        Args:
            message: Message dictionary
            room_id: Room identifier
        """
        if room_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[room_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to room '{room_id}': {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def emit_event(self, event_type: EventType, data: dict, room_id: Optional[str] = None):
        """
        Emit an event to a room or all connections.
        
        Args:
            event_type: Type of event
            data: Event data
            room_id: Optional room identifier (broadcasts to all if None)
        """
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Call registered event handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(event_type, data, room_id)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
        
        if room_id:
            await self.broadcast_to_room(message, room_id)
        else:
            # Broadcast to all connections
            for room in list(self.active_connections.keys()):
                await self.broadcast_to_room(message, room)
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """
        Register an event handler.
        
        Args:
            event_type: Event type to handle
            handler: Async handler function(event_type, data, room_id)
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = set()
        self.event_handlers[event_type].add(handler)
    
    def unregister_event_handler(self, event_type: EventType, handler: Callable):
        """
        Unregister an event handler.
        
        Args:
            event_type: Event type
            handler: Handler function to remove
        """
        if event_type in self.event_handlers:
            self.event_handlers[event_type].discard(handler)
    
    async def send_heartbeat(self, websocket: WebSocket):
        """Send heartbeat to keep connection alive."""
        await self.send_personal_message({
            "type": EventType.HEARTBEAT.value,
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    def get_connection_count(self, room_id: Optional[str] = None) -> int:
        """
        Get number of active connections.
        
        Args:
            room_id: Optional room identifier
            
        Returns:
            Number of connections
        """
        if room_id:
            return len(self.active_connections.get(room_id, set()))
        return len(self.connection_rooms)
    
    async def emit_generation_progress(
        self,
        job_id: str,
        progress: float,
        message: str = "",
        quality_prediction: Optional[Dict[str, Any]] = None,
    ):
        """Emit generation progress event."""
        await self.emit_event(
            EventType.GENERATION_PROGRESS,
            {
                "job_id": job_id,
                "progress": progress,
                "message": message,
                "quality_prediction": quality_prediction,
            },
            room_id=job_id
        )
    
    async def emit_generation_chunk(self, job_id: str, chunk: str, progress: float):
        """Emit generation chunk event (streaming)."""
        await self.emit_event(
            EventType.GENERATION_CHUNK,
            {
                "job_id": job_id,
                "chunk": chunk,
                "progress": progress
            },
            room_id=job_id
        )
    
    async def emit_generation_complete(self, job_id: str, artifact_id: str, validation_score: float, is_valid: bool):
        """Emit generation complete event."""
        await self.emit_event(
            EventType.GENERATION_COMPLETE,
            {
                "job_id": job_id,
                "artifact_id": artifact_id,
                "validation_score": validation_score,
                "is_valid": is_valid
            },
            room_id=job_id
        )
    
    async def emit_generation_error(self, job_id: str, error: str):
        """Emit generation error event."""
        await self.emit_event(
            EventType.GENERATION_ERROR,
            {
                "job_id": job_id,
                "error": error
            },
            room_id=job_id
        )
    
    async def emit_training_progress(self, job_id: str, progress: float, epoch: Optional[int] = None, loss: Optional[float] = None):
        """Emit training progress event."""
        await self.emit_event(
            EventType.TRAINING_PROGRESS,
            {
                "job_id": job_id,
                "progress": progress,
                "epoch": epoch,
                "loss": loss
            },
            room_id=job_id
        )
    
    async def emit_training_complete(self, job_id: str, model_name: str, final_loss: float):
        """Emit training complete event."""
        await self.emit_event(
            EventType.TRAINING_COMPLETE,
            {
                "job_id": job_id,
                "model_name": model_name,
                "final_loss": final_loss
            },
            room_id=job_id
        )
    
    async def emit_training_error(self, job_id: str, error: str):
        """Emit training error event."""
        await self.emit_event(
            EventType.TRAINING_ERROR,
            {
                "job_id": job_id,
                "error": error
            },
            room_id=job_id
        )


# Global WebSocket manager instance
websocket_manager = WebSocketManager()

