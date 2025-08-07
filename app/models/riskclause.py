from typing import Optional
from sqlmodel import SQLModel, Field

class RiskClause(SQLModel, table=True):
    """
    Пункт договора с указанием уровня риска.

    Attributes:
        clause_text (str): Сам текст пункта.
        risk_level (RiskLevel): LOW, MEDIUM или HIGH.
        explanation (Optional[str]): Комментарий‑обоснование.
    """
    id: int = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="mljob.id")
    clause_text: str
    risk_level: str
    explanation: Optional[str] = None
