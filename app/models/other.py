from enum import Enum


class Role(str, Enum):
    """Роль учётной записи."""
    USER = "USER"
    ADMIN = "ADMIN"


class TxType(str, Enum):
    """Типы движения средств в кошельке."""
    CREDIT = "CREDIT"   # пополнение
    DEBIT = "DEBIT"    # списание


class JobStatus(str, Enum):
    """Статус задачи в очереди / воркере."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class SummaryDepth(str, Enum):
    """Гранулярность итогового конспекта договора."""
    BRIEF = "BRIEF"     # несколько предложений
    BULLET = "BULLET"    # список буллетов
    DETAILED = "DETAILED"  # развернутый пересказ


class RiskLevel(str, Enum):
    """Уровень риска, обнаруженного в пункте договора."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
