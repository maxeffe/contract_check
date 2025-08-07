from sqlmodel import SQLModel, Field


class Model(SQLModel, table=True):
    """
    Метаданные ML‑модели.

    Attributes:
        name (str): Название модели.
        price_per_page (int): Стоимость обработки одной страницы в кредитах.
        active (bool): Доступна ли модель пользователям.
    """
    id: int = Field(default=None, primary_key=True)
    name: str
    price_per_page: int = Field(default=1)
    active: bool = Field(default=True)

    def predict(self, text: str) -> str:
        return f"Processed by {self.name}: {text[:50]}..."
