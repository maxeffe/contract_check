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


class MLWorker:
    """Worker для обработки ML задач из RabbitMQ"""
    
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.config = RabbitMQConfig()
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = self.config.get_connection()
            self.channel = self.config.setup_queue(self.connection)
            
            self.channel.basic_qos(prefetch_count=1)
            
            app_logger.info(f"ML Worker {self.worker_id} подключен к RabbitMQ")
        except Exception as e:
            app_logger.error(f"Ошибка подключения Worker {self.worker_id} к RabbitMQ: {e}")
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
            
            # В случае критической ошибки обработки также возвращаем деньги
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
                
                summary_text, risk_score = self.simulate_ml_analysis(
                    document.raw_text, 
                    summary_depth, 
                    model.name
                )
                
                used_credits = document.pages * model.price_per_page
                job.used_credits = used_credits
                
                job.finish_ok(summary_text, risk_score)
                session.add(job)
                # Исправлено: один commit в конце для атомарности транзакции
                session.commit()
                
                app_logger.info(f"ML анализ завершен: job_id={job_id}, risk_score={risk_score}, credits={used_credits}")
                return True
                
        except Exception as e:
            app_logger.error(f"Ошибка выполнения ML предикта для задачи {job_id}: {e}")
            self.update_job_status(job_id, "ERROR", f"Ошибка ML: {str(e)}", refund_money=True)
            return False
    
    def simulate_ml_analysis(self, text: str, depth: str, model_name: str) -> tuple[str, float]:
        """Имитирует ML анализ документа"""
        time.sleep(2)
        
        risk_factors = []
        risk_score = 0.1
        
        risk_keywords = [
            'штраф', 'пеня', 'неустойка', 'ответственность', 
            'обязательство', 'гарантия', 'возмещение', 'ущерб'
        ]
        
        for keyword in risk_keywords:
            if keyword.lower() in text.lower():
                risk_factors.append(keyword)
                risk_score += 0.15
        
        risk_score = min(risk_score, 1.0)
        
        if depth == "BULLET":
            summary = f"""• Анализ выполнен моделью {model_name}
• Найдено рисковых факторов: {len(risk_factors)}
• Ключевые термины: {', '.join(risk_factors[:3]) if risk_factors else 'отсутствуют'}
• Общий риск-индекс: {risk_score:.2f}"""
        else: 
            summary = f"""Детальный анализ договора (модель: {model_name})

РИСКОВЫЕ ФАКТОРЫ:
{chr(10).join(f'- {factor}' for factor in risk_factors) if risk_factors else 'Значимые риски не выявлены'}

РЕКОМЕНДАЦИИ:
- Обратить внимание на разделы с финансовой ответственностью
- Проверить сроки исполнения обязательств
- Уточнить процедуры разрешения споров

Интегральная оценка риска: {risk_score:.2f} из 1.0"""
        
        return summary, risk_score
    
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
                                        refund_amount = Decimal(str(document.pages * model.price_per_page))
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