"""
Meeting Notes Service - Handles folder organization and AI suggestions.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Optional AI imports
try:
    from agents.universal_agent import UniversalArchitectAgent
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("UniversalArchitectAgent not available. AI suggestions will use keyword matching.")


class MeetingNotesService:
    """
    Service for managing meeting notes with AI-powered folder suggestions.
    
    Features:
    - AI-powered folder suggestions based on content analysis
    - Folder organization and management
    - Content analysis for better categorization
    """
    
    def __init__(self):
        """Initialize Meeting Notes Service."""
        self.agent = UniversalArchitectAgent() if AI_AVAILABLE else None
        logger.info("Meeting Notes Service initialized")
    
    async def suggest_folder(self, content: str) -> Dict[str, Any]:
        """
        Suggest the best folder for meeting notes content using AI.
        
        Args:
            content: Meeting notes content to analyze
        
        Returns:
            Dictionary with suggested_folder, confidence, and alternatives
        """
        if not content or len(content.strip()) < 10:
            return {
                "suggested_folder": "general",
                "confidence": 0.5,
                "alternatives": []
            }
        
        # Use AI if available for better suggestions
        if self.agent and AI_AVAILABLE:
            try:
                # Use AI to analyze content and suggest folder
                prompt = f"""Analyze the following meeting notes and suggest the most appropriate folder name.
Consider the main topic, feature, or domain discussed.

Meeting Notes:
{content[:1000]}

Respond with ONLY a single folder name (lowercase, no spaces, use underscores). Examples: authentication, api, database, frontend, backend, deployment, testing, general.

Folder name:"""
                
                # Use a lightweight model for quick suggestions
                # Try local first, then cloud if needed
                try:
                    from ai.ollama_client import OllamaClient
                    ollama = OllamaClient()
                    response = await ollama.generate(
                        model_name="llama3:8b-instruct-q4_K_M",
                        prompt=prompt,
                        system_message="You are a helpful assistant that categorizes meeting notes into appropriate folders. Respond with only the folder name.",
                        temperature=0.1
                    )
                    if response.success and response.content:
                        suggested_folder = response.content.strip().lower().replace(" ", "_")
                        # Validate folder name
                        if suggested_folder and len(suggested_folder) < 50:
                            return {
                                "suggested_folder": suggested_folder,
                                "confidence": 0.8,
                                "alternatives": []
                            }
                except Exception as e:
                    logger.debug(f"Local model suggestion failed: {e}")
                
                # Fallback to keyword matching
            except Exception as e:
                logger.warning(f"AI folder suggestion failed: {e}")
        
        # Fallback: Keyword-based matching
        keywords = {
            "authentication": ["auth", "login", "user", "password", "session", "token", "oauth", "jwt"],
            "api": ["api", "endpoint", "rest", "graphql", "route", "controller", "request", "response"],
            "database": ["database", "schema", "table", "migration", "query", "orm", "sql", "nosql"],
            "frontend": ["ui", "component", "react", "vue", "angular", "interface", "design", "ux"],
            "backend": ["server", "service", "controller", "middleware", "business logic", "handler"],
            "deployment": ["deploy", "docker", "kubernetes", "ci/cd", "infrastructure", "aws", "azure"],
            "testing": ["test", "unit", "integration", "e2e", "qa", "quality", "coverage"],
            "security": ["security", "vulnerability", "encryption", "ssl", "tls", "firewall"],
            "performance": ["performance", "optimization", "speed", "latency", "throughput", "cache"],
        }
        
        text_lower = content.lower()
        scores = {}
        
        for folder_name, folder_keywords in keywords.items():
            score = sum(1 for keyword in folder_keywords if keyword in text_lower)
            if score > 0:
                scores[folder_name] = score
        
        if scores:
            suggested_folder = max(scores, key=scores.get)
            max_score = scores[suggested_folder]
            total_keywords = len(keywords[suggested_folder])
            confidence = min(max_score / total_keywords, 1.0)
            
            # Get alternatives (top 3)
            alternatives = sorted(
                [(name, score) for name, score in scores.items() if name != suggested_folder],
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            return {
                "suggested_folder": suggested_folder,
                "confidence": confidence,
                "alternatives": [{"folder": name, "score": score} for name, score in alternatives]
            }
        else:
            return {
                "suggested_folder": "general",
                "confidence": 0.5,
                "alternatives": []
            }
    
    def get_existing_folders(self) -> List[str]:
        """Get list of existing folder names."""
        # Use centralized config to avoid circular import with API layer
        meeting_notes_dir = settings.meeting_notes_dir
        meeting_notes_dir.mkdir(parents=True, exist_ok=True)
        
        folders = []
        if meeting_notes_dir.exists():
            for folder_path in meeting_notes_dir.iterdir():
                if folder_path.is_dir():
                    folders.append(folder_path.name)
        return folders
    
    def get_notes_by_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Get all notes from a specific folder.
        
        Args:
            folder_id: The folder name/ID
            
        Returns:
            List of note dictionaries with id, name, content, etc.
        """
        # Use centralized config to avoid circular import with API layer
        meeting_notes_dir = settings.meeting_notes_dir
        meeting_notes_dir.mkdir(parents=True, exist_ok=True)
        
        folder_path = meeting_notes_dir / folder_id
        if not folder_path.exists() or not folder_path.is_dir():
            logger.warning(f"Folder not found: {folder_id}")
            return []
        
        notes = []
        # Read all .md and .txt files in the folder
        for note_file in folder_path.glob("*"):
            if note_file.suffix in [".md", ".txt"] and note_file.is_file():
                try:
                    content = note_file.read_text(encoding="utf-8")
                    notes.append({
                        "id": note_file.stem,
                        "name": note_file.name,
                        "content": content,
                        "created_at": datetime.fromtimestamp(note_file.stat().st_ctime).isoformat(),
                        "updated_at": datetime.fromtimestamp(note_file.stat().st_mtime).isoformat(),
                    })
                except Exception as e:
                    logger.error(f"Error reading note {note_file}: {e}")
                    continue
        
        return notes


# Global service instance
_meeting_notes_service: Optional[MeetingNotesService] = None

def get_service() -> MeetingNotesService:
    """Get or create global Meeting Notes Service instance."""
    global _meeting_notes_service
    if _meeting_notes_service is None:
        _meeting_notes_service = MeetingNotesService()
    return _meeting_notes_service

