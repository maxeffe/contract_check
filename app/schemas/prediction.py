from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal

class PredictionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    document_text: str
    filename: Optional[str] = None
    language: Optional[str] = "UNKNOWN"
    model_name: Optional[str] = "default_model"
    summary_depth: Optional[str] = "BULLET"

class RiskClauseResponse(BaseModel):
    id: int
    clause_text: str
    risk_level: str
    explanation: Optional[str] = None

class MLJobResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    id: int
    document_id: int
    model_id: int
    status: str
    summary_depth: str
    used_credits: Decimal
    summary_text: Optional[str] = None
    risk_score: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    risk_clauses: List[RiskClauseResponse] = []

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    pages: int
    language: str
    uploaded_at: datetime

class PredictionHistoryResponse(BaseModel):
    jobs: List[MLJobResponse]
    total_count: int

class PredictionJobResponse(BaseModel):
    job_id: int
    status: str
    message: str

class ModelResponse(BaseModel):
    id: int
    name: str
    price_per_page: int
    active: bool