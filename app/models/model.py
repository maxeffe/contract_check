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
