"""
Chat API endpoints for project-aware AI chat.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime

from backend.models.dto import ChatRequest, ChatResponse, ChatMessage
from backend.services.chat_service import get_chat_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    body: ChatRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Send a message to the AI chat.
    
    Request body:
    {
        "message": "What is the architecture of this project?",
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ],
        "include_project_context": true
    }
    """
    service = get_chat_service()
    
    try:
        # Generate response
        response_content = ""
        model_used = "unknown"
        provider = "unknown"
        
        async for chunk in service.chat(
            message=body.message,
            conversation_history=body.conversation_history,
            include_project_context=body.include_project_context,
            stream=False
        ):
            if chunk.get("type") == "complete":
                response_content = chunk.get("content", "")
                model_used = chunk.get("model", "unknown")
                provider = chunk.get("provider", "unknown")
                break
            elif chunk.get("type") == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=chunk.get("error", "Chat generation failed")
                )
        
        return ChatResponse(
            message=response_content,
            model_used=model_used,
            provider=provider,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {str(e)}"
        )


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Send a message with streaming response.
    """
    service = get_chat_service()
    
    async def generate_stream():
        """Stream chat response."""
        try:
            async for chunk in service.chat(
                message=request.message,
                conversation_history=request.conversation_history,
                include_project_context=request.include_project_context,
                stream=True
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}", exc_info=True)
            error_chunk = {
                "type": "error",
                "content": f"Error: {str(e)}",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

