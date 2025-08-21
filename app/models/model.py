from sqlmodel import SQLModel, Field


class Model(SQLModel, table=True):
    model_config = {"protected_namespaces": ()}
    """
    Метаданные ML‑модели.

    Attributes:
        name (str): Название модели.
        price_per_token (float): Стоимость обработки одного токена в кредитах.
        active (bool): Доступна ли модель пользователям.
    """
    id: int = Field(default=None, primary_key=True)
    name: str
    price_per_token: float = Field(default=0.001)  # 0.001 рубля за токен
    active: bool = Field(default=True)

    def predict(self, text: str) -> str:
        return f"Processed by {self.name}: {text[:50]}..."
