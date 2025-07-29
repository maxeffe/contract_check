"""
Web‑сервис для юристов и предпринимателей, который:

* принимает договор (PDF / DOCX / сырой текст, RU или EN);
* списывает кредиты из личного кабинета (1 кредит = 1 страница);
* прогоняет документ через модель;
* возвращает структурированный краткий конспект договора и подсвечивает рискованные пункты.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import re
import bcrypt


class Role(str, Enum):
    """Роль учётной записи."""
    USER  = "USER"
    ADMIN = "ADMIN"


class TxType(str, Enum):
    """Типы движения средств в кошельке."""
    CREDIT = "CREDIT"   # пополнение
    DEBIT  = "DEBIT"    # списание


class JobStatus(str, Enum):
    """Статус задачи в очереди / воркере."""
    QUEUED  = "QUEUED"
    RUNNING = "RUNNING"
    DONE    = "DONE"
    ERROR   = "ERROR"


class SummaryDepth(str, Enum):
    """Гранулярность итогового конспекта договора."""
    BRIEF    = "BRIEF"     # несколько предложений
    BULLET   = "BULLET"    # список буллетов
    DETAILED = "DETAILED"  # развернутый пересказ


class RiskLevel(str, Enum):
    """Уровень риска, обнаруженного в пункте договора."""
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


@dataclass
class Transaction:
    """
    Движение средств в кошельке пользователя.

    Attributes:
        id (int): Уникальный идентификатор транзакции.
        user_id (int): ID пользователя, к которому относится транзакция.
        tx_type (TxType): CREDIT (зачисление) или DEBIT (списание).
        amount (Decimal): Сумма операции в кредитах (без знака).
        trans_time (datetime): Момент совершения операции.
    """
    id: int
    user_id: int
    tx_type: TxType
    amount: Decimal
    trans_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class User:
    """
    Учётная запись.

    Attributes:
        id (int): Идентификатор пользователя.
        username (str): Отображаемое имя / login.
        email (str): Адрес электронной почты.
        password (str): Хэш пароля.
        role (Role): USER или ADMIN.
        wallet (Wallet): Кошелек пользователя.
    """
    id: int
    username: str
    email: str
    password: str
    role: Role = Role.USER
    wallet: Optional[Wallet] = None


    def __post_init__(self) -> None:
        self._validate_email()
        self._validate_password()
        if self.wallet is None:
            self.wallet = Wallet(user_id=self.id)

    def _validate_email(self) -> None:
        if not re.fullmatch(r"^[\w\.-]+@[\w\.-]+\.\w+$", self.email):
            raise ValueError("Invalid email")

    def _validate_password(self) -> None:
        if len(self.password) < 8:
            raise ValueError("Password must be ≥ 8 chars")

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширует пароль с использованием bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Проверяет соответствие пароля хешу."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))


    @property
    def balance(self) -> Decimal:
        """Текущий баланс пользователя (read‑only)."""
        return self.wallet.balance if self.wallet else Decimal("0")

    def credit(self, amount: int | Decimal, ref: str = "topup") -> Transaction:
        """Зачисление средств."""
        return self.wallet.credit(amount, ref)

    def debit(self, amount: int | Decimal, ref: str) -> Transaction:
        """Списание средств. Бросает ValueError при нехватке баланса."""
        return self.wallet.debit(amount, ref)


class Admin(User):
    """Администратор — наследник User c дополнительными полномочиями."""

    def __init__(self, id: int, username: str, email: str, password: str):
        super().__init__(id=id, username=username,
                         email=email, password=password,
                         role=Role.ADMIN)

    def credit_user(self, other: User, amount: int | Decimal,
                    note: str = "admin_topup") -> Transaction:
        """Начисляет кредиты другому пользователю от имени администратора."""
        return other.credit(amount, note)


@dataclass
class Wallet:
    """
    Кошелек пользователя для управления балансом и транзакциями.

    Attributes:
        user_id (int): ID пользователя, которому принадлежит кошелек.
        _balance (Decimal): Текущий баланс в кредитах.
        transactions (List[Transaction]): История операций.
    """
    user_id: int
    _balance: Decimal = Decimal("0")
    transactions: List[Transaction] = field(default_factory=list)

    @property
    def balance(self) -> Decimal:
        """Текущий баланс (read-only)."""
        return self._balance

    def _add_tx(self, tx: Transaction) -> None:
        """Добавляет транзакцию в историю и пересчитывает баланс."""
        self.transactions.append(tx)
        if tx.tx_type == TxType.CREDIT:
            self._balance += tx.amount
        elif tx.tx_type == TxType.DEBIT:
            self._balance -= tx.amount

    def credit(self, amount: int | Decimal, ref: str = "topup") -> Transaction:
        """Зачисление средств."""
        amount = Decimal(str(amount))
        tx = Transaction(
            id=len(self.transactions) + 1,
            user_id=self.user_id,
            tx_type=TxType.CREDIT,
            amount=amount
        )
        self._add_tx(tx)
        return tx

    def debit(self, amount: int | Decimal, ref: str) -> Transaction:
        """Списание средств. Бросает ValueError при нехватке баланса."""
        amount = Decimal(str(amount))
        if self._balance < amount:
            raise ValueError(f"Insufficient balance: {self._balance} < {amount}")
        
        tx = Transaction(
            id=len(self.transactions) + 1,
            user_id=self.user_id,
            tx_type=TxType.DEBIT,
            amount=amount
        )
        self._add_tx(tx)
        return tx



@dataclass
class Document:
    """
    Загруженный договор / файл.

    Attributes:
        id (int): Идентификатор документа.
        user_id (int): Автор документа.
        filename (str): Имя файла.
        raw_text (str): Извлечённый полный текст договора.
        pages (int): Количество страниц (нужно для тарификации).
        language (str): RU, EN или UNKNOWN.
        uploaded_at (datetime): Время загрузки.
    """
    id: int
    user_id: int
    filename: str
    raw_text: str
    pages: int
    language: str = "UNKNOWN"
    uploaded_at: datetime = field(default_factory=datetime.utcnow)


class Model:
    """
    Метаданные ML‑модели.

    Attributes:
        name (str): Название модели.
        price_per_page (int): Стоимость обработки одной страницы в кредитах.
        active (bool): Доступна ли модель пользователям.
    """
    name: str
    price_per_page: int
    active: bool = True

    def __init__(self, name: str, price_per_page: int = 1):
        self.name = name
        self.price_per_page = price_per_page

    def predict(self, text: str) -> str:
        """Обрабатывает текст через ML-модель и возвращает результат."""
        return f"Processed by {self.name}: {text[:50]}..."


@dataclass
class RiskClause:
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
        self.started_at = datetime.utcnow()

    def finish_ok(self, summary: str,
                  clauses: List[RiskClause], score: float) -> None:
        """Финализирует задачу со статусом DONE."""
        self.status = JobStatus.DONE
        self.summary_text = summary
        self.risk_clauses = clauses
        self.risk_score = score
        self.finished_at = datetime.utcnow()

    def finish_error(self, msg: str) -> None:
        """Финализирует задачу со статусом ERROR."""
        self.status = JobStatus.ERROR
        self.summary_text = f"Error: {msg}"
        self.finished_at = datetime.utcnow()


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


if __name__ == "__main__":
    # Создание пользователя    
    user = User(
        id=1, 
        username="karpov", 
        email="karpov@jurist.ru",
        password=User.hash_password("password12312")
    )
    print(f"Создан пользователь: {user.username}, баланс: {user.balance}")
    
    # Пополнение счета
    user.credit(500, "initial_payment")
    print(f"После пополнения баланс: {user.balance}")
    
    # Создание документа
    document = Document(
        id=1,
        user_id=user.id,
        filename="contract_supply.pdf", 
        raw_text="Договор образовательных услуг karpov.courses",
        pages=8,
        language="RU"
    )
    print(f"Загружен документ: {document.filename}, страниц: {document.pages}")


    admin = Admin(2, "admin", "admin@lawfirm.ru", User.hash_password("admin_pass"))
    admin.credit_user(user, 200, "bonus")
    print(f"Админ начислил бонус, баланс пользователя: {user.balance}")
    
    # Создание ML-модели
    model = Model("Legal-Analyzer-RU", price_per_page=3)
    print(f"Модель: {model.name}, цена за страницу: {model.price_per_page}")
    


    

    

