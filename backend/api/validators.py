from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from backend.core.dependencies import get_current_user
from backend.services.custom_validator_service import get_custom_validator_service

router = APIRouter(prefix="/api/validators", tags=["validators"])


@router.get("/custom", response_model=List[Dict[str, Any]])
async def list_custom_validators(current_user=Depends(get_current_user)):
    service = get_custom_validator_service()
    return service.list_validators()


@router.post("/custom", response_model=Dict[str, Any])
async def create_custom_validator(
    payload: Dict[str, Any],
    current_user=Depends(get_current_user),
):
    if "rule_type" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rule_type is required")
    service = get_custom_validator_service()
    return service.add_validator(payload)


@router.delete("/custom/{validator_id}")
async def delete_custom_validator(
    validator_id: str,
    current_user=Depends(get_current_user),
):
    service = get_custom_validator_service()
    if not service.remove_validator(validator_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validator not found")
    return {"success": True}

