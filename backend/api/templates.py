from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.dependencies import get_current_user
from backend.models.dto import (
    TemplateDTO,
    TemplateApplyRequest,
    TemplateApplyResponse,
)
from backend.services.template_service import get_template_service

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/", response_model=list[TemplateDTO])
async def list_templates(current_user=Depends(get_current_user)):
    """Return available artifact templates."""
    service = get_template_service()
    return service.list_templates()


@router.post("/apply", response_model=TemplateApplyResponse)
async def apply_template(
    request: TemplateApplyRequest,
    current_user=Depends(get_current_user),
):
    """Return meeting notes + artifact bundle for the selected template."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Applying template: {request.template_id}")
    
    service = get_template_service()
    template = service.get_template(request.template_id)
    
    if not template:
        logger.error(f"Template not found: {request.template_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    logger.info(f"Template applied successfully: {template.get('name')}")
    return TemplateApplyResponse(
        template=template,
        meeting_notes=template["meeting_notes"],
        artifact_types=template["recommended_artifacts"],
    )

