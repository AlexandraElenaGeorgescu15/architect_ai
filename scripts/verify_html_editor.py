import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Add root directory for imports
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from backend.services.chat_service import get_chat_service
from backend.services.generation_service import get_service as get_gen_service
from backend.services.version_service import get_version_service
from backend.models.dto import ArtifactType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_html_editor():
    logger.info("🚀 Starting Interactive HTML Editor Verification")
    
    chat_service = get_chat_service()
    gen_service = get_gen_service()
    version_service = get_version_service()
    
    # 1. Setup Baseline
    artifact_id = "test_html_artifact"
    artifact_type = "html_prototype"
    initial_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Prototype</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
        .card { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Hello Architect!</h1>
        <p>This is a test artifact for interactive editing.</p>
        <button>Click Me</button>
    </div>
</body>
</html>"""

    logger.info("Step 1: Creating baseline artifact")
    version_service.create_version(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        content=initial_content,
        metadata={"source": "test_verification"}
    )
    
    # 2. Verify "Make Dark" (Small Change)
    logger.info("Step 2: Testing 'Make Dark' (Small change)")
    dark_mode_prompt = f"""Modify this HTML based on the user's request.

HTML:
```html
{initial_content}
```

REQUEST: "Convert to a dark theme with good contrast"

Return ONLY the complete modified HTML. No explanations or markdown."""

    dark_response = ""
    async for chunk in chat_service.chat(message=dark_mode_prompt, include_project_context=False):
        if chunk.get("type") == "complete":
            dark_response = chunk.get("content", "")
            break
    
    if not dark_response:
        logger.error("❌ Failed to get 'Make Dark' response")
        return False
    
    # Simple check for dark mode indicators
    dark_indicators = ["background-color", "color", "#", "dark"]
    has_indicators = any(ind in dark_response.lower() for ind in dark_indicators)
    
    if has_indicators:
        logger.info("✅ 'Make Dark' response contains styling indicators")
    else:
        logger.warning("⚠️ 'Make Dark' response might be missing styling indicators")
    
    # Validate extraction logic (simulating InteractivePrototypeEditor.tsx)
    def extract_html(response):
        html = response.strip()
        if "```html" in html:
            html = html.split("```html")[1].split("```")[0].strip()
        elif "```" in html:
            html = html.split("```")[1].split("```")[0].strip()
        return html

    dark_html = extract_html(dark_response)
    
    # Save the update
    logger.info("Step 2.1: Saving 'Make Dark' update")
    updated = gen_service.update_artifact(artifact_id, dark_html, {"source": "test_make_dark"})
    if updated:
        logger.info("✅ 'Make Dark' update saved successfully")
    else:
        logger.error("❌ Failed to save 'Make Dark' update")
        return False
        
    # 3. Verify "Make Pretty" (Big Change)
    logger.info("Step 3: Testing 'Make Pretty' (Big change)")
    pretty_prompt = f"""You are a professional UI/UX designer. Transform this basic HTML prototype into a beautiful, modern, polished design.

CURRENT HTML:
```html
{dark_html}
```

USER REQUEST: "Make this look professional and modern with better colors, spacing, shadows, and typography"

REQUIREMENTS:
1. Keep the same basic structure and functionality
2. Add modern styling: gradients, shadows, rounded corners, smooth transitions
3. Use a cohesive color palette
4. Add proper spacing, padding, and typography
5. Make it responsive and visually appealing

OUTPUT: Return ONLY the complete, working HTML document. No explanations."""

    pretty_response = ""
    async for chunk in chat_service.chat(message=pretty_prompt, include_project_context=False):
        if chunk.get("type") == "complete":
            pretty_response = chunk.get("content", "")
            break
            
    if not pretty_response:
        logger.error("❌ Failed to get 'Make Pretty' response")
        return False
        
    pretty_html = extract_html(pretty_response)
    
    # Check for "pretty" features
    pretty_indicators = ["box-shadow", "border-radius", "gradient", "flex", "grid", "transition"]
    found_indicators = [ind for ind in pretty_indicators if ind in pretty_html.lower()]
    
    if found_indicators:
        logger.info(f"✅ 'Make Pretty' contains modern CSS: {', '.join(found_indicators)}")
    else:
        logger.warning("⚠️ 'Make Pretty' response might lack modern CSS improvements")

    # Save the update
    logger.info("Step 3.1: Saving 'Make Pretty' update")
    updated = gen_service.update_artifact(artifact_id, pretty_html, {"source": "test_make_pretty"})
    if updated:
        logger.info("✅ 'Make Pretty' update saved successfully")
    else:
        logger.error("❌ Failed to save 'Make Pretty' update")
        return False

    # 4. Verify Versioning
    logger.info("Step 4: Verifying versioning")
    versions = version_service.get_versions(artifact_id)
    logger.info(f"Found {len(versions)} versions for {artifact_id}")
    
    if len(versions) >= 3:
        logger.info("✅ Versioning sequence verified")
    else:
        logger.error(f"❌ Versioning fail: expected at least 3, got {len(versions)}")
        return False

    logger.info("🎉 Verification Successful!")
    return True

if __name__ == "__main__":
    success = asyncio.run(verify_html_editor())
    sys.exit(0 if success else 1)
