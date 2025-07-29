from dataclasses import dataclass, field
from datetime import datetime


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
    uploaded_at: datetime = field(default_factory=datetime.now)
