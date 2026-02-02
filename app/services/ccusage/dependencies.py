"""CCUsage 서비스 의존성"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.external import get_db
from app.services.ccusage.service import CcusageService


def get_ccusage_service(db: Session = Depends(get_db)) -> CcusageService:
    """CCUsage 서비스 의존성"""
    return CcusageService(db)
