import uuid
import json
from decimal import Decimal
from typing import Dict, Any, List
from services.crud import document as DocumentService
from services.crud import wallet as WalletService
from services.crud import mljob as MLJobService
from services.crud import model as ModelService
from services.rabbitmq_config import get_ml_publisher

class MockMLService:
    """Сервис имитации ML предсказаний"""
    
    @staticmethod
    def analyze_contract(text: str, language: str = "UNKNOWN") -> Dict[str, Any]:
        """Имитация анализа договора с ML моделью"""

        word_count = len(text.split())
        
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
        base_cost = Decimal("1.0") 

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
    
    from models.document import Document
    token_count = Document.count_tokens(document_text)
    
    document = DocumentService.create_document(
        user_id=user_id,
        filename=filename or f"document_{uuid.uuid4().hex[:8]}.txt",
        raw_text=document_text,
        token_count=token_count,
        session=session,
        language=language
    )
    
    model = ModelService.get_model_by_name(model_name, session)
    if not model:
        model = ModelService.create_model(
            name=model_name,
            session=session,
            price_per_token=0.001,
            active=True
        )
    
    cost = Decimal(str(token_count * model.price_per_token))
    
    wallet = WalletService.get_or_create_wallet(user_id, session)
    if wallet.balance < cost:
        raise ValueError(f"Insufficient balance. Required: {cost}, Available: {wallet.balance}")
    
    job = MLJobService.create_mljob(
        document_id=document.id,
        model_id=model.id,
        session=session,
        summary_depth=summary_depth
    )
    
    publisher = get_ml_publisher()
    task_sent = publisher.publish_ml_task(
        job_id=job.id,
        document_id=document.id,
        model_id=model.id,
        summary_depth=summary_depth
    )
    
    if not task_sent:
        session.delete(job)
        session.commit()
        raise Exception("Не удалось отправить задачу в очередь обработки")
    

    WalletService.debit_wallet(user_id, cost, session)
    
    return {
        "job_id": job.id,
        "document_id": document.id,
        "status": "queued",
        "message": "Задача отправлена на обработку",
        "cost": float(cost),
        "tokens_processed": token_count
    }