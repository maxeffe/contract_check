import streamlit as st
from datetime import datetime
from typing import Any, Dict, List

def format_datetime(date_string: str) -> str:
    """Форматировать дату и время для отображения"""
    if not date_string:
        return "N/A"
    
    try:
        # Парсим ISO формат даты
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return date_string

def format_currency(amount: float) -> str:
    """Форматировать сумму в рублях"""
    return f"{amount:.2f}₽"

def format_percentage(value: float) -> str:
    """Форматировать процентное значение"""
    return f"{value * 100:.1f}%"

def get_status_color(status: str) -> str:
    """Получить цвет для статуса"""
    colors = {
        'COMPLETED': 'green',
        'ERROR': 'red',
        'PROCESSING': 'orange',
        'QUEUED': 'blue'
    }
    return colors.get(status, 'gray')

def get_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса"""
    emojis = {
        'COMPLETED': '✅',
        'ERROR': '❌',
        'PROCESSING': '🔄',
        'QUEUED': '⏳'
    }
    return emojis.get(status, '❓')

def calculate_pages_from_text(text: str) -> int:
    """Рассчитать примерное количество страниц из текста"""
    word_count = len(text.split())
    return max(1, word_count // 500)  # Примерно 500 слов на страницу

def validate_file_size(file_content: bytes, max_size_mb: int = 10) -> bool:
    """Проверить размер файла"""
    size_mb = len(file_content) / (1024 * 1024)
    return size_mb <= max_size_mb

def get_file_extension(filename: str) -> str:
    """Получить расширение файла"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def is_supported_file(filename: str) -> bool:
    """Проверить, поддерживается ли файл"""
    supported_extensions = ['txt', 'pdf', 'doc', 'docx']
    extension = get_file_extension(filename)
    return extension in supported_extensions

def show_success_message(message: str, duration: int = 3):
    """Показать сообщение об успехе"""
    placeholder = st.empty()
    placeholder.success(message)
    # В реальном приложении здесь можно добавить таймер

def show_error_message(message: str):
    """Показать сообщение об ошибке"""
    st.error(f"❌ {message}")

def show_warning_message(message: str):
    """Показать предупреждение"""
    st.warning(f"⚠️ {message}")

def show_info_message(message: str):
    """Показать информационное сообщение"""
    st.info(f"ℹ️ {message}")

def create_download_button(data: str, filename: str, mime_type: str = "text/plain"):
    """Создать кнопку загрузки файла"""
    return st.download_button(
        label=f"📥 Скачать {filename}",
        data=data,
        file_name=filename,
        mime=mime_type,
        use_container_width=True
    )

def format_job_status_text(status: str) -> str:
    """Форматировать текст статуса задания"""
    status_texts = {
        'COMPLETED': 'Завершено',
        'ERROR': 'Ошибка',
        'PROCESSING': 'Обрабатывается',
        'QUEUED': 'В очереди'
    }
    return status_texts.get(status, status)

def get_language_name(language_code: str) -> str:
    """Получить название языка по коду"""
    languages = {
        'RU': '🇷🇺 Русский',
        'EN': '🇺🇸 English',
        'UNKNOWN': '🌐 Автоопределение'
    }
    return languages.get(language_code, language_code)

def get_summary_depth_name(depth: str) -> str:
    """Получить название глубины анализа"""
    depths = {
        'BULLET': '📋 Краткий',
        'DETAILED': '📖 Подробный'
    }
    return depths.get(depth, depth)

def estimate_analysis_cost(text_length: int, model_price: float) -> float:
    """Оценить стоимость анализа"""
    pages = calculate_pages_from_text_length(text_length)
    return pages * model_price

def calculate_pages_from_text_length(text_length: int) -> int:
    """Рассчитать страницы по длине текста"""
    # Примерно 2000 символов на страницу
    return max(1, text_length // 2000)

def format_file_size(size_bytes: int) -> str:
    """Форматировать размер файла"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

class SessionManager:
    """Менеджер состояния сессии"""
    
    @staticmethod
    def init_session_state():
        """Инициализировать состояние сессии"""
        if 'page_refresh_counter' not in st.session_state:
            st.session_state.page_refresh_counter = 0
    
    @staticmethod
    def increment_refresh_counter():
        """Увеличить счетчик обновлений страницы"""
        st.session_state.page_refresh_counter += 1
    
    @staticmethod
    def clear_cache():
        """Очистить кеш"""
        st.cache_data.clear()
    
    @staticmethod
    def force_refresh():
        """Принудительно обновить страницу"""
        st.cache_data.clear()
        st.rerun()

def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Безопасно получить значение из словаря"""
    return dictionary.get(key, default) if dictionary else default

def filter_jobs_by_status(jobs: List[Dict[str, Any]], status_filter: List[str]) -> List[Dict[str, Any]]:
    """Фильтровать задания по статусу"""
    if not status_filter:
        return jobs
    
    return [job for job in jobs if job.get('status') in status_filter]

def sort_jobs_by_date(jobs: List[Dict[str, Any]], ascending: bool = False) -> List[Dict[str, Any]]:
    """Сортировать задания по дате"""
    return sorted(
        jobs, 
        key=lambda x: x.get('started_at', ''), 
        reverse=not ascending
    )

def get_unique_statuses(jobs: List[Dict[str, Any]]) -> List[str]:
    """Получить уникальные статусы из списка заданий"""
    statuses = set()
    for job in jobs:
        if job.get('status'):
            statuses.add(job['status'])
    return sorted(list(statuses))