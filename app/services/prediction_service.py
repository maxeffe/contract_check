import uuid
import json
from decimal import Decimal
from typing import Dict, Any, List
from services.crud import document as DocumentService
from services.crud import wallet as WalletService
from services.crud import mljob as MLJobService
from services.crud import model as ModelService

class MockMLService:
    """Мок-сервис для имитации ML предсказаний"""
    
    @staticmethod
    def analyze_contract(text: str, language: str = "UNKNOWN") -> Dict[str, Any]:
        """Имитация анализа договора с ML моделью"""
        # Простая имитация результата анализа
        word_count = len(text.split())
        
        # Имитируем различные типы рисков
        risk_score = min(word_count * 0.01, 1.0)
        
        result = {
            "risk_score": round(risk_score, 2),
            "risk_level": "HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.4 else "LOW",
            "identified_clauses": [
                {
                    "type": "payment_terms",
                    "risk_level": "MEDIUM",
                    "text_snippet": text[:100] + "..." if len(text) > 100 else text,
                    "recommendation": "Рекомендуется уточнить условия платежа"
                },
                {
                    "type": "liability",
                    "risk_level": "LOW",
                    "text_snippet": text[100:200] + "..." if len(text) > 200 else "",
                    "recommendation": "Стандартные условия ответственности"
                }
            ] if word_count > 10 else [],
            "summary": f"Проанализирован договор на {language.lower()} языке, найдено {word_count} слов",
            "confidence": 0.85,
            "processing_time": 2.5
        }
        
        return result
    
    @staticmethod
    def calculate_cost(pages: int, language: str = "UNKNOWN") -> Decimal:
        """Расчет стоимости анализа на основе количества страниц и языка"""
        base_cost = Decimal("1.0")  # 1 кредит за страницу
        
        # Множители для разных языков
        language_multipliers = {
            "RU": Decimal("1.0"),
            "EN": Decimal("1.2"),
            "UNKNOWN": Decimal("1.5")
        }
        
        multiplier = language_multipliers.get(language.upper(), Decimal("1.5"))
        total_cost = base_cost * pages * multiplier
        
        return total_cost

def process_prediction_request(
    user_id: int,
    document_text: str,
    filename: str = None,
    language: str = "UNKNOWN",
    model_name: str = "default_model",
    summary_depth: str = "BULLET",
    session=None
) -> Dict[str, Any]:
    """Обработка запроса на предсказание - бизнес-логика уровня приложения"""
    
    # Подсчитываем примерное количество страниц (по 500 слов на страницу)
    word_count = len(document_text.split())
    pages = max(1, word_count // 500)
    
    # Создаем документ в базе
    document = DocumentService.create_document(
        user_id=user_id,
        filename=filename or f"document_{uuid.uuid4().hex[:8]}.txt",
        raw_text=document_text,
        pages=pages,
        session=session,
        language=language
    )
    
    # Получаем или создаем модель
    model = ModelService.get_model_by_name(model_name, session)
    if not model:
        model = ModelService.create_model(
            name=model_name,
            session=session,
            price_per_page=1,
            active=True
        )
    
    # Рассчитываем стоимость
    cost = Decimal(str(pages * model.price_per_page))
    
    # Проверяем баланс пользователя
    wallet = WalletService.get_or_create_wallet(user_id, session)
    if wallet.balance < cost:
        raise ValueError(f"Insufficient balance. Required: {cost}, Available: {wallet.balance}")
    
    # Создаем ML задание
    job = MLJobService.create_mljob(
        document_id=document.id,
        model_id=model.id,
        session=session,
        summary_depth=summary_depth
    )
    
    # Списываем средства
    WalletService.debit_wallet(user_id, cost, session)
    
    # Выполняем анализ
    analysis_result = MockMLService.analyze_contract(document_text, language)
    
    # Завершаем задание с результатами
    risk_clauses_data = [{
        "text": clause["text_snippet"],
        "risk_level": clause["risk_level"],
        "explanation": clause["recommendation"]
    } for clause in analysis_result.get("identified_clauses", [])]
    
    completed_job = MLJobService.complete_job(
        job_id=job.id,
        summary_text=analysis_result.get("summary", ""),
        risk_score=analysis_result.get("risk_score", 0.0),
        risk_clauses=risk_clauses_data,
        session=session
    )
    
    return {
        "job_id": completed_job.id,
        "document_id": document.id,
        "prediction_result": analysis_result,
        "cost": float(cost),
        "pages_processed": pages,
        "status": "completed"
    }