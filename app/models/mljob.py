from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlmodel import SQLModel, Field

class MLJob(SQLModel, table=True):
    """
    Задание на ML‑обработку документа.

    Attributes:
        id (int): Идентификатор задачи.
        document_id (int): ID исходного документа.
        model_id (int): ID используемой ML‑модели.
        status (JobStatus): Текущий статус выполнения.
        summary_depth (SummaryDepth): Желаемая подробность конспекта.
        used_credits (Decimal): Сколько списано за задачу.
        summary_text (Optional[str]): Итоговый конспект.
        risk_score (Optional[float]): Общий «риск‑индекс» договора.
        started_at / finished_at (datetime): Таймстемпы выполнения.
    """
    id: int = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    model_id: int = Field(foreign_key="model.id")
    status: str = Field(default="QUEUED")
    summary_depth: str = Field(default="BULLET")
    used_credits: Decimal = Field(default=Decimal("0"))
    summary_text: Optional[str] = None
    risk_score: Optional[float] = None
    started_at: Optional[datetime] = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    def start(self) -> None:
        self.status = "RUNNING"
        self.started_at = datetime.now()

    def finish_ok(self, summary: str, score: float) -> None:
        self.status = "DONE"
        self.summary_text = summary
        self.risk_score = score
        self.finished_at = datetime.now()

    def finish_error(self, msg: str) -> None:
        self.status = "ERROR"
        self.summary_text = f"Error: {msg}"
        self.finished_at = datetime.now()

    def get_user_id(self, session) -> int:
        """Получить user_id через связанный документ"""
        from models.document import Document
        from sqlmodel import select
        statement = select(Document).where(Document.id == self.document_id)
        result = session.exec(statement)
        document = result.first()
        return document.user_id if document else None
