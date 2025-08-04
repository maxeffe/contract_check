from models.user import User
from models.admin import Admin
from models.document import Document
from models.model import Model
from database.config import get_settings
from database.database import get_session, init_db, engine
from sqlmodel import Session



def create_demo_data():
    """Создает демо пользователей и данные для тестирования системы"""
    
    demo_user = User(
        id=1,
        username="demo_user",
        email="demo@example.com",
        password=User.hash_password("password123"),
    )
    print(f"Создан демо пользователь: {demo_user.username}")
    
    admin = Admin(
        user_id=2,
        username="admin",
        email="admin@lawfirm.ru",
        password=User.hash_password("admin_password")
    )
    print(f"Создан администратор: {admin.username}")
    
    return demo_user, admin


def test_basic_functionality(admin):
    """Тестирует базовую функциональность моделей"""
    print("\n=== Тестирование основных моделей ===")
    
    from models.wallet import Wallet
    wallet = Wallet(user_id=1)
    print(f"Создан кошелек с балансом: {wallet.balance}")
    
    tx1 = wallet.credit(100, "initial_topup") 
    print(f"Пополнение на 100: новый баланс {wallet.balance}")
    
    tx2 = admin.credit_user(wallet, 50, "admin_bonus")
    print(f"Админ начислил бонус 50: новый баланс {wallet.balance}")
    print(f"Роль администратора: {admin.role}")

    try:
        tx3 = wallet.debit(30, "service_payment")
        print(f"Списание 30: новый баланс {wallet.balance}")
    except ValueError as e:
        print(f"Ошибка списания: {e}")
    
    transactions = wallet.get_transactions()
    print(f"Всего транзакций: {len(transactions)}")
    for i, tx in enumerate(transactions, 1):
        print(f"{i}. {tx.tx_type} - {tx.amount} кредитов")

def test_document_processing():
    """Тестирует загрузку и обработку документов"""
    print("\n=== Обработка документов ===")
    
    document = Document(
        id=1,
        user_id=1,
        filename="test_contract.pdf",
        raw_text="Договор поставки товаров между ООО 'Поставщик' и ООО 'Покупатель'",
        pages=5,
        language="RU",
    )
    print(f"Загружен документ: {document.filename}")
    print(f"Страниц: {document.pages}, язык: {document.language}")
    
    model = Model("Legal-Analyzer-RU", price_per_page=3)
    print(f"Используется модель: {model.name}")
    print(f"Стоимость обработки: {model.price_per_page} кредитов за страницу")
    
    total_cost = document.pages * model.price_per_page
    print(f"Общая стоимость обработки: {total_cost} кредитов")


if __name__ == "__main__":
    print("🚀 Запуск системы анализа договоров")
    
    init_db()
    print("✅ База данных инициализирована")
    
    demo_user, admin = create_demo_data()
    

    test_basic_functionality(admin)
    

    test_document_processing()


