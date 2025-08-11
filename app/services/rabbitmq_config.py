import pika
import json
import os
from datetime import datetime
from typing import Optional
from config.logging_config import app_logger


class RabbitMQConfig:
    """Конфигурация для подключения к RabbitMQ"""
    
    def __init__(self):
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.username = os.getenv('RABBITMQ_DEFAULT_USER', 'guest')
        self.password = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
        self.virtual_host = os.getenv('RABBITMQ_VIRTUAL_HOST', '/')
        
        self.ml_queue_name = 'ml_tasks_queue'
        self.exchange_name = 'ml_exchange'
        self.routing_key = 'ml.task'

    def get_connection(self) -> pika.BlockingConnection:
        """Создает подключение к RabbitMQ"""
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        return pika.BlockingConnection(parameters)
    
    def setup_queue(self, connection: pika.BlockingConnection):
        """Настраивает exchange и очередь"""
        channel = connection.channel()
        
        channel.exchange_declare(
            exchange=self.exchange_name,
            exchange_type='direct',
            durable=True
        )
        
        channel.queue_declare(
            queue=self.ml_queue_name,
            durable=True
        )
        
        channel.queue_bind(
            exchange=self.exchange_name,
            queue=self.ml_queue_name,
            routing_key=self.routing_key
        )
        
        app_logger.info(f"RabbitMQ настроен: exchange={self.exchange_name}, queue={self.ml_queue_name}")
        return channel


class MLTaskPublisher:
    """Publisher для отправки ML задач в RabbitMQ"""
    
    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = self.config.get_connection()
            self.channel = self.config.setup_queue(self.connection)
            app_logger.info("Publisher подключен к RabbitMQ")
        except Exception as e:
            app_logger.error(f"Ошибка подключения Publisher к RabbitMQ: {e}")
            raise
    
    def publish_ml_task(self, job_id: int, document_id: int, model_id: int, summary_depth: str = "BULLET"):
        """Отправляет ML задачу в очередь"""
        if not self.channel:
            self.connect()
        
        task_data = {
            "job_id": job_id,
            "document_id": document_id,
            "model_id": model_id,
            "summary_depth": summary_depth,
            "timestamp": str(datetime.now())
        }
        
        try:
            self.channel.basic_publish(
                exchange=self.config.exchange_name,
                routing_key=self.config.routing_key,
                body=json.dumps(task_data),
                properties=pika.BasicProperties(
                    delivery_mode=2, 
                    content_type='application/json'
                )
            )
            app_logger.info(f"ML задача отправлена в очередь: job_id={job_id}")
            return True
        except Exception as e:
            app_logger.error(f"Ошибка отправки ML задачи: {e}")
            return False
    
    def close(self):
        """Закрывает соединение"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            app_logger.info("Publisher отключен от RabbitMQ")


_publisher = None

def get_ml_publisher() -> MLTaskPublisher:
    """Возвращает singleton экземпляр publisher"""
    global _publisher
    if _publisher is None:
        config = RabbitMQConfig()
        _publisher = MLTaskPublisher(config)
    return _publisher