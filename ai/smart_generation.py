"""
Smart Local-First Generation System with Cloud Fallback

This module implements the intelligent generation strategy:
1. Try local model (best available for artifact type)
2. Strict validation of output
3. Cloud fallback only if local fails validation
4. Capture cloud responses for fine-tuning
5. Apply to ALL artifacts: diagrams, code, docs, PM mode, prototypes

CRITICAL: This is the central orchestrator for all artifact generation.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime


# Enhanced Mermaid System Prompts - Precise Syntax Rules
MERMAID_ERD_PROMPT = """Generate a Mermaid ERD diagram using EXACTLY this syntax:

erDiagram
    ENTITY_NAME {
        datatype fieldName PK
        datatype fieldName FK
        datatype fieldName
    }
    ENTITY1 ||--o{ ENTITY2 : "has many"
    ENTITY1 }o--|| ENTITY2 : "belongs to"

RULES:
- Start with "erDiagram" (NOT "erdiagram" or "ER Diagram")
- Entity names: PascalCase (e.g., SwapRequest, PhoneSwapOffer)
- Field syntax: type name [PK/FK/UK]
- Relationships: ||--o{, }o--||, ||--||, }o--o{
- NO generic entities (User, Phone) unless explicitly requested
- Focus on NEW feature entities from meeting notes
- Minimum 2 entities, 1 relationship

Example:
erDiagram
    SwapRequest {
        int id PK
        int fromUserId FK
        int toUserId FK
        datetime requestedAt
        string status
    }
    PhoneSwapOffer {
        int id PK
        int swapRequestId FK
        int offeredPhoneId FK
        datetime createdAt
    }
    SwapRequest ||--o{ PhoneSwapOffer : "contains"
"""

MERMAID_ARCHITECTURE_PROMPT = """Generate a Mermaid architecture/flowchart using EXACTLY this syntax:

flowchart TD
    A[Component Name]
    B[Another Component]
    A-->B
    A-->|Label|C
    B-.->D
    C==>E

RULES:
- Start with "flowchart TD" (NOT "graph TD" - that's old syntax!)
- Node syntax: ID[Display Name]
- Arrows: --> (solid), -.-> (dotted), ==> (thick)
- Labels: -->|text|
- Direction: TD (top-down), LR (left-right)
- NO generic components unless requested
- Focus on NEW feature architecture from meeting notes

Example:
flowchart TD
    UI[Phone Swap UI]
    API[Swap Request API]
    DB[(Swap Database)]
    Notif[Notification Service]
    
    UI-->|Submit Request|API
    API-->|Store|DB
    API-->|Trigger|Notif
    Notif-.->|Email|UI
"""

MERMAID_SEQUENCE_PROMPT = """Generate a Mermaid sequence diagram using EXACTLY this syntax:

sequenceDiagram
    participant A as Actor Name
    participant B as System
    A->>B: Request Message
    B-->>A: Response
    B->>+C: Activate
    C-->>-B: Deactivate

RULES:
- Start with "sequenceDiagram"
- Participants: "participant ID as Display Name"
- Messages: ->> (solid), -->> (dashed)
- Activation: ->>+ (activate), -->>- (deactivate)
- Focus on NEW feature flows from meeting notes

Example:
sequenceDiagram
    participant U as User
    participant UI as Swap Modal
    participant API as Swap API
    participant DB as Database
    
    U->>UI: Click "Request Swap"
    UI->>API: POST /swap-requests
    API->>DB: INSERT swap_request
    DB-->>API: Success
    API-->>UI: 201 Created
    UI-->>U: Show Confirmation
"""

HTML_PROTOTYPE_PROMPT = """Generate a complete, interactive HTML prototype using EXACTLY this structure:

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feature Name</title>
    <style>
        /* Modern, clean CSS */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        /* More styles here */
    </style>
</head>
<body>
    <!-- Main content based on feature from meeting notes -->
    <div class="container">
        <h1>Feature Title</h1>
        <!-- Interactive elements -->
    </div>
    
    <script>
        // Interactive JavaScript based on feature requirements
        document.addEventListener('DOMContentLoaded', function() {
            // Event handlers, form validation, etc.
        });
    </script>
</body>
</html>

CRITICAL RULES:
1. MUST include: <!DOCTYPE html>, <html>, <head>, <body> tags
2. MUST include: <meta charset>, <meta viewport>, <title>
3. NO Mermaid syntax inside HTML (no <sequenceDiagram>, no erDiagram)
4. NO placeholder comments like "<!-- Add more fields -->" or "// TODO"
5. NO generic templates - build SPECIFIC UI for the feature in meeting notes
6. Use inline CSS in <style> tag (no external files)
7. Use inline JavaScript in <script> tag (no external files)
8. Make it INTERACTIVE (buttons work, forms validate, modals open/close)
9. Use modern CSS (flexbox, grid, CSS variables)
10. Include responsive design (mobile-friendly)

FEATURE FOCUS:
- Read the meeting notes carefully
- Identify the SPECIFIC feature being requested
- Build UI components for THAT feature only
- Use feature-specific labels, placeholders, button text
- Example: If notes say "phone swap", build swap request form, NOT generic user form

BAD EXAMPLE (Generic, has Mermaid):
<div>
    <sequenceDiagram>...</sequenceDiagram>  ❌ WRONG!
    <form>
        <input placeholder="Name">  ❌ Too generic!
    </form>
</div>

GOOD EXAMPLE (Specific to phone swap feature):
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phone Swap Request</title>
    <style>
        .swap-modal { 
            max-width: 500px; 
            margin: 50px auto; 
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }
        button { width: 100%; padding: 14px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="swap-modal">
        <h2>Request Phone Swap</h2>
        <form id="swapForm">
            <div class="form-group">
                <label for="currentPhone">Your Current Phone</label>
                <select id="currentPhone" required>
                    <option value="">Select your phone...</option>
                    <option value="iphone14">iPhone 14 Pro</option>
                    <option value="samsung">Samsung Galaxy S23</option>
                </select>
            </div>
            <div class="form-group">
                <label for="desiredPhone">Phone You Want</label>
                <select id="desiredPhone" required>
                    <option value="">Select desired phone...</option>
                    <option value="iphone15">iPhone 15 Pro Max</option>
                    <option value="pixel">Google Pixel 8</option>
                </select>
            </div>
            <div class="form-group">
                <label for="reason">Reason for Swap</label>
                <input type="text" id="reason" placeholder="e.g., Need better camera" required>
            </div>
            <button type="submit">Submit Swap Request</button>
        </form>
        <div id="confirmation" style="display:none; margin-top:20px; padding:15px; background:#d4edda; border-radius:8px;">
            ✅ Swap request submitted successfully!
        </div>
    </div>
    
    <script>
        document.getElementById('swapForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate
            const currentPhone = document.getElementById('currentPhone').value;
            const desiredPhone = document.getElementById('desiredPhone').value;
            const reason = document.getElementById('reason').value;
            
            if (!currentPhone || !desiredPhone || !reason) {
                alert('Please fill in all fields');
                return;
            }
            
            if (currentPhone === desiredPhone) {
                alert('Cannot swap for the same phone model');
                return;
            }
            
            // Show confirmation
            document.getElementById('swapForm').style.display = 'none';
            document.getElementById('confirmation').style.display = 'block';
            
            // In real app: send to API
            console.log('Swap request:', { currentPhone, desiredPhone, reason });
        });
    </script>
</body>
</html>
"""


@dataclass
class GenerationResult:
    """Result of a generation attempt"""
    success: bool
    content: str
    model_used: str
    quality_score: float
    is_local: bool
    used_cloud_fallback: bool
    validation_errors: List[str]
    generation_time: float
    attempts: List[Dict[str, Any]]


@dataclass
class CloudFallbackData:
    """Data captured from cloud for fine-tuning"""
    artifact_type: str
    prompt: str
    system_message: str
    cloud_response: str
    quality_score: float
    timestamp: str
    local_model_failed: str
    meeting_notes: str = ""


class SmartGenerationOrchestrator:
    """
    Central orchestrator for all artifact generation.
    
    Strategy:
    1. Identify artifact type
    2. Select best local model for that type
    3. Generate with local model
    4. Strict validation (artifact-specific rules)
    5. If validation fails → try next local model
    6. If all local models fail → cloud fallback
    7. Save cloud responses for fine-tuning
    8. Fine-tuned models improve over time
    """
    
    def __init__(
        self,
        ollama_client,
        output_validator,
        min_quality_threshold: int = 80
    ):
        """
        Initialize smart generation orchestrator.
        
        Args:
            ollama_client: OllamaClient instance
            output_validator: OutputValidator instance
            min_quality_threshold: Minimum quality score (0-100)
        """
        self.ollama_client = ollama_client
        self.validator = output_validator
        self.min_quality_threshold = min_quality_threshold
        
        # Artifact type → Priority local models mapping
        # SUPPORTS BOTH: "erd" (old) and "mermaid_erd" (new) naming
        self.artifact_models = {
            # Diagrams (both naming conventions)
            "erd": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "mermaid_erd": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "architecture": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "mermaid_architecture": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "api_sequence": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "mermaid_sequence": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "class_diagram": ["mistral:7b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            "mermaid_class": ["mistral:7b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            "state_diagram": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "mermaid_state": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "flowchart": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "mermaid_flowchart": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "system_overview": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "data_flow": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "user_flow": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            "components_diagram": ["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            
            # HTML/Visual prototypes (use specialized code models)
            "html_diagram": ["qwen2.5-coder:14b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M", "deepseek-coder:6.7b-instruct-q4_K_M"],
            "visual_prototype": ["qwen2.5-coder:14b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M", "deepseek-coder:6.7b-instruct-q4_K_M"],
            "visual_prototype_dev": ["qwen2.5-coder:14b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M", "deepseek-coder:6.7b-instruct-q4_K_M"],
            
            # Code prototypes
            "code_prototype": ["codellama:7b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M"],
            "typescript_code": ["codellama:7b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M"],
            "csharp_code": ["codellama:7b-instruct-q4_K_M", "qwen2.5-coder:7b-instruct-q4_K_M"],
            
            # Documentation
            "jira_stories": ["llama3:8b-instruct-q4_K_M"],
            "api_docs": ["llama3:8b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            "workflows": ["llama3:8b-instruct-q4_K_M"],
            "documentation": ["llama3:8b-instruct-q4_K_M"],
            
            # PM Mode
            "pm_analysis": ["llama3:8b-instruct-q4_K_M"],
            "pm_planning": ["llama3:8b-instruct-q4_K_M"],
            "pm_tasks": ["llama3:8b-instruct-q4_K_M"],
        }
        
        # Artifact type → Validation type mapping (supports both naming conventions)
        self.validation_map = {
            # Old naming (from app)
            "erd": "ERD",
            "architecture": "ARCHITECTURE",
            "api_sequence": "SEQUENCE",
            "class_diagram": "CLASS_DIAGRAM",
            "state_diagram": "STATE_DIAGRAM",
            "flowchart": "ARCHITECTURE",
            "system_overview": "ARCHITECTURE",
            "data_flow": "ARCHITECTURE",
            "user_flow": "ARCHITECTURE",
            "components_diagram": "ARCHITECTURE",
            "html_diagram": "HTML_PROTOTYPE",
            "visual_prototype": "HTML_PROTOTYPE",
            "visual_prototype_dev": "HTML_PROTOTYPE",
            "code_prototype": "CODE_PROTOTYPE",
            "typescript_code": "CODE_PROTOTYPE",
            "csharp_code": "CODE_PROTOTYPE",
            "jira": "JIRA_STORIES",
            "jira_stories": "JIRA_STORIES",
            "api_docs": "API_DOCS",
            "workflows": "WORKFLOWS",
            "documentation": "DOCUMENTATION",
            "pm_analysis": "DOCUMENTATION",
            "pm_planning": "WORKFLOWS",
            "pm_tasks": "JIRA_STORIES",
            # New naming (mermaid_*)
            "mermaid_erd": "ERD",
            "mermaid_architecture": "ARCHITECTURE",
            "mermaid_sequence": "SEQUENCE",
            "mermaid_class": "CLASS_DIAGRAM",
            "mermaid_state": "STATE_DIAGRAM",
            "mermaid_flowchart": "ARCHITECTURE",
        }
        
        # Directory for saving cloud responses for fine-tuning
        self.finetuning_data_dir = Path("finetune_datasets/cloud_responses")
        self.finetuning_data_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[SMART_GEN] Initialized with {len(self.artifact_models)} artifact types")
        print(f"[SMART_GEN] Quality threshold: {self.min_quality_threshold}/100")
    
    async def generate(
        self,
        artifact_type: str,
        prompt: str,
        system_message: Optional[str] = None,
        cloud_fallback_fn: Optional[callable] = None,
        temperature: float = 0.2,
        meeting_notes: str = "",
        context: Dict = None,
        ui_callback: Optional[callable] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate artifact with smart local-first strategy.
        
        This is the MAIN entry point for all generation requests.
        
        Args:
            artifact_type: Type of artifact (e.g., "mermaid_erd", "code_prototype")
            prompt: Generation prompt
            system_message: System message (optional)
            cloud_fallback_fn: Cloud generation function (async callable)
            temperature: Generation temperature
            meeting_notes: Meeting notes for semantic validation
            context: Additional context dict
            ui_callback: Optional callback for UI updates (callable that takes message string)
            **kwargs: Additional arguments
            
        Returns:
            GenerationResult with content and metadata
        """
        start_time = time.time()
        attempts = []
        
        def _log(message: str, to_ui: bool = True):
            """Log to terminal and optionally to UI"""
            print(message)
            if to_ui and ui_callback:
                try:
                    ui_callback(message)
                except Exception:
                    pass  # Ignore UI callback errors
        
        _log(f"\n{'='*60}", to_ui=False)
        _log(f"[SMART_GEN] Starting generation for: {artifact_type}")
        _log(f"{'='*60}", to_ui=False)
        
        # Get priority models for this artifact type
        priority_models = self.artifact_models.get(artifact_type, ["llama3:8b-instruct-q4_K_M"])
        validation_type = self.validation_map.get(artifact_type, "DOCUMENTATION")
        
        _log(f"🎯 Using {len(priority_models)} local model(s): {', '.join(priority_models)}")
        _log(f"📋 Validation: {validation_type} | Quality threshold: {self.min_quality_threshold}/100")
        
        # Try each local model in priority order
        for i, model_name in enumerate(priority_models):
            _log(f"\n🔄 Attempt {i+1}/{len(priority_models)}: Trying {model_name}...")
            
            try:
                # Load and generate
                attempt_start = time.time()
                
                _log(f"⏳ Loading model {model_name}...", to_ui=False)
                await self.ollama_client.ensure_model_available(model_name)
                
                # Enhance system message with precise syntax rules
                enhanced_system_message = system_message or ""
                if artifact_type in ["erd", "mermaid_erd"]:
                    enhanced_system_message = MERMAID_ERD_PROMPT + "\n\n" + (system_message or "")
                elif artifact_type in ["architecture", "mermaid_architecture", "system_overview", "components_diagram"]:
                    enhanced_system_message = MERMAID_ARCHITECTURE_PROMPT + "\n\n" + (system_message or "")
                elif artifact_type in ["api_sequence", "mermaid_sequence"]:
                    enhanced_system_message = MERMAID_SEQUENCE_PROMPT + "\n\n" + (system_message or "")
                elif artifact_type in ["visual_prototype_dev", "html_diagram", "visual_prototype"]:
                    enhanced_system_message = HTML_PROTOTYPE_PROMPT + "\n\n" + (system_message or "")
                    _log(f"📝 Using enhanced HTML prototype prompt with strict validation rules")
                
                _log(f"🤖 Generating with {model_name}...")
                response = await self.ollama_client.generate(
                    model_name=model_name,
                    prompt=prompt,
                    system_message=enhanced_system_message,
                    temperature=temperature
                )
                
                attempt_time = time.time() - attempt_start
                
                if not response.success or not response.content:
                    _log(f"❌ Generation failed: {response.error_message}")
                    attempts.append({
                        "model": model_name,
                        "success": False,
                        "error": response.error_message,
                        "time": attempt_time
                    })
                    continue
                
                # Validate output
                _log(f"🔍 Validating output from {model_name}...")
                _log(f"[DEBUG] Artifact type: {artifact_type} → Validation type: {validation_type}", to_ui=False)
                
                # Import ArtifactType enum
                from ai.artifact_router import ArtifactType
                
                try:
                    validation_enum = getattr(ArtifactType, validation_type)
                    _log(f"[DEBUG] Validation enum: {validation_enum}", to_ui=False)
                except AttributeError:
                    _log(f"[ERROR] Unknown validation type: {validation_type}", to_ui=False)
                    _log(f"[ERROR] Available types: {[attr for attr in dir(ArtifactType) if not attr.startswith('_')]}", to_ui=False)
                    # Fallback to generic validation
                    validation_enum = ArtifactType.DOCUMENTATION
                
                # Prepare validation context
                validation_context = context or {}
                if meeting_notes:
                    validation_context['meeting_notes'] = meeting_notes
                
                _log(f"[DEBUG] Validation context keys: {list(validation_context.keys())}", to_ui=False)
                
                validation_result, validation_errors, quality_score = self.validator.validate(
                    validation_enum,
                    response.content,
                    validation_context
                )
                
                _log(f"📊 Quality: {quality_score}/100 (threshold: {self.min_quality_threshold})")
                
                attempt_info = {
                    "model": model_name,
                    "success": True,
                    "quality_score": quality_score,
                    "validation_errors": validation_errors,
                    "time": attempt_time
                }
                attempts.append(attempt_info)
                
                # Check if quality threshold met
                if quality_score >= self.min_quality_threshold:
                    _log(f"✅ SUCCESS! {model_name} met quality threshold ({quality_score}≥{self.min_quality_threshold})")
                    total_time = time.time() - start_time
                    
                    return GenerationResult(
                        success=True,
                        content=response.content,
                        model_used=model_name,
                        quality_score=quality_score,
                        is_local=True,
                        used_cloud_fallback=False,
                        validation_errors=[],
                        generation_time=total_time,
                        attempts=attempts
                    )
                else:
                    _log(f"⚠️ Quality too low ({quality_score} < {self.min_quality_threshold}), trying next model...")
                    if validation_errors:
                        _log(f"   Issues: {', '.join(validation_errors[:2])}", to_ui=False)
            
            except Exception as e:
                _log(f"❌ {model_name} failed: {e}")
                attempts.append({
                    "model": model_name,
                    "success": False,
                    "error": str(e),
                    "time": 0
                })
                continue
        
        # All local models failed - try cloud fallback
        _log(f"\n☁️ All local models below threshold - using cloud fallback...")
        
        if not cloud_fallback_fn:
            _log(f"❌ No cloud fallback function provided")
            total_time = time.time() - start_time
            
            # Return best local attempt if available
            best_attempt = max(
                [a for a in attempts if a.get("success") and "quality_score" in a],
                key=lambda x: x.get("quality_score", 0),
                default=None
            )
            
            if best_attempt:
                print(f"[FALLBACK] Using best local attempt: {best_attempt['model']} ({best_attempt['quality_score']}/100)")
                # Find the actual response content from the last successful attempt
                # For now, return empty since we need to refactor to store content
                return GenerationResult(
                    success=False,
                    content="",
                    model_used=best_attempt['model'],
                    quality_score=best_attempt['quality_score'],
                    is_local=True,
                    used_cloud_fallback=False,
                    validation_errors=best_attempt.get('validation_errors', []),
                    generation_time=total_time,
                    attempts=attempts
                )
            
            return GenerationResult(
                success=False,
                content="",
                model_used="none",
                quality_score=0.0,
                is_local=False,
                used_cloud_fallback=False,
                validation_errors=["All local models failed"],
                generation_time=total_time,
                attempts=attempts
            )
        
        # Try cloud fallback
        try:
            print(f"[CLOUD_FALLBACK] Calling cloud provider...")
            cloud_start = time.time()
            
            cloud_content = await cloud_fallback_fn(
                prompt=prompt,
                system_message=system_message,
                artifact_type=artifact_type,
                temperature=temperature
            )
            
            cloud_time = time.time() - cloud_start
            
            if cloud_content:
                # Validate cloud result
                from ai.artifact_router import ArtifactType
                validation_enum = getattr(ArtifactType, validation_type)
                
                validation_context = context or {}
                if meeting_notes:
                    validation_context['meeting_notes'] = meeting_notes
                
                validation_result, validation_errors, quality_score = self.validator.validate(
                    validation_enum,
                    cloud_content,
                    validation_context
                )
                
                print(f"[CLOUD_FALLBACK] Quality: {quality_score}/100")
                
                cloud_attempt = {
                    "model": "cloud_provider",
                    "success": True,
                    "quality_score": quality_score,
                    "validation_errors": validation_errors,
                    "time": cloud_time
                }
                attempts.append(cloud_attempt)
                
                # Save cloud response for fine-tuning
                await self._save_for_finetuning(
                    artifact_type=artifact_type,
                    prompt=prompt,
                    system_message=system_message or "",
                    cloud_response=cloud_content,
                    quality_score=quality_score,
                    local_model_failed=priority_models[0] if priority_models else "unknown",
                    meeting_notes=meeting_notes
                )
                
                total_time = time.time() - start_time
                
                print(f"[SUCCESS] ✅ Cloud fallback successful! Quality: {quality_score}/100")
                
                return GenerationResult(
                    success=True,
                    content=cloud_content,
                    model_used="cloud_provider",
                    quality_score=quality_score,
                    is_local=False,
                    used_cloud_fallback=True,
                    validation_errors=validation_errors,
                    generation_time=total_time,
                    attempts=attempts
                )
        
        except Exception as e:
            print(f"[ERROR] Cloud fallback failed: {e}")
            attempts.append({
                "model": "cloud_provider",
                "success": False,
                "error": str(e),
                "time": 0
            })
        
        # Complete failure
        total_time = time.time() - start_time
        print(f"[FAILURE] ❌ All generation attempts failed")
        
        return GenerationResult(
            success=False,
            content="",
            model_used="none",
            quality_score=0.0,
            is_local=False,
            used_cloud_fallback=False,
            validation_errors=["All models (local and cloud) failed"],
            generation_time=total_time,
            attempts=attempts
        )
    
    async def _save_for_finetuning(
        self,
        artifact_type: str,
        prompt: str,
        system_message: str,
        cloud_response: str,
        quality_score: float,
        local_model_failed: str,
        meeting_notes: str = ""
    ):
        """
        Save cloud response for fine-tuning dataset.
        
        This captures high-quality cloud responses that can be used to
        fine-tune local models, improving their performance over time.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{artifact_type}_{timestamp}.json"
            filepath = self.finetuning_data_dir / filename
            
            data = CloudFallbackData(
                artifact_type=artifact_type,
                prompt=prompt,
                system_message=system_message,
                cloud_response=cloud_response,
                quality_score=quality_score,
                timestamp=datetime.now().isoformat(),
                local_model_failed=local_model_failed,
                meeting_notes=meeting_notes
            )
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data.__dict__, f, indent=2, ensure_ascii=False)
            
            print(f"[FINETUNING] Saved cloud response: {filename}")
            print(f"[FINETUNING] Quality: {quality_score}/100, Failed model: {local_model_failed}")
        
        except Exception as e:
            print(f"[ERROR] Failed to save fine-tuning data: {e}")


# Global instance
_smart_generator: Optional[SmartGenerationOrchestrator] = None


def get_smart_generator(
    ollama_client,
    output_validator,
    min_quality_threshold: int = 80
) -> SmartGenerationOrchestrator:
    """Get or create global smart generation orchestrator"""
    global _smart_generator
    if _smart_generator is None:
        _smart_generator = SmartGenerationOrchestrator(
            ollama_client=ollama_client,
            output_validator=output_validator,
            min_quality_threshold=min_quality_threshold
        )
    return _smart_generator
