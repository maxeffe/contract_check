from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal

class PredictionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    document_text: str = Field(..., min_length=10, max_length=1000000, description="Текст документа (10-1000000 символов)")
    filename: Optional[str] = Field(None, max_length=255, description="Имя файла")
    language: Optional[str] = Field("RU", pattern="^RU$", description="Язык документа (только русский)")
    model_name: Optional[str] = Field("default_model", max_length=100, description="Название модели")
    summary_depth: Optional[str] = Field("BULLET", pattern="^(BULLET|DETAILED)$", description="Глубина анализа")

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
    price_per_token: float
    active: bool