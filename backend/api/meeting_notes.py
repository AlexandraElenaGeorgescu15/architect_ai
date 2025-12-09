"""
Meeting Notes API endpoints with folder system and AI suggestions.
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Request
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import json
from datetime import datetime

from backend.models.dto import UserPublic
from backend.core.auth import get_current_user
from backend.core.middleware import limiter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meeting-notes", tags=["Meeting Notes"])

# Storage directory
MEETING_NOTES_DIR = Path("data/meeting_notes")
MEETING_NOTES_DIR.mkdir(parents=True, exist_ok=True)


class CreateFolderRequest(BaseModel):
    name: str


class SuggestFolderRequest(BaseModel):
    content: str


@router.get("/folders", summary="List all meeting note folders")
async def list_folders(
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """List all folders containing meeting notes."""
    try:
        folders = []
        if MEETING_NOTES_DIR.exists():
            for folder_path in MEETING_NOTES_DIR.iterdir():
                if folder_path.is_dir():
                    try:
                        notes_count = len(list(folder_path.glob("*.md"))) + len(list(folder_path.glob("*.txt")))
                        folders.append({
                            "id": folder_path.name,
                            "name": folder_path.name,
                            "notes_count": notes_count,
                            "created_at": datetime.fromtimestamp(folder_path.stat().st_ctime).isoformat(),
                        })
                    except Exception as e:
                        logger.warning(f"Error reading folder {folder_path}: {e}")
                        continue
        
        logger.debug(f"📁 [MEETING_NOTES] Returning {len(folders)} folders")
        return {"success": True, "folders": folders}
    except Exception as e:
        logger.error(f"Error listing folders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list folders: {str(e)}"
        )


@router.post("/folders", summary="Create a new folder")
@limiter.limit("10/minute")
async def create_folder(
    request: Request,
    body: CreateFolderRequest,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new folder for meeting notes."""
    name = body.name
    folder_path = MEETING_NOTES_DIR / name
    if folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder '{name}' already exists"
        )
    
    folder_path.mkdir(parents=True, exist_ok=True)
    return {"success": True, "folder": {"id": name, "name": name}}


@router.get("/folders/{folder_id}/notes", summary="List notes in a folder")
async def list_notes(
    folder_id: str,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """List all meeting notes in a folder."""
    folder_path = MEETING_NOTES_DIR / folder_id
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder '{folder_id}' not found"
        )
    
    notes = []
    # Include both .md and .txt files
    for ext in ["*.md", "*.txt"]:
        for note_file in folder_path.glob(ext):
            notes.append({
                "id": note_file.stem,
                "name": note_file.name,
                "size": note_file.stat().st_size,
                "created_at": datetime.fromtimestamp(note_file.stat().st_ctime).isoformat(),
                "updated_at": datetime.fromtimestamp(note_file.stat().st_mtime).isoformat(),
            })
    
    # Sort by updated_at descending (newest first)
    notes.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {"success": True, "notes": notes}


@router.post("/upload", summary="Upload meeting notes with AI folder suggestion")
@limiter.limit("20/minute")
async def upload_meeting_notes(
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload meeting notes file.
    
    If folder_id is not provided, AI will suggest a folder based on content.
    """
    content = await file.read()
    text_content = content.decode('utf-8')
    
    # AI suggestion for folder using service
    suggested_folder = None
    if not folder_id:
        try:
            from backend.services.meeting_notes_service import get_service
            service = get_service()
            suggestion = await service.suggest_folder(text_content)
            if suggestion and suggestion.get("suggested_folder"):
                suggested_folder = suggestion["suggested_folder"]
        except Exception as e:
            logger.warning(f"AI folder suggestion failed, using keyword matching: {e}")
        
        # Fallback to keyword matching if AI unavailable
        if not suggested_folder:
            keywords = {
                "authentication": ["auth", "login", "user", "password", "session", "token"],
                "api": ["api", "endpoint", "rest", "graphql", "route", "controller"],
                "database": ["database", "schema", "table", "migration", "query", "orm"],
                "frontend": ["ui", "component", "react", "vue", "angular", "interface"],
                "backend": ["server", "service", "controller", "middleware", "business logic"],
                "deployment": ["deploy", "docker", "kubernetes", "ci/cd", "infrastructure"],
                "testing": ["test", "unit", "integration", "e2e", "qa"],
            }
            
            text_lower = text_content.lower()
            scores = {}
            for folder_name, folder_keywords in keywords.items():
                score = sum(1 for keyword in folder_keywords if keyword in text_lower)
                if score > 0:
                    scores[folder_name] = score
            
            if scores:
                suggested_folder = max(scores, key=scores.get)
            else:
                suggested_folder = "general"
    
    target_folder = folder_id or suggested_folder or "general"
    folder_path = MEETING_NOTES_DIR / target_folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = folder_path / file.filename
    file_path.write_bytes(content)
    
    return {
        "success": True,
        "note": {
            "id": file_path.stem,
            "name": file.filename,
            "folder_id": target_folder,
            "suggested_folder": suggested_folder if not folder_id else None,
        }
    }


@router.get("/notes/{note_id}", summary="Get meeting note content")
async def get_note(
    note_id: str,
    folder_id: str,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get content of a meeting note."""
    note_path = MEETING_NOTES_DIR / folder_id / f"{note_id}.md"
    if not note_path.exists():
        # Try .txt extension
        note_path = MEETING_NOTES_DIR / folder_id / f"{note_id}.txt"
    
    if not note_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{note_id}' not found in folder '{folder_id}'"
        )
    
    content = note_path.read_text(encoding='utf-8')
    
    return {
        "success": True,
        "note": {
            "id": note_id,
            "folder_id": folder_id,
            "content": content,
        }
    }


