import streamlit as st
import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.auth_service import (
    check_authentication, 
    login_form, 
    register_form, 
    logout, 
    init_session_state,
    show_user_info
)
from services.api_client import get_api_client
from utils.helpers import SessionManager, format_currency
from utils.style_loader import load_theme
import plotly.express as px

# Page Configuration  
st.set_page_config(
    page_title="Платформа анализа договоров",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide default Streamlit page navigation
st.markdown("""
<style>
    section[data-testid="stSidebarNav"] {
        display: none !important;
    }
    .css-1544g2n {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session and load theme
init_session_state()
SessionManager.init_session_state()
load_theme()


def main():
    """Главная функция приложения"""
    
    # Боковая панель
    with st.sidebar:
        st.markdown('<h1 class="sidebar-main-title">Платформа для анализа договоров</h1>', unsafe_allow_html=True)
        st.markdown("Интеллектуальный анализ юридических документов")
        
        # Информация для неавторизованных пользователей - ближе к заголовку
        if not check_authentication():
            st.markdown('<div class="auth-info-section"><p class="auth-required-text"><strong>Для доступа ко всем функциям необходимо войти в систему</strong></p></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Информация о пользователе
        show_user_info()
    
        # Навигация без заголовка
        
        if check_authentication():
            if st.button("Анализировать документ", use_container_width=True):
                st.switch_page("pages/New_Analysis.py")
            if st.button("История", use_container_width=True):
                st.switch_page("pages/History.py")
            if st.button("Баланс", use_container_width=True):
                st.switch_page("pages/Wallet.py")
            
            st.markdown("---")
            
            # Быстрая информация
            try:
                api_client = get_api_client()
                wallet_info = api_client.get_wallet_info()
                
                st.markdown("### 💰 Быстрая информация")
                st.metric(
                    "Текущий баланс", 
                    format_currency(float(wallet_info.get('balance', 0)))
                )
                
            except Exception as e:
                st.sidebar.warning("Не удалось загрузить быструю информацию")
        

    # Основной контент
    if check_authentication():
        show_dashboard()
    else:
        show_welcome_page()

def show_welcome_page():
    """Страница приветствия для неавторизованных пользователей"""
    st.markdown('<h1 class="main-header">Платформа для анализа договоров</h1>', unsafe_allow_html=True)
    
    # Описание системы
    st.markdown("""
    ### 🎯 Добро пожаловать в систему интеллектуального анализа договоров!
    
    Наша платформа поможет вам:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h4>🔍 Анализ рисков</h4>
            <p>Автоматическое выявление потенциально опасных пунктов в договорах</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>📊 Оценка документов</h4>
            <p>Получение числового риск-индекса для каждого документа</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h4>📝 Генерация сводок</h4>
            <p>Создание краткого и подробного анализа содержания</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Вкладки для авторизации
    tab1, tab2 = st.tabs(["Вход в систему", "Регистрация"])
    
    with tab1:
        login_form()
    
    with tab2:
        register_form()
    
    # Дополнительная информация
    with st.expander("📚 Подробнее о системе", expanded=False):
        st.markdown("""
        ### 🛠️ Технические возможности:
        
        **Поддерживаемые форматы:**
        - 📄 TXT - текстовые файлы
        - 📄 PDF - документы PDF
        - 📄 DOC/DOCX - документы Microsoft Word
        
        **Поддерживаемые языки:**
        - 🇷🇺 Русский
        - 🇺🇸 English
        - 🌐 Автоопределение языка
        
        **Модели анализа:**
        - Различные ML модели для разных типов документов
        - Гибкая система ценообразования
        - Высокая точность анализа
        
        **Безопасность:**
        - Защищенное хранение данных
        - Аутентификация пользователей
        - Логирование всех операций
        """)

def show_dashboard():
    """Главная панель для авторизованных пользователей"""
    st.markdown('<h1 class="main-header">Панель управления</h1>', unsafe_allow_html=True)
    
    try:
        api_client = get_api_client()
        
        # Загружаем данные
        with st.spinner("📊 Загружаем данные кошелька..."):
            wallet_info = api_client.get_wallet_info()
        
        # Попробуем загрузить историю, но если не получится - продолжим
        recent_jobs = {"jobs": [], "total_count": 0}
        try:
            recent_jobs = api_client.get_prediction_history(limit=10)
        except Exception as e:
            # Более детальная обработка ошибок
            error_msg = str(e)
            if "500" in error_msg:
                st.warning("⚠️ Сервер временно недоступен. Попробуйте позже.")
            elif "404" in error_msg:
                st.info("ℹ️ Функция истории анализов временно недоступна.")
            elif "401" in error_msg or "403" in error_msg:
                st.error("🔒 Ошибка авторизации. Пожалуйста, войдите в систему заново.")
            else:
                st.warning(f"⚠️ Не удалось загрузить историю анализов: {error_msg}")
            
        # Основные метрики
        st.markdown("### 📈 Основные показатели")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            balance = float(wallet_info.get('balance', 0))
            st.metric(
                "💰 Баланс",
                format_currency(balance),
                delta="Доступно для анализов"
            )
        
        with col2:
            total_jobs = recent_jobs.get('total_count', 0)
            st.metric(
                "📊 Всего анализов",
                total_jobs
            )
        
        with col3:
            jobs = recent_jobs.get('jobs', [])
            completed_jobs = len([j for j in jobs if j.get('status') == 'DONE'])
            st.metric(
                "✅ Завершено",
                completed_jobs,
                delta=f"из {len(jobs)}" if jobs else "0"
            )
        
        with col4:
            # Средний риск-индекс
            risk_scores = [j.get('risk_score') for j in jobs if j.get('risk_score') is not None]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
            st.metric(
                "⚠️ Средний риск",
                f"{avg_risk*100:.1f}%" if avg_risk > 0 else "N/A",
                delta="За последние анализы"
            )
        
        # Быстрые действия
        st.markdown("### 🚀 Быстрые действия")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Анализировать документ", use_container_width=True, type="primary"):
                st.switch_page("pages/New_Analysis.py")
        
        with col2:
            if st.button("Посмотреть историю", use_container_width=True):
                st.switch_page("pages/History.py")
        
        with col3:
            if st.button("Управление кошельком", use_container_width=True):
                st.switch_page("pages/Wallet.py")
        
        with col4:
            if st.button("Обновить данные", use_container_width=True):
                SessionManager.clear_cache()
                st.rerun()
        
        
        if not jobs:
            st.info("📭 У вас пока нет выполненных анализов")
            st.markdown("👆 Создайте свой первый анализ, используя кнопку выше!")
    
    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {str(e)}")
        st.info("🔄 Попробуйте обновить страницу")

# ИСПРАВЛЕНИЕ ВСЕХ КНОПОК И ТЕКСТА
st.markdown("""
<style>
/* SIDEBAR: МАКСИМАЛЬНО АГРЕССИВНО ЧЕРНЫЙ - ВСЕ ЭЛЕМЕНТЫ */
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div,
section[data-testid="stSidebar"] > div > div > div,
section[data-testid="stSidebar"] > div > div > div > div,
[data-testid="stSidebar"] *,
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
.css-1d391kg, .css-1lcbmhc, .css-1aumxhk {
    background: #1a1a1a !important;
    background-color: #1a1a1a !important;
}

/* НЕ ДАВАТЬ КНОПКАМ И ИХ ТЕКСТУ НАСЛЕДОВАТЬ ЧЕРНЫЙ ФОН */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] .stButton > button {
    background: #555555 !important;
    background-color: #555555 !important;
}

/* ПРОЗРАЧНЫЙ ФОН ДЛЯ ТЕКСТА ВНУТРИ КНОПОК SIDEBAR */
section[data-testid="stSidebar"] button *,
section[data-testid="stSidebar"] .stButton > button *,
section[data-testid="stSidebar"] button div,
section[data-testid="stSidebar"] button span {
    background: transparent !important;
    background-color: transparent !important;
    color: #ffffff !important;
}

/* SIDEBAR: КНОПКИ - СЕРЫЕ С ЧЕТКИМ БЕЛЫМ ТЕКСТОМ */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] [role="button"] {
    background-color: #555555 !important;
    color: #ffffff !important;
    border: 2px solid #777777 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #666666 !important;
    color: #ffffff !important;
    border: 2px solid #888888 !important;
}

/* SIDEBAR: БЕЛЫЙ ТЕКСТ */
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div {
    color: #ffffff !important;
}

/* ОСНОВНЫЕ КНОПКИ: ТЕМНЫЕ С БЕЛЫМ ТЕКСТОМ */
.stButton > button {
    background-color: #333333 !important;
    color: #ffffff !important;
    border: 2px solid #555555 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

.stButton > button:hover {
    background-color: #444444 !important;
    color: #ffffff !important;
    border: 2px solid #666666 !important;
}

/* ПРИНУДИТЕЛЬНЫЙ БЕЛЫЙ ТЕКСТ НА ВСЕХ КНОПКАХ */
button, button *, 
.stButton > button, .stButton > button *,
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] button * {
    color: #ffffff !important;
    text-decoration: none !important;
}

/* УБИРАЕМ БЕЛЫЕ ПОЛОСЫ ВНУТРИ КНОПОК */
.stButton > button > div,
.stButton > button > span,
.stButton > button div,
.stButton > button span {
    background: transparent !important;
    background-color: transparent !important;
    color: #ffffff !important;
}

/* ДОПОЛНИТЕЛЬНОЕ ИСПРАВЛЕНИЕ ДЛЯ ВНУТРЕННИХ ЭЛЕМЕНТОВ КНОПОК */
button div, button span,
.stButton div, .stButton span {
    background: transparent !important;
    background-color: transparent !important;
    color: inherit !important;
}
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()