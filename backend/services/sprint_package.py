"""
Sprint Package Service

Batch artifact generation service for comprehensive sprint packages.
Generates complete artifact suites from meeting notes including:
ERD, Architecture, Sequence diagrams, API docs, Code prototypes,
Visual prototypes, and JIRA stories.

Artifacts are generated in dependency order and automatically linked.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from backend.models.dto import ArtifactType

logger = logging.getLogger(__name__)


class PackagePreset(str, Enum):
    """Pre-defined package configurations."""
    FULL = "full"  # All artifacts
    BACKEND = "backend"  # ERD, API docs, code prototype
    FRONTEND = "frontend"  # Visual prototype, user flow
    DOCUMENTATION = "documentation"  # All diagrams + docs
    PM = "pm"  # JIRA, workflows, estimations
    QUICK = "quick"  # ERD + Architecture + API docs


# Package presets define which artifacts to generate
PACKAGE_DEFINITIONS = {
    PackagePreset.FULL: {
        "name": "Full Sprint Package",
        "description": "Complete set of all artifacts for a feature",
        "artifacts": [
            ArtifactType.MERMAID_ERD,
            ArtifactType.MERMAID_ARCHITECTURE,
            ArtifactType.MERMAID_SEQUENCE,
            ArtifactType.API_DOCS,
            ArtifactType.CODE_PROTOTYPE,
            ArtifactType.DEV_VISUAL_PROTOTYPE,
            ArtifactType.JIRA,
        ],
        "estimated_time_minutes": 15,
    },
    PackagePreset.BACKEND: {
        "name": "Backend Package",
        "description": "Data model, API, and implementation",
        "artifacts": [
            ArtifactType.MERMAID_ERD,
            ArtifactType.MERMAID_CLASS,
            ArtifactType.API_DOCS,
            ArtifactType.CODE_PROTOTYPE,
        ],
        "estimated_time_minutes": 8,
    },
    PackagePreset.FRONTEND: {
        "name": "Frontend Package",
        "description": "UI prototype and user flows",
        "artifacts": [
            ArtifactType.DEV_VISUAL_PROTOTYPE,
            ArtifactType.MERMAID_USER_FLOW,
            ArtifactType.MERMAID_STATE,
        ],
        "estimated_time_minutes": 6,
    },
    PackagePreset.DOCUMENTATION: {
        "name": "Documentation Package",
        "description": "All diagrams and documentation",
        "artifacts": [
            ArtifactType.MERMAID_ERD,
            ArtifactType.MERMAID_ARCHITECTURE,
            ArtifactType.MERMAID_SEQUENCE,
            ArtifactType.MERMAID_COMPONENT,
            ArtifactType.MERMAID_DATA_FLOW,
            ArtifactType.API_DOCS,
        ],
        "estimated_time_minutes": 12,
    },
    PackagePreset.PM: {
        "name": "PM Package",
        "description": "Project management artifacts",
        "artifacts": [
            ArtifactType.JIRA,
            ArtifactType.WORKFLOWS,
            ArtifactType.ESTIMATIONS,
            ArtifactType.BACKLOG,
        ],
        "estimated_time_minutes": 8,
    },
    PackagePreset.QUICK: {
        "name": "Quick Start Package",
        "description": "Essential artifacts to get started",
        "artifacts": [
            ArtifactType.MERMAID_ERD,
            ArtifactType.MERMAID_ARCHITECTURE,
            ArtifactType.API_DOCS,
        ],
        "estimated_time_minutes": 5,
    },
}


@dataclass
class PackageProgress:
    """Progress update for package generation."""
    total_artifacts: int
    completed_artifacts: int
    current_artifact: str
    current_artifact_type: str
    status: str  # "generating", "completed", "failed"
    progress_percent: float
    message: str
    elapsed_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedArtifact:
    """A generated artifact in the package."""
    artifact_type: str
    content: str
    generated_at: str
    generation_time_seconds: float
    model_used: str
    validation_score: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SprintPackageResult:
    """Result of sprint package generation."""
    package_id: str
    preset: str
    meeting_notes_summary: str
    artifacts: List[GeneratedArtifact]
    total_time_seconds: float
    success_rate: float
    failed_artifacts: List[str]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["artifacts"] = [a.to_dict() if isinstance(a, GeneratedArtifact) else a for a in self.artifacts]
        return result


class SprintPackageGenerator:
    """
    Generates complete artifact packages from meeting notes.
    
    Features:
    - Pre-defined package presets (Full, Backend, Frontend, etc.)
    - Custom artifact selection
    - Progress streaming
    - Dependency-ordered generation
    - Artifact linking
    """
    
    def __init__(self):
        self.presets = PACKAGE_DEFINITIONS
        self._generation_service = None
        self._artifact_linker = None
    
    @property
    def generation_service(self):
        """Lazy load generation service."""
        if self._generation_service is None:
            from backend.services.enhanced_generation import EnhancedGenerationService
            self._generation_service = EnhancedGenerationService()
        return self._generation_service
    
    @property
    def artifact_linker(self):
        """Lazy load artifact linker."""
        if self._artifact_linker is None:
            from backend.services.artifact_linker import get_artifact_linker
            self._artifact_linker = get_artifact_linker()
        return self._artifact_linker
    
    def get_available_presets(self) -> List[Dict[str, Any]]:
        """Get list of available package presets."""
        return [
            {
                "id": preset.value,
                "name": config["name"],
                "description": config["description"],
                "artifact_count": len(config["artifacts"]),
                "estimated_time_minutes": config["estimated_time_minutes"],
                "artifacts": [a.value for a in config["artifacts"]]
            }
            for preset, config in self.presets.items()
        ]
    
    def get_preset_details(self, preset: PackagePreset) -> Dict[str, Any]:
        """Get details for a specific preset."""
        if preset not in self.presets:
            return {"error": f"Unknown preset: {preset}"}
        
        config = self.presets[preset]
        return {
            "id": preset.value,
            "name": config["name"],
            "description": config["description"],
            "artifacts": [
                {
                    "type": a.value,
                    "name": self._format_artifact_type(a),
                    "description": self._get_artifact_description(a)
                }
                for a in config["artifacts"]
            ],
            "estimated_time_minutes": config["estimated_time_minutes"]
        }
    
    async def generate_package(
        self,
        meeting_notes: str,
        preset: PackagePreset = PackagePreset.FULL,
        custom_artifacts: Optional[List[ArtifactType]] = None,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a complete sprint package.
        
        Args:
            meeting_notes: The meeting notes to generate from
            preset: Which preset to use (ignored if custom_artifacts provided)
            custom_artifacts: Custom list of artifacts (overrides preset)
            progress_callback: Optional callback for progress updates
            
        Yields:
            Progress updates and final result
        """
        start_time = datetime.now()
        package_id = f"pkg_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Determine artifacts to generate
        if custom_artifacts:
            artifacts_to_generate = custom_artifacts
            preset_name = "custom"
        else:
            config = self.presets.get(preset, self.presets[PackagePreset.FULL])
            artifacts_to_generate = config["artifacts"]
            preset_name = preset.value
        
        total = len(artifacts_to_generate)
        generated_artifacts: List[GeneratedArtifact] = []
        failed_artifacts: List[str] = []
        
        logger.info(f"Starting sprint package generation: {total} artifacts, preset={preset_name}")
        
        # Yield initial progress
        yield {
            "type": "progress",
            "data": PackageProgress(
                total_artifacts=total,
                completed_artifacts=0,
                current_artifact="",
                current_artifact_type="",
                status="starting",
                progress_percent=0.0,
                message=f"Starting {preset_name} package generation...",
                elapsed_seconds=0.0
            ).to_dict()
        }
        
        # Generate each artifact
        for idx, artifact_type in enumerate(artifacts_to_generate):
            artifact_start = datetime.now()
            current_name = self._format_artifact_type(artifact_type)
            
            # Yield progress
            elapsed = (datetime.now() - start_time).total_seconds()
            yield {
                "type": "progress",
                "data": PackageProgress(
                    total_artifacts=total,
                    completed_artifacts=idx,
                    current_artifact=current_name,
                    current_artifact_type=artifact_type.value,
                    status="generating",
                    progress_percent=(idx / total) * 100,
                    message=f"Generating {current_name} ({idx + 1}/{total})...",
                    elapsed_seconds=elapsed
                ).to_dict()
            }
            
            try:
                # Build context from previously generated artifacts
                context_additions = self._build_context_from_generated(generated_artifacts)
                enhanced_notes = f"{meeting_notes}\n\n{context_additions}" if context_additions else meeting_notes
                
                # Generate the artifact
                result = await self.generation_service.generate_with_pipeline(
                    artifact_type=artifact_type,
                    meeting_notes=enhanced_notes,
                    options={"temperature": 0.3, "max_retries": 2}
                )
                
                if result.get("content"):
                    gen_time = (datetime.now() - artifact_start).total_seconds()
                    artifact = GeneratedArtifact(
                        artifact_type=artifact_type.value,
                        content=result["content"],
                        generated_at=datetime.now().isoformat(),
                        generation_time_seconds=gen_time,
                        model_used=result.get("model_used", "unknown"),
                        validation_score=result.get("validation_score")
                    )
                    generated_artifacts.append(artifact)
                    
                    # Register with artifact linker
                    self.artifact_linker.register_artifact(
                        artifact_id=f"{package_id}_{artifact_type.value}",
                        artifact_type=artifact_type.value,
                        content=result["content"],
                        metadata={"package_id": package_id}
                    )
                    
                    logger.info(f"Generated {artifact_type.value} in {gen_time:.1f}s")
                else:
                    failed_artifacts.append(artifact_type.value)
                    logger.warning(f"Failed to generate {artifact_type.value}: empty content")
                    
            except Exception as e:
                failed_artifacts.append(artifact_type.value)
                logger.error(f"Failed to generate {artifact_type.value}: {e}")
        
        # Calculate final stats
        total_time = (datetime.now() - start_time).total_seconds()
        success_rate = len(generated_artifacts) / total if total > 0 else 0
        
        # Create summary
        notes_summary = meeting_notes[:200] + "..." if len(meeting_notes) > 200 else meeting_notes
        
        result = SprintPackageResult(
            package_id=package_id,
            preset=preset_name,
            meeting_notes_summary=notes_summary,
            artifacts=generated_artifacts,
            total_time_seconds=total_time,
            success_rate=success_rate,
            failed_artifacts=failed_artifacts,
            created_at=start_time.isoformat()
        )
        
        # Yield final result
        yield {
            "type": "progress",
            "data": PackageProgress(
                total_artifacts=total,
                completed_artifacts=len(generated_artifacts),
                current_artifact="",
                current_artifact_type="",
                status="completed",
                progress_percent=100.0,
                message=f"Package complete! Generated {len(generated_artifacts)}/{total} artifacts",
                elapsed_seconds=total_time
            ).to_dict()
        }
        
        yield {
            "type": "result",
            "data": result.to_dict()
        }
        
        logger.info(f"Sprint package complete: {len(generated_artifacts)}/{total} artifacts in {total_time:.1f}s")
    
    def _build_context_from_generated(self, generated: List[GeneratedArtifact]) -> str:
        """Build context string from previously generated artifacts."""
        if not generated:
            return ""
        
        context_parts = []
        
        for artifact in generated:
            # Add relevant context based on type
            if artifact.artifact_type == "mermaid_erd":
                context_parts.append(f"## Previously Generated ERD:\n```mermaid\n{artifact.content[:1000]}\n```")
            elif artifact.artifact_type == "mermaid_architecture":
                context_parts.append(f"## Previously Generated Architecture:\n```mermaid\n{artifact.content[:1000]}\n```")
            elif artifact.artifact_type == "api_docs":
                context_parts.append(f"## Previously Generated API Docs:\n{artifact.content[:1500]}")
            elif artifact.artifact_type == "code_prototype":
                context_parts.append(f"## Previously Generated Code Implementation (Logic to Visualize):\n{artifact.content[:2000]}")
        
        if context_parts:
            return "\n\n---\n\n".join(context_parts)
        return ""
    
    def _format_artifact_type(self, artifact_type: ArtifactType) -> str:
        """Format artifact type for display."""
        return artifact_type.value.replace("mermaid_", "").replace("_", " ").title()
    
    def _get_artifact_description(self, artifact_type: ArtifactType) -> str:
        """Get description for artifact type."""
        descriptions = {
            ArtifactType.MERMAID_ERD: "Entity-Relationship Diagram showing database structure",
            ArtifactType.MERMAID_ARCHITECTURE: "High-level system architecture diagram",
            ArtifactType.MERMAID_SEQUENCE: "Sequence diagram showing interactions",
            ArtifactType.MERMAID_CLASS: "Class diagram showing code structure",
            ArtifactType.MERMAID_STATE: "State diagram showing status transitions",
            ArtifactType.MERMAID_COMPONENT: "Component diagram showing modules",
            ArtifactType.MERMAID_FLOWCHART: "Flowchart showing process logic",
            ArtifactType.MERMAID_USER_FLOW: "User flow showing interaction paths",
            ArtifactType.MERMAID_DATA_FLOW: "Data flow showing information movement",
            ArtifactType.API_DOCS: "API documentation with endpoints",
            ArtifactType.CODE_PROTOTYPE: "Backend code implementation",
            ArtifactType.DEV_VISUAL_PROTOTYPE: "Frontend UI prototype",
            ArtifactType.JIRA: "JIRA stories with acceptance criteria",
            ArtifactType.WORKFLOWS: "Workflow documentation",
            ArtifactType.ESTIMATIONS: "Time and effort estimates",
            ArtifactType.BACKLOG: "Product backlog items",
        }
        return descriptions.get(artifact_type, f"Generate {artifact_type.value}")


# Singleton instance
_sprint_package_generator: Optional[SprintPackageGenerator] = None


def get_sprint_package_generator() -> SprintPackageGenerator:
    """Get or create sprint package generator singleton."""
    global _sprint_package_generator
    if _sprint_package_generator is None:
        _sprint_package_generator = SprintPackageGenerator()
    return _sprint_package_generator