@router.post("/suggest-folder", summary="AI suggestion for folder based on content")
@limiter.limit("10/minute")
async def suggest_folder(
    request: Request,
    body: SuggestFolderRequest,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get AI suggestion for which folder a meeting note should go to.
    
    Uses AI (if available) or intelligent keyword matching to suggest
    the most appropriate folder.
    """
    from backend.services.meeting_notes_service import get_service
    
    service = get_service()
    result = await service.suggest_folder(body.content)
    
    return {
        "success": True,
        **result
    }


class MoveNoteRequest(BaseModel):
    """Request to move a note to a different folder."""
    note_id: str
    from_folder: str
    to_folder: str


class RenameRequest(BaseModel):
    """Request to rename a folder or note."""
    new_name: str


@router.post("/notes/move", summary="Move a note to a different folder")
@limiter.limit("20/minute")
async def move_note(
    request: Request,
    body: MoveNoteRequest,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Move a note from one folder to another."""
    from_folder_path = MEETING_NOTES_DIR / body.from_folder
    to_folder_path = MEETING_NOTES_DIR / body.to_folder
    
    if not from_folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source folder '{body.from_folder}' not found"
        )
    
    # Find the note file (try both .md and .txt extensions)
    note_file = None
    for ext in ['.md', '.txt']:
        potential_file = from_folder_path / f"{body.note_id}{ext}"
        if potential_file.exists():
            note_file = potential_file
            break
    
    if not note_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{body.note_id}' not found in folder '{body.from_folder}'"
        )
    
    # Create destination folder if it doesn't exist
    to_folder_path.mkdir(parents=True, exist_ok=True)
    
    # Move the file
    destination_file = to_folder_path / note_file.name
    note_file.rename(destination_file)
    
    return {
        "success": True,
        "note": {
            "id": body.note_id,
            "name": note_file.name,
            "from_folder": body.from_folder,
            "to_folder": body.to_folder,
        }
    }


@router.delete("/folders/{folder_id}", summary="Delete a folder")
@limiter.limit("10/minute")
async def delete_folder(
    request: Request,
    folder_id: str,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a folder and all its notes."""
    import shutil
    
    folder_path = MEETING_NOTES_DIR / folder_id
    
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder '{folder_id}' not found"
        )
    
    # Delete the folder and all its contents
    shutil.rmtree(folder_path)
    
    return {
        "success": True,
        "folder_id": folder_id,
        "message": f"Folder '{folder_id}' deleted successfully"
    }


@router.put("/folders/{folder_id}/rename", summary="Rename a folder")
@limiter.limit("10/minute")
async def rename_folder(
    request: Request,
    folder_id: str,
    body: RenameRequest,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Rename a folder."""
    old_folder_path = MEETING_NOTES_DIR / folder_id
    new_folder_path = MEETING_NOTES_DIR / body.new_name
    
    if not old_folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder '{folder_id}' not found"
        )
    
    if new_folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder '{body.new_name}' already exists"
        )
    
    # Rename the folder
    old_folder_path.rename(new_folder_path)
    
    return {
        "success": True,
        "old_name": folder_id,
        "new_name": body.new_name
    }


@router.delete("/folders/{folder_id}/notes/{note_id}", summary="Delete a note")
@limiter.limit("20/minute")
async def delete_note(
    request: Request,
    folder_id: str,
    note_id: str,
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a meeting note."""
    # Try both extensions
    note_file = None
    for ext in ['.md', '.txt']:
        potential_file = MEETING_NOTES_DIR / folder_id / f"{note_id}{ext}"
        if potential_file.exists():
            note_file = potential_file
            break
    
    if not note_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{note_id}' not found in folder '{folder_id}'"
        )
    
    # Delete the file
    note_file.unlink()
    
    return {
        "success": True,
        "note_id": note_id,
        "folder_id": folder_id,
        "message": f"Note '{note_id}' deleted successfully"
    }


@router.put("/folders/{folder_id}/notes/{note_id}", summary="Update note content")
@limiter.limit("20/minute")
async def update_note(
    request: Request,
    folder_id: str,
    note_id: str,
    content: str = Form(...),
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update the content of a meeting note."""
    # Try both extensions
    note_file = None
    for ext in ['.md', '.txt']:
        potential_file = MEETING_NOTES_DIR / folder_id / f"{note_id}{ext}"
        if potential_file.exists():
            note_file = potential_file
            break
    
    if not note_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{note_id}' not found in folder '{folder_id}'"
        )
    
    # Update the file content
    note_file.write_text(content, encoding='utf-8')
    
    return {
        "success": True,
        "note": {
            "id": note_id,
            "folder_id": folder_id,
            "size": len(content),
            "updated_at": datetime.now().isoformat()
        }
    }