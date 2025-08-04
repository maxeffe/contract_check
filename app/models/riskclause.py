from dataclasses import dataclass
from typing import Optional
from models.other import RiskLevel
from sqlmodel import SQLModel, Field


@dataclass
class RiskClause(SQLmodel, table=true):
    """
    Пункт договора с указанием уровня риска.

    Attributes:
        clause_text (str): Сам текст пункта.
        risk_level (RiskLevel): LOW, MEDIUM или HIGH.
        explanation (Optional[str]): Комментарий‑обоснование.
    """
    clause_text: str
    risk_level: RiskLevel
    explanation: Optional[str] = None
