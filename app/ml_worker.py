import json
import time
import traceback
from datetime import datetime
import pika
from sqlmodel import Session
from database.database import engine
from models.mljob import MLJob
from models.document import Document
from models.model import Model
from services.rabbitmq_config import RabbitMQConfig
from services.crud import wallet as WalletService
from config.logging_config import app_logger
from services.huggingface_service import huggingface_service


class MLWorker:
    """Worker для обработки ML задач из RabbitMQ"""
    
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.config = RabbitMQConfig()
        self.connection = None
        self.channel = None
        self.ml_service = huggingface_service
        app_logger.info(f"Worker {worker_id} использует реальный API сервис Hugging Face")
        
    def connect(self):
        """Подключение к RabbitMQ с повторными попытками"""
        import time
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.connection = self.config.get_connection()
                self.channel = self.config.setup_queue(self.connection)
                
                self.channel.basic_qos(prefetch_count=1)
                
                app_logger.info(f"ML Worker {self.worker_id} подключен к RabbitMQ")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    app_logger.warning(f"Worker {self.worker_id} попытка {attempt + 1}/{max_retries} подключения к RabbitMQ неудачна, повтор через {retry_delay}с: {e}")
                    time.sleep(retry_delay)
                else:
                    app_logger.error(f"Ошибка подключения Worker {self.worker_id} к RabbitMQ после {max_retries} попыток: {e}")
                    raise
    
    def process_ml_task(self, ch, method, properties, body):
        """Обработчик ML задачи"""
        try:
            task_data = json.loads(body.decode('utf-8'))
            job_id = task_data['job_id']
            document_id = task_data['document_id']
            model_id = task_data['model_id']
            summary_depth = task_data.get('summary_depth', 'BULLET')
            
            app_logger.info(f"Worker {self.worker_id} начал обработку задачи {job_id}")
            
            if not self.validate_task_data(job_id, document_id, model_id):
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            success = self.execute_ml_prediction(job_id, document_id, model_id, summary_depth)
            
            if success:
                app_logger.info(f"Worker {self.worker_id} успешно завершил задачу {job_id}")
            else:
                app_logger.error(f"Worker {self.worker_id} не смог выполнить задачу {job_id}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            app_logger.error(f"Worker {self.worker_id} ошибка обработки: {e}")
            app_logger.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                task_data = json.loads(body.decode('utf-8'))
                job_id = task_data.get('job_id')
                if job_id:
                    self.update_job_status(job_id, "ERROR", f"Критическая ошибка обработки: {str(e)}", refund_money=True)
            except:
                pass
            
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def validate_task_data(self, job_id: int, document_id: int, model_id: int) -> bool:
        """Валидация данных задачи"""
        try:
            with Session(engine) as session:
                job = session.get(MLJob, job_id)
                if not job:
                    app_logger.error(f"MLJob {job_id} не найдена")
                    return False
                
                document = session.get(Document, document_id)
                if not document:
                    app_logger.error(f"Document {document_id} не найден")
                    self.update_job_status(job_id, "ERROR", "Документ не найден", refund_money=True)
                    return False
                
                model = session.get(Model, model_id)
                if not model:
                    app_logger.error(f"Model {model_id} не найдена")
                    self.update_job_status(job_id, "ERROR", "Модель не найдена", refund_money=True)
                    return False
                
                if not document.raw_text:
                    app_logger.error(f"Document {document_id} не содержит текста")
                    self.update_job_status(job_id, "ERROR", "Документ не содержит текста", refund_money=True)
                    return False
                
                app_logger.info(f"Валидация задачи {job_id} прошла успешно")
                return True
                
        except Exception as e:
            app_logger.error(f"Ошибка валидации задачи {job_id}: {e}")
            self.update_job_status(job_id, "ERROR", f"Ошибка валидации: {str(e)}", refund_money=True)
            return False
    
    def execute_ml_prediction(self, job_id: int, document_id: int, model_id: int, summary_depth: str) -> bool:
        """Выполняет ML предикт"""
        try:
            with Session(engine) as session:
                job = session.get(MLJob, job_id)
                document = session.get(Document, document_id)
                model = session.get(Model, model_id)
                
                if not all([job, document, model]):
                    return False
                
                job.start()
                app_logger.info(f"Начат ML анализ документа {document.filename} с моделью {model.name}")
                
                analysis_result = self.ml_service.analyze_contract_risks(document.raw_text)
                
                if analysis_result["processed_successfully"]:
                    summary_text = analysis_result.get("summary") or "Анализ выполнен успешно"
                    risk_score = analysis_result.get("risk_score", 0.0)
                    risk_clauses = analysis_result.get("risk_clauses", [])
                    
                    if analysis_result.get("key_terms"):
                        key_terms = analysis_result["key_terms"][:5]
                        summary_text += f"\n\nКлючевые термины: {', '.join(key_terms)}"
                        
                    app_logger.info(f"HuggingFace API успешно обработал документ {document.filename}")
                else:
                    app_logger.warning(f"HuggingFace API не смог обработать документ {document.filename}: {analysis_result.get('error_message', 'Unknown error')}")
                    summary_text, risk_score, risk_clauses = self.simulate_ml_analysis_fallback(
                        document.raw_text, summary_depth, model.name
                    )
                
                used_credits = document.token_count * model.price_per_token
                job.used_credits = used_credits
                
                job.finish_ok(summary_text, risk_score)
                session.add(job)
                
                if risk_clauses:
                    from services.crud import mljob as MLJobService
                    MLJobService.add_risk_clauses_to_job(job.id, risk_clauses, session)
                
                session.commit()
                
                app_logger.info(f"ML анализ завершен: job_id={job_id}, risk_score={risk_score}, credits={used_credits}")
                return True
                
        except Exception as e:
            app_logger.error(f"Ошибка выполнения ML предикта для задачи {job_id}: {e}")
            self.update_job_status(job_id, "ERROR", f"Ошибка ML: {str(e)}", refund_money=True)
            return False

    def simulate_ml_analysis_fallback(self, text: str, depth: str, model_name: str) -> tuple[str, float, list]:
        """Резервный метод когда HuggingFace API недоступен"""
        app_logger.warning("HuggingFace API недоступен, используется локальный анализ")
        time.sleep(1)
        
        risk_keywords = {
            'неустойка': 0.8, 'штраф': 0.7, 'пени': 0.8,
            'ответственность': 0.6, 'нарушение': 0.7,
            'расторжение': 0.9, 'односторонний': 0.9,
            'просрочка': 0.6, 'penalty': 0.7, 'fine': 0.7
        }
        
        found_risks = []
        risk_score = 0.1
        text_lower = text.lower()
        
        for keyword, weight in risk_keywords.items():
            if keyword in text_lower:
                found_risks.append(keyword)
                risk_score += weight * 0.1
        
        risk_score = min(risk_score, 0.9) 
        
        api_notice = "⚠️ ВНИМАНИЕ: Текст не был обработан полноценными ML-моделями."
        
        if depth == "BULLET":
            summary = f"""{api_notice}
• Выполнен базовый анализ на ключевых словах
• Найдено рисковых терминов: {len(found_risks)}
• Ключевые термины: {', '.join(found_risks[:3]) if found_risks else 'не обнаружены'}
• Приблизительная оценка риска: {risk_score:.2f}
• Для точного анализа требуется настройка HuggingFace API"""
        else:
            summary = f"""{api_notice}

БАЗОВЫЙ АНАЛИЗ:
Выполнен упрощенный анализ документа без использования нейронных сетей.

ОБНАРУЖЕННЫЕ РИСКОВЫЕ ТЕРМИНЫ:
{chr(10).join(f'- {term}' for term in found_risks) if found_risks else '- Значимые рисковые термины не обнаружены'}

ОГРАНИЧЕНИЯ АНАЛИЗА:
- Анализ выполнен без ML-моделей HuggingFace
- Результаты могут быть неточными
- Рекомендуется настройка API для полноценного анализа

ПРИБЛИЗИТЕЛЬНАЯ ОЦЕНКА РИСКА: {risk_score:.2f} из 1.0

Для получения качественного анализа необходимо:
1. Установить HUGGINGFACE_API_TOKEN в переменные окружения
2. Убедиться в наличии доступа к интернету"""
        
        risk_clauses = []
        if found_risks:
            risk_clauses.append({
                'clause_text': f"Обнаружены потенциально рисковые термины: {', '.join(found_risks[:5])}",
                'risk_level': 'MEDIUM',
                'explanation': 'Базовый анализ без ML-моделей. Требуется настройка HuggingFace API для точного анализа.'
            })
        
        return summary, risk_score, risk_clauses
    
    def update_job_status(self, job_id: int, status: str, error_msg: str = "", refund_money: bool = False):
        """Обновляет статус задачи в БД и возвращает деньги при ошибке"""
        try:
            with Session(engine) as session:
                job = session.get(MLJob, job_id)
                if job:
                    if status == "ERROR":
                        job.finish_error(error_msg)
                        
                        if refund_money:
                            try:
                                user_id = job.get_user_id(session)
                                if user_id:
                                    from decimal import Decimal
                                    document = session.get(Document, job.document_id)
                                    model = session.get(Model, job.model_id)
                                    if document and model:
                                        refund_amount = Decimal(str(document.token_count * model.price_per_token))
                                        WalletService.credit_wallet(user_id, refund_amount, session)
                                        app_logger.info(f"Возвращены средства пользователю {user_id}: {refund_amount} за неудачное предсказание {job_id}")
                                    else:
                                        app_logger.error(f"Не удалось найти документ или модель для возврата средств по job {job_id}")
                                else:
                                    app_logger.error(f"Не удалось определить пользователя для возврата средств по job {job_id}")
                            except Exception as refund_error:
                                app_logger.error(f"Ошибка возврата средств для job {job_id}: {refund_error}")
                    else:
                        job.status = status
                    session.add(job)
                    session.commit()
        except Exception as e:
            app_logger.error(f"Ошибка обновления статуса job {job_id}: {e}")
    
    def start_consuming(self):
        """Запускает потребление сообщений из очереди"""
        if not self.channel:
            self.connect()
        
        self.channel.basic_consume(
            queue=self.config.ml_queue_name,
            on_message_callback=self.process_ml_task
        )
        
        app_logger.info(f"Worker {self.worker_id} начал ожидание ML задач...")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            app_logger.info(f"Worker {self.worker_id} получил сигнал остановки")
            self.stop_consuming()
    
    def stop_consuming(self):
        """Останавливает потребление сообщений"""
        if self.channel:
            self.channel.stop_consuming()
        
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        
        app_logger.info(f"Worker {self.worker_id} остановлен")


if __name__ == "__main__":
    import sys
    
    worker_id = sys.argv[1] if len(sys.argv) > 1 else "worker-default"
    
    worker = MLWorker(worker_id)
    try:
        worker.start_consuming()
    except Exception as e:
        app_logger.error(f"Критическая ошибка worker {worker_id}: {e}")
        sys.exit(1)