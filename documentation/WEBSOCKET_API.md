# WebSocket API Documentation

## Overview

The Architect.AI backend provides WebSocket support for real-time communication, including generation progress, training updates, and streaming content.

## Connection

### Endpoint

```
ws://localhost:8000/ws/{room_id}?token={jwt_token}
```

**Parameters:**
- `room_id` (path): Room identifier, typically a job ID (e.g., `job_123`, `training_456`)
- `token` (query, optional): JWT token for authenticated connections

### Connection Flow

1. **Client connects** to WebSocket endpoint
2. **Server sends** `connection.established` event
3. **Client can send** messages (ping, subscribe, unsubscribe)
4. **Server sends** events as they occur
5. **Heartbeat** keeps connection alive (every 30 seconds)

### Example Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job_123?token=your_jwt_token');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

## Events

### Server → Client Events

#### `connection.established`

Sent immediately after connection is established.

```json
{
  "type": "connection.established",
  "data": {
    "room_id": "job_123",
    "authenticated": true
  },
  "timestamp": "2025-11-18T14:30:00Z"
}
```

#### `generation.progress`

Emitted during artifact generation to show progress.

```json
{
  "type": "generation.progress",
  "data": {
    "job_id": "job_123",
    "progress": 45.5,
    "message": "Generating ERD diagram..."
  },
  "timestamp": "2025-11-18T14:30:15Z"
}
```

**Fields:**
- `job_id`: Generation job identifier
- `progress`: Progress percentage (0-100)
- `message`: Optional status message

#### `generation.chunk`

Emitted when a chunk of content is generated (streaming).

```json
{
  "type": "generation.chunk",
  "data": {
    "job_id": "job_123",
    "chunk": "erDiagram\n    User {",
    "progress": 10.0
  },
  "timestamp": "2025-11-18T14:30:16Z"
}
```

**Fields:**
- `job_id`: Generation job identifier
- `chunk`: Generated content chunk
- `progress`: Current progress percentage

#### `generation.complete`

Emitted when generation completes successfully.

```json
{
  "type": "generation.complete",
  "data": {
    "job_id": "job_123",
    "artifact_id": "artifact_456",
    "validation_score": 85.5,
    "is_valid": true
  },
  "timestamp": "2025-11-18T14:30:30Z"
}
```

**Fields:**
- `job_id`: Generation job identifier
- `artifact_id`: Generated artifact identifier
- `validation_score`: Validation score (0-100)
- `is_valid`: Whether artifact passed validation

#### `generation.error`

Emitted when generation fails.

```json
{
  "type": "generation.error",
  "data": {
    "job_id": "job_123",
    "error": "Model timeout"
  },
  "timestamp": "2025-11-18T14:30:25Z"
}
```

#### `training.progress`

Emitted during model training.

```json
{
  "type": "training.progress",
  "data": {
    "job_id": "training_789",
    "progress": 60.0,
    "epoch": 2,
    "loss": 0.15
  },
  "timestamp": "2025-11-18T15:00:00Z"
}
```

**Fields:**
- `job_id`: Training job identifier
- `progress`: Progress percentage (0-100)
- `epoch`: Current epoch (optional)
- `loss`: Current loss value (optional)

#### `training.complete`

Emitted when training completes successfully.

```json
{
  "type": "training.complete",
  "data": {
    "job_id": "training_789",
    "model_name": "codellama-7b-custom-v1",
    "final_loss": 0.12
  },
  "timestamp": "2025-11-18T15:30:00Z"
}
```

#### `training.error`

Emitted when training fails.

```json
{
  "type": "training.error",
  "data": {
    "job_id": "training_789",
    "error": "Out of memory"
  },
  "timestamp": "2025-11-18T15:15:00Z"
}
```

#### `heartbeat`

Sent periodically to keep connection alive.

```json
{
  "type": "heartbeat",
  "timestamp": "2025-11-18T14:30:45Z"
}
```

#### `pong`

Response to client `ping` message.

```json
{
  "type": "pong",
  "timestamp": "2025-11-18T14:30:46Z"
}
```

#### `error`

General error message.

```json
{
  "type": "error",
  "data": {
    "message": "Error processing message"
  },
  "timestamp": "2025-11-18T14:30:47Z"
}
```

### Client → Server Messages

#### `ping`

Keepalive message. Server responds with `pong`.

```json
{
  "type": "ping"
}
```

#### `subscribe`

Subscribe to additional rooms.

```json
{
  "type": "subscribe",
  "rooms": ["job_124", "job_125"]
}
```

#### `unsubscribe`

Unsubscribe from rooms.

```json
{
  "type": "unsubscribe",
  "rooms": ["job_124"]
}
```

## Usage Examples

### Generation Progress Tracking

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job_123');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'generation.progress':
      updateProgressBar(message.data.progress);
      showStatus(message.data.message);
      break;
      
    case 'generation.chunk':
      appendToOutput(message.data.chunk);
      break;
      
    case 'generation.complete':
      showArtifact(message.data.artifact_id);
      break;
      
    case 'generation.error':
      showError(message.data.error);
      break;
  }
};
```

### Training Progress Tracking

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/training_789');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'training.progress') {
    updateTrainingProgress(
      message.data.progress,
      message.data.epoch,
      message.data.loss
    );
  }
};
```

### Multi-Room Subscription

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job_123');

ws.onopen = () => {
  // Subscribe to additional rooms
  ws.send(JSON.stringify({
    type: 'subscribe',
    rooms: ['job_124', 'job_125']
  }));
};
```

## Reconnection

The WebSocket client should implement automatic reconnection with exponential backoff:

```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connect() {
  const ws = new WebSocket('ws://localhost:8000/ws/job_123');
  
  ws.onclose = () => {
    if (reconnectAttempts < maxReconnectAttempts) {
      const delay = Math.pow(2, reconnectAttempts) * 1000; // Exponential backoff
      setTimeout(() => {
        reconnectAttempts++;
        connect();
      }, delay);
    }
  };
  
  ws.onopen = () => {
    reconnectAttempts = 0; // Reset on successful connection
  };
}
```

## Authentication

For authenticated connections, include JWT token in query string:

```
ws://localhost:8000/ws/job_123?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Authenticated connections have access to user-specific data and may receive additional events.

## Error Handling

All errors are sent as `error` events:

```json
{
  "type": "error",
  "data": {
    "message": "Error description"
  },
  "timestamp": "2025-11-18T14:30:00Z"
}
```

Common errors:
- **Invalid token**: Token provided but invalid
- **Room not found**: Room ID doesn't exist
- **Permission denied**: Insufficient permissions for room
- **Connection timeout**: Connection idle too long

## Best Practices

1. **Always handle reconnection**: Implement automatic reconnection logic
2. **Use ping/pong**: Send periodic ping messages to detect dead connections
3. **Subscribe to specific rooms**: Only subscribe to rooms you need
4. **Handle errors gracefully**: Display user-friendly error messages
5. **Unsubscribe when done**: Clean up subscriptions when leaving pages
6. **Use authentication**: Include JWT token for authenticated features

## Rate Limiting

WebSocket connections are subject to rate limiting:
- **Connection rate**: 10 connections per minute per IP
- **Message rate**: 100 messages per minute per connection
- **Heartbeat**: Automatic, no rate limit

## Security

- **Use HTTPS/WSS in production**: Always use secure WebSocket connections
- **Validate tokens**: Server validates JWT tokens on connection
- **Room isolation**: Users can only access rooms they have permission for
- **Input validation**: All client messages are validated



