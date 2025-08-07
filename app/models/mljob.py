from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from models.user import User
from models.other import JobStatus, SummaryDepth
from models.riskclause import RiskClause
from models.document import Document
from models.model import Model


@dataclass
class MLJob:
    """
    Задание на ML‑обработку документа.

    Attributes:
        id (int): Идентификатор задачи.
        document (Document): Исходный документ.
        model (Model): Используемая ML‑модель.
        status (JobStatus): Текущий статус выполнения.
        summary_depth (SummaryDepth): Желаемая подробность конспекта.
        used_credits (Decimal): Сколько списано за задачу.
        summary_text (Optional[str]): Итоговый конспект.
        risk_score (Optional[float]): Общий «риск‑индекс» договора.
        risk_clauses (List[RiskClause]): Список рискованных пунктов.
        started_at / finished_at (datetime): Таймстемпы выполнения.
    """
    id: int
    document: Document
    model: Model
    status: JobStatus = JobStatus.QUEUED
    summary_depth: SummaryDepth = SummaryDepth.BULLET
    used_credits: Decimal = Decimal("0")
    summary_text: Optional[str] = None
    risk_score: Optional[float] = None
    risk_clauses: List[RiskClause] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def start(self) -> None:
        """Помечает задачу как RUNNING и ставит started_at."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now()

    def finish_ok(self, summary: str,
                  clauses: List[RiskClause], score: float) -> None:
        """Финализирует задачу со статусом DONE."""
        self.status = JobStatus.DONE
        self.summary_text = summary
        self.risk_clauses = clauses
        self.risk_score = score
        self.finished_at = datetime.now()

    def finish_error(self, msg: str) -> None:
        """Финализирует задачу со статусом ERROR."""
        self.status = JobStatus.ERROR
        self.summary_text = f"Error: {msg}"
        self.finished_at = datetime.now()

    @classmethod
    def enqueue(cls, user: User, document: Document, model: Model,
                depth: SummaryDepth = SummaryDepth.BULLET) -> "MLJob":
        """
        Создаёт ML‑задачу и списывает кредиты за неё.

        Args:
            user: Пользователь, инициировавший задачу.
            document: Документ для обработки.
            model: Выбранная модель.
            depth: Желаемая глубина конспекта.

        Returns:
            Экземпляр MLJob со статусом QUEUED.
        """
        cost = Decimal(str(document.pages * model.price_per_page))
        user.debit(cost, f"ML processing: {document.filename}")

        job = cls(
            id=1,  # в реальном приложении должно генерироваться
            document=document,
            model=model,
            summary_depth=depth,
            used_credits=cost
        )
        return job
