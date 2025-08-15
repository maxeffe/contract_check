import streamlit as st
import sys
import os

# Добавляем родительскую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import protected_page, check_authentication, show_user_info
from services.api_client import get_api_client
from utils.helpers import (
    calculate_pages_from_text, validate_file_size, is_supported_file,
    format_currency, get_language_name, get_summary_depth_name,
    show_success_message, show_error_message
)
from utils.style_loader import load_theme

# Загружаем тему для скрытия Streamlit элементов
load_theme()

# ИСПРАВЛЕНИЕ SIDEBAR - ЧЕРНЫЙ ФОН С СЕРЫМИ КНОПКАМИ
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
</style>
""", unsafe_allow_html=True)

# Применяем защиту страницы
if check_authentication():
    show_user_info()
else:
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.stop()

st.title("Анализ документа")
st.markdown("Загрузите документ или введите текст для интеллектуального анализа рисков")

# Получаем API клиент
api_client = get_api_client()

# Загружаем доступные модели
@st.cache_data(ttl=300)  # Кешируем на 5 минут
def get_available_models():
    try:
        return api_client.get_available_models()
    except Exception as e:
        st.error(f"Ошибка загрузки моделей: {e}")
        return []

models = get_available_models()

# Проверяем баланс пользователя
@st.cache_data(ttl=30)
def get_user_balance():
    try:
        wallet_info = api_client.get_wallet_info()
        return float(wallet_info.get('balance', 0))
    except Exception as e:
        st.warning("Не удалось проверить баланс")
        return 0.0

user_balance = get_user_balance()

# Показываем текущий баланс
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("")  # Пустая колонка
with col2:
    st.metric("💰 Текущий баланс", format_currency(user_balance))

# Выбор способа ввода
st.markdown("### 📄 Выберите способ ввода документа")

input_method = st.radio(
    "",
    ["📝 Ввести текст вручную", "📄 Загрузить файл"],
    horizontal=True
)

# Основная форма анализа
with st.form("prediction_form", clear_on_submit=False):
    document_text = ""
    filename = ""
    uploaded_file = None
    estimated_pages = 0
    
    if input_method == "📝 Ввести текст вручную":
        st.markdown("#### ✏️ Ввод текста")
        
        document_text = st.text_area(
            "Введите текст договора:",
            height=300,
            help="Введите текст договора для анализа (минимум 10 символов)",
            placeholder="Вставьте сюда текст вашего договора..."
        )
        
        filename = st.text_input(
            "Название документа (опционально):",
            placeholder="Например: Договор поставки 2024.txt"
        )
        
        # Подсчет символов и страниц
        if document_text:
            char_count = len(document_text)
            word_count = len(document_text.split())
            estimated_pages = calculate_pages_from_text(document_text)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 Символов", char_count)
            with col2:
                st.metric("📖 Слов", word_count)
            with col3:
                st.metric("📄 Страниц", estimated_pages)
        
    else:  # Загрузка файла
        st.markdown("#### 📤 Загрузка файла")
        
        uploaded_file = st.file_uploader(
            "Выберите файл для анализа:",
            type=['txt', 'pdf', 'doc', 'docx'],
            help="Поддерживаемые форматы: TXT, PDF, DOC, DOCX (макс. 10 МБ)",
            accept_multiple_files=False
        )
        
        if uploaded_file:
            file_size = len(uploaded_file.getvalue())
            
            # Проверяем размер файла
            if not validate_file_size(uploaded_file.getvalue(), 10):
                st.error("❌ Файл слишком большой! Максимальный размер: 10 МБ")
            elif not is_supported_file(uploaded_file.name):
                st.error("❌ Неподдерживаемый формат файла!")
            else:
                st.success(f"✅ Файл загружен: {uploaded_file.name}")
                
                # Показываем информацию о файле
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"📁 **Имя файла:** {uploaded_file.name}")
                    st.write(f"📏 **Размер:** {file_size/1024:.1f} КБ")
                with col2:
                    # Приблизительная оценка страниц
                    estimated_pages = max(1, file_size // 2000)  # Примерно 2000 символов на страницу
                    st.write(f"📄 **Примерно страниц:** {estimated_pages}")
                    st.write(f"🗂️ **Тип:** {uploaded_file.type}")
    
    st.markdown("---")
    
    # Параметры анализа
    st.markdown("#### ⚙️ Параметры анализа")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        language = st.selectbox(
            "🌐 Язык документа:",
            ["UNKNOWN", "RU", "EN"],
            format_func=get_language_name,
            help="Выберите язык документа или оставьте автоопределение"
        )
    
    with col2:
        if models:
            model_options = [(model['name'], model['price_per_page'], model['id']) for model in models]
            selected_model_idx = st.selectbox(
                "🤖 Модель анализа:",
                range(len(model_options)),
                format_func=lambda x: f"{model_options[x][0]} ({format_currency(model_options[x][1])}/стр)",
                help="Выберите модель для анализа документа"
            )
            model_name, model_price, model_id = model_options[selected_model_idx]
        else:
            model_name = "default_model"
            model_price = 1.0
            st.selectbox("🤖 Модель анализа:", ["default_model (недоступно)"])
    
    with col3:
        summary_depth = st.selectbox(
            "📊 Глубина анализа:",
            ["BULLET", "DETAILED"],
            format_func=get_summary_depth_name,
            help="Краткий анализ - основные риски, подробный - развернутый отчет"
        )
    
    # Расчет стоимости
    if (document_text or uploaded_file) and models:
        if document_text:
            estimated_pages = calculate_pages_from_text(document_text)
        elif uploaded_file:
            file_size = len(uploaded_file.getvalue())
            estimated_pages = max(1, file_size // 2000)
        
        estimated_cost = estimated_pages * model_price
        
        # Показываем оценку стоимости
        st.markdown("#### 💰 Оценка стоимости")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📄 Страниц", estimated_pages)
        with col2:
            st.metric("💵 За страницу", format_currency(model_price))
        with col3:
            st.metric("💰 Итого", format_currency(estimated_cost))
        with col4:
            balance_after = user_balance - estimated_cost
            st.metric(
                "🏦 Останется",
                format_currency(balance_after),
                delta=format_currency(-estimated_cost) if balance_after >= 0 else None
            )
        
        # Предупреждение о недостатке средств
        if estimated_cost > user_balance:
            st.error(f"❌ Недостаточно средств! Требуется: {format_currency(estimated_cost)}, доступно: {format_currency(user_balance)}")
            st.info("💡 Пополните баланс в разделе 'Кошелек' для продолжения работы")
    
    st.markdown("---")
    
    # Кнопка отправки
    col1, col2 = st.columns([2, 1])
    with col1:
        submitted = st.form_submit_button(
            "🚀 Запустить анализ", 
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        if st.form_submit_button("🔄 Очистить форму", use_container_width=True):
            st.rerun()
    
    # Обработка отправки формы
    if submitted:
        # Валидация
        error_messages = []
        
        if input_method == "📝 Ввести текст вручную":
            if not document_text or len(document_text.strip()) < 10:
                error_messages.append("Текст документа должен содержать минимум 10 символов")
            if len(document_text) > 1000000:
                error_messages.append("Текст документа слишком длинный (максимум 1,000,000 символов)")
        else:
            if not uploaded_file:
                error_messages.append("Пожалуйста, выберите файл для загрузки")
            elif not validate_file_size(uploaded_file.getvalue(), 10):
                error_messages.append("Файл слишком большой (максимум 10 МБ)")
            elif not is_supported_file(uploaded_file.name):
                error_messages.append("Неподдерживаемый формат файла")
        
        # Проверка баланса
        if models and estimated_cost > user_balance:
            error_messages.append(f"Недостаточно средств (требуется {format_currency(estimated_cost)})")
        
        # Показываем ошибки
        if error_messages:
            for msg in error_messages:
                st.error(f"❌ {msg}")
        else:
            # Выполняем анализ
            try:
                with st.spinner("🔄 Отправляем документ на анализ..."):
                    if input_method == "📝 Ввести текст вручную":
                        # Создаем анализ через текст
                        prediction_data = {
                            "document_text": document_text,
                            "filename": filename or "manual_input.txt",
                            "language": language,
                            "model_name": model_name,
                            "summary_depth": summary_depth
                        }
                        
                        response = api_client.create_prediction(prediction_data)
                    
                    else:
                        # Создаем анализ через файл
                        file_content = uploaded_file.getvalue()
                        response = api_client.upload_file_prediction(
                            file_content, 
                            uploaded_file.name, 
                            language
                        )
                
                # Успешная отправка
                st.success("🎉 Анализ успешно запущен!")
                
                # Очищаем кеш для обновления баланса
                st.cache_data.clear()
                
                # Отображаем информацию о задаче
                st.markdown("### ✅ Информация о созданной задаче")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🆔 ID задачи", response['job_id'])
                    st.metric("💰 Стоимость", format_currency(response['cost']))
                with col2:
                    st.metric("📄 Страниц обработано", response['pages_processed'])
                    st.metric("📊 Статус", response['status'])
                
                # Информационное сообщение
                st.info(f"📝 {response.get('message', 'Задача поставлена в очередь на обработку')}")
                
                # Сохраняем состояние успешного создания
                st.session_state.analysis_created = True
                st.session_state.job_id = response['job_id']
                
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ Ошибка создания анализа: {error_msg}")
                
                # Дополнительные действия на основе типа ошибки
                if "Insufficient balance" in error_msg:
                    st.info("💡 Пополните баланс кошелька для продолжения работы")
                    st.session_state.show_wallet_button = True
                
                elif "queue" in error_msg.lower():
                    st.warning("⚠️ Система временно недоступна. Попробуйте позже.")
                
                else:
                    st.info("🔄 Попробуйте еще раз или обратитесь в поддержку")

# Кнопки действий вне формы
if st.session_state.get('analysis_created', False):
    st.markdown("---")
    st.markdown("### 🎯 Следующие действия")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Перейти к истории", use_container_width=True, key="goto_history"):
            st.session_state.analysis_created = False  # Сбрасываем состояние
            st.switch_page("pages/History.py")
    
    with col2:
        if st.button("📝 Создать еще один анализ", use_container_width=True, key="create_new"):
            st.session_state.analysis_created = False  # Сбрасываем состояние
            st.rerun()

# Кнопка перехода к кошельку при недостатке баланса
if st.session_state.get('show_wallet_button', False):
    st.markdown("---")
    if st.button("💳 Перейти к кошельку", use_container_width=True, key="goto_wallet"):
        st.session_state.show_wallet_button = False  # Сбрасываем состояние
        st.switch_page("pages/Wallet.py")

# Боковая панель
with st.sidebar:
    if st.button("🏠 Главное меню", use_container_width=True):
        st.switch_page("app.py")