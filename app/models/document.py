from datetime import datetime
from sqlmodel import SQLModel, Field
import re

class Document(SQLModel, table=True):
    """
    Загруженный договор / файл.

    Attributes:
        id (int): Идентификатор документа.
        user_id (int): Автор документа.
        filename (str): Имя файла.
        raw_text (str): Извлечённый полный текст договора.
        token_count (int): Количество токенов (нужно для тарификации).
        language (str): RU (только русский язык).
        uploaded_at (datetime): Время загрузки.
    """
    id: int = Field(default=None, primary_key=True)
    user_id: int
    filename: str
    raw_text: str
    token_count: int
    language: str = "RU"
    uploaded_at: datetime = Field(default_factory=datetime.now)
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Подсчет токенов в тексте (приблизительно)"""
        clean_text = re.sub(r'\s+', ' ', text.strip())
        return max(1, len(clean_text) // 4)
