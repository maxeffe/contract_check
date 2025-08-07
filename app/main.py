"""
Web‑сервис для юристов и предпринимателей, который:

* принимает договор (PDF / DOCX / сырой текст, RU или EN);
* списывает кредиты из личного кабинета (1 кредит = 1 страница);
* прогоняет документ через модель;
* возвращает структурированный краткий конспект договора и подсвечивает
  рискованные пункты.

"""


from models.user import User
from models.admin import Admin
from models.document import Document
from models.model import Model


if __name__ == "__main__":
    # Создание пользователя
    user = User(
        id=1,
        username="karpov",
        email="karpov@jurist.ru",
        password=User.hash_password("password12312"),
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
        language="RU",
    )
    print(f"Загружен документ: {document.filename}, страниц: {document.pages}")

    admin = Admin(2, "admin", "admin@lawfirm.ru",
                  User.hash_password("admin_pass"))
    admin.credit_user(user, 200, "bonus")
    print(f"Админ начислил бонус, баланс пользователя: {user.balance}")

    # Создание ML-модели
    model = Model("Legal-Analyzer-RU", price_per_page=3)
    print(f"Модель: {model.name}, цена за страницу: {model.price_per_page}")




#Для теста
# import uvicorn
# from fastapi import FastAPI

# app = FastAPI()


# @app.get("/")
# async def read_root():
#     return {"Hello": "World"}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080) 
