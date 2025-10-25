from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.core.auth import get_current_user, require_mobile_platform
from app.schemas.respondents import RespondentCreate, RespondentResponse
from app.database.models import Respondent, User
import uuid

router = APIRouter()

@router.post("/respondents", response_model=RespondentResponse)
async def create_respondent(
    respondent_data: RespondentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    respondent = Respondent(
        guest_name=respondent_data.guest_name,
        gender=respondent_data.gender,
        age=respondent_data.age,
        height=respondent_data.height,
        weight=respondent_data.weight,
        status=respondent_data.status,
        university=respondent_data.university,
        created_by=current_user.id
    )
    
    db.add(respondent)
    db.commit()
    db.refresh(respondent)
    
    return respondent

@router.get("/respondents", response_model=List[RespondentResponse])
async def get_respondents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = db.query(Respondent).filter(Respondent.created_by == current_user.id)
    
    if search:
        query = query.filter(Respondent.guest_name.ilike(f"%{search}%"))
    
    respondents = query.order_by(Respondent.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return respondents

@router.get("/respondents/{respondent_id}", response_model=RespondentResponse)
async def get_respondent(
    respondent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    respondent = db.query(Respondent).filter(
        Respondent.id == uuid.UUID(respondent_id),
        Respondent.created_by == current_user.id
    ).first()
    
    if not respondent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Respondent not found"
        )
    
    return respondent