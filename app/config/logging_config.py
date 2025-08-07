import logging
import sys
from datetime import datetime
import os

def setup_logging():
    """Настройка системы логирования для приложения"""
    
    # Создаем папку для логов если не существует
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настройка форматирования
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Консольный вывод
            logging.StreamHandler(sys.stdout),
            # Файл с полными логами
            logging.FileHandler(
                f"{log_dir}/app_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            ),
            # Отдельный файл только для ошибок
            logging.FileHandler(
                f"{log_dir}/errors_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
        ]
    )
    
    # Настройка уровней для разных компонентов
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Создание логгеров для разных модулей
    loggers = {
        'app': logging.getLogger('app'),
        'auth': logging.getLogger('auth'),
        'database': logging.getLogger('database'),
        'prediction': logging.getLogger('prediction'),
        'wallet': logging.getLogger('wallet'),
        'api': logging.getLogger('api')
    }
    
    # Настройка обработчика только для ошибок
    error_handler = logging.FileHandler(
        f"{log_dir}/errors_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    for logger in loggers.values():
        logger.addHandler(error_handler)
    
    return loggers

# Инициализация логгеров
loggers = setup_logging()

# Экспорт основных логгеров
app_logger = loggers['app']
auth_logger = loggers['auth'] 
database_logger = loggers['database']
prediction_logger = loggers['prediction']
wallet_logger = loggers['wallet']
api_logger = loggers['api']