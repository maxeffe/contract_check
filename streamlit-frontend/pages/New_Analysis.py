import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import protected_page, check_authentication, show_user_info, init_session_state
from services.api_client import get_api_client
from utils.helpers import (
    calculate_pages_from_text, calculate_tokens_from_text, validate_file_size, is_supported_file,
    format_currency, get_language_name, get_summary_depth_name,
    show_success_message, show_error_message, calculate_pages_from_file_size, 
    calculate_tokens_from_file_size, get_file_extension
)
from utils.style_loader import load_theme

load_theme()


init_session_state()
if not check_authentication():
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.info("👈 Перейдите на главную страницу для входа в систему")
    st.stop()

st.title("Анализ документа")
st.markdown("Загрузите документ или введите текст для интеллектуального анализа рисков")

api_client = get_api_client()

@st.cache_data(ttl=300) 
def get_available_models():
    try:
        return api_client.get_available_models()
    except Exception as e:
        st.error(f"Ошибка загрузки моделей: {e}")
        return []

models = get_available_models()

@st.cache_data(ttl=30)
def get_user_balance():
    try:
        wallet_info = api_client.get_wallet_info()
        return float(wallet_info.get('balance', 0))
    except Exception as e:
        st.warning("Не удалось проверить баланс")
        return 0.0

user_balance = get_user_balance()

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("💰 Текущий баланс", format_currency(user_balance))
with col2:
    st.markdown("")

st.markdown("### 📄 Выберите способ ввода документа")

input_method = st.radio(
    "",
    ["📝 Ввести текст вручную", "📄 Загрузить файл"],
    horizontal=True
)

uploaded_file = None
if input_method == "📄 Загрузить файл":
    st.markdown("#### 📤 Загрузка файла")
    
    uploaded_file = st.file_uploader(
        "Выберите файл для анализа:",
        type=['txt', 'pdf', 'doc', 'docx'],
        help="Поддерживаемые форматы: TXT, PDF, DOC, DOCX (макс. 10 МБ)",
        accept_multiple_files=False
    )
    
    if uploaded_file:
        file_size = len(uploaded_file.getvalue())
        
        if not validate_file_size(uploaded_file.getvalue(), 10):
            st.error("❌ Файл слишком большой! Максимальный размер: 10 МБ")
        elif not is_supported_file(uploaded_file.name):
            st.error("❌ Неподдерживаемый формат файла!")
        else:
            st.success(f"✅ Файл загружен: {uploaded_file.name}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"📁 **Имя файла:** {uploaded_file.name}")
                st.write(f"📏 **Размер:** {file_size/1024:.1f} КБ")
            with col2:
                pass
                st.write(f"🗂️ **Тип:** {uploaded_file.type}")

with st.form("prediction_form", clear_on_submit=False):
    document_text = ""
    filename = ""
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

        if document_text:
            char_count = len(document_text)
            word_count = len(document_text.split())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 Символов", char_count)
            with col2:
                st.metric("📖 Слов", word_count)
            with col3:
                pass
    
    st.markdown("---")
    
    st.markdown("#### ⚙️ Параметры анализа")
    
    col1, col2 = st.columns(2)
    
    language = "RU"
    
    with col1:
        if models:
            if 'price_per_token' in models[0]:
                model_options = [(model['name'], model['price_per_token'], model['id']) for model in models]
                price_label = "1000 токенов"
                display_price_func = lambda x: f"{model_options[x][0]} ({format_currency(model_options[x][1] * 1000)}/{price_label})"
            else:
                model_options = [(model['name'], model.get('price_per_page', 1), model['id']) for model in models]
                price_label = "стр"
                display_price_func = lambda x: f"{model_options[x][0]} ({format_currency(model_options[x][1])}/{price_label})"
                
            selected_model_idx = st.selectbox(
                "🤖 Модель анализа:",
                range(len(model_options)),
                format_func=display_price_func,
                help="Выберите модель для анализа документа"
            )
            model_name, model_price, model_id = model_options[selected_model_idx]
        else:
            model_name = "default_model"
            model_price = 1.0
            st.selectbox("🤖 Модель анализа:", ["default_model (недоступно)"])
    
    with col2:
        summary_depth = st.selectbox(
            "📊 Глубина анализа:",
            ["BULLET", "DETAILED"],
            format_func=get_summary_depth_name,
            help="Краткий анализ - основные риски, подробный - развернутый отчет"
        )
    
    if (document_text or uploaded_file) and models:
        try:
            if document_text:
                estimate = api_client.estimate_cost(text=document_text)
            elif uploaded_file:
                file_content = uploaded_file.getvalue()
                estimate = api_client.estimate_cost(file_content=file_content, filename=uploaded_file.name)
            
            api_token_count = estimate.get('token_count', 0)
            estimated_cost = estimate.get('estimated_cost', 0)
            
            if 'price_per_token' in models[0]:
                billing_unit = "токенов"
                billing_count = api_token_count
                price_per_unit = model_price * 1000 
                price_unit_label = "1000 токенов"
            else:
                billing_unit = "страниц"
                billing_count = estimated_pages
                price_per_unit = model_price
                price_unit_label = "страницу"
                
        except Exception as e:
            st.error(f"❌ Не удалось получить оценку стоимости: {str(e)}")
            st.info("🔄 Попробуйте создать анализ - стоимость будет рассчитана при обработке")
            api_token_count = 0
            estimated_cost = 0
            billing_unit = "токенов"
            billing_count = 0
            price_per_unit = model_price * 1000 if 'price_per_token' in models[0] else model_price
            price_unit_label = "1000 токенов" if 'price_per_token' in models[0] else "страницу"
        
        st.markdown("#### 💰 Оценка стоимости")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(f"🔢 {billing_unit.capitalize()}", billing_count)
        with col2:
            st.metric(f"💵 За {price_unit_label}", format_currency(price_per_unit))
        with col3:
            st.metric("💰 Итого", format_currency(estimated_cost))
        with col4:
            balance_after = user_balance - estimated_cost
            st.metric(
                "🏦 Останется",
                format_currency(balance_after),
                delta=format_currency(-estimated_cost) if balance_after >= 0 else None
            )
        
        if estimated_cost > user_balance:
            st.error(f"❌ Недостаточно средств! Требуется: {format_currency(estimated_cost)}, доступно: {format_currency(user_balance)}")
            st.info("💡 Пополните баланс в разделе 'Кошелек' для продолжения работы")
    
    st.markdown("---")

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

    if submitted:
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
        
        
        if error_messages:
            for msg in error_messages:
                st.error(f"❌ {msg}")
        else:

            try:
                with st.spinner("🔄 Отправляем документ на анализ..."):
                    if input_method == "📝 Ввести текст вручную":
 
                        prediction_data = {
                            "document_text": document_text,
                            "filename": filename or "manual_input.txt",
                            "language": language,
                            "model_name": model_name,
                            "summary_depth": summary_depth
                        }
                        
                        response = api_client.create_prediction(prediction_data)
                    
                    else:
                        file_content = uploaded_file.getvalue()
                        response = api_client.upload_file_prediction(
                            file_content, 
                            uploaded_file.name, 
                            language
                        )
                

                st.success("🎉 Анализ успешно запущен!")

                st.cache_data.clear()
                
                st.markdown("### ✅ Информация о созданной задаче")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Стоимость анализа", format_currency(response['cost']))
                with col2:
                    status_text = {
                        'QUEUED': 'В очереди на обработку',
                        'queued': 'В очереди на обработку',
                        'PROCESSING': 'Анализируется',
                        'processing': 'Анализируется',
                        'DONE': 'Завершен',
                        'done': 'Завершен',
                        'COMPLETED': 'Завершен',
                        'completed': 'Завершен',
                        'ERROR': 'Ошибка при обработке',
                        'error': 'Ошибка при обработке'
                    }.get(response['status'], response['status'])
                    st.metric("📊 Статус", status_text)

                st.info(f"📝 {response.get('message', 'Задача поставлена в очередь на обработку')}")
                
                st.session_state.analysis_created = True
                st.session_state.job_id = response['job_id']
                
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ Ошибка создания анализа: {error_msg}")
                
                if "Insufficient balance" in error_msg:
                    st.info("💡 Пополните баланс кошелька для продолжения работы")
                    st.session_state.show_wallet_button = True
                
                elif "queue" in error_msg.lower():
                    st.warning("⚠️ Система временно недоступна. Попробуйте позже.")
                
                else:
                    st.info("🔄 Попробуйте еще раз или обратитесь в поддержку")

if st.session_state.get('analysis_created', False):
    st.markdown("---")
    st.markdown("### 🎯 Следующие действия")
    
    if st.session_state.get('job_id'):
        job_id = st.session_state.job_id
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 Проверить статус", use_container_width=True, key="check_status"):
                try:
                    job_details = api_client.get_job_details(job_id)
                    status = job_details.get('status', 'UNKNOWN')
                    
                    if status == 'DONE':
                        st.success("✅ Анализ завершен!")
                        
                        if job_details.get('summary_text'):
                            st.markdown("**📋 Результаты анализа:**")
                            st.text_area(
                                "Полная сводка анализа:",
                                job_details['summary_text'],
                                height=300,
                                disabled=True
                            )
                            
                            import json
                            from datetime import datetime
                            
                            risk_index = f"{job_details['risk_score']*100:.1f}%" if job_details.get('risk_score') else 'N/A'
                            
                            risk_clauses_text = ""
                            if job_details.get('risk_clauses'):
                                risk_clauses_text = "\n".join([
                                    f"{i+1}. [{clause.get('risk_level', 'UNKNOWN')}] {clause.get('clause_text', '')}\n   Пояснение: {clause.get('explanation', 'Нет пояснения')}"
                                    for i, clause in enumerate(job_details.get('risk_clauses', []))
                                ])
                            else:
                                risk_clauses_text = "Рисковые пункты не выявлены"
                            
                            full_report = f"""ОТЧЕТ ПО АНАЛИЗУ ДОГОВОРА
====================================

ОБЩАЯ ИНФОРМАЦИЯ:
-----------------
Статус: Завершен
Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

ФИНАНСОВАЯ ИНФОРМАЦИЯ:
---------------------
Стоимость анализа: {format_currency(float(job_details.get('used_credits', 0)))}
Риск-индекс: {risk_index}

РЕЗУЛЬТАТЫ АНАЛИЗА:
------------------
{job_details.get('summary_text', 'Результаты анализа недоступны')}

ВЫЯВЛЕННЫЕ РИСКОВЫЕ ПУНКТЫ:
--------------------------
{risk_clauses_text}

Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Система анализа договоров v2.0
"""
                            
                            st.download_button(
                                label="📄 Скачать полный отчет",
                                data=full_report,
                                file_name=f"analysis_report_{job_id}_{datetime.now().strftime('%Y%m%d')}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        if job_details.get('risk_score') is not None:
                            risk_percent = job_details['risk_score'] * 100
                            st.metric("🎯 Риск-индекс", f"{risk_percent:.1f}%")
                            
                        if job_details.get('risk_clauses'):
                            unique_clauses = []
                            seen_texts = set()
                            for clause in job_details['risk_clauses']:
                                clause_text = clause.get('clause_text', '')
                                if clause_text and clause_text not in seen_texts:
                                    seen_texts.add(clause_text)
                                    unique_clauses.append(clause)
                            
                            st.write(f"**⚠️ Найдено рисков:** {len(unique_clauses)}")
                            
                            if unique_clauses:
                                st.markdown("**🚨 Выявленные рисковые пункты:**")
                                for i, clause in enumerate(unique_clauses, 1):
                                    risk_level = clause.get('risk_level', 'UNKNOWN')
                                    risk_colors = {
                                        'HIGH': '#dc3545',
                                        'MEDIUM': '#ffc107', 
                                        'LOW': '#28a745'
                                    }
                                    risk_color = risk_colors.get(risk_level, '#6c757d')
                                    
                                    risk_level_text = {
                                        'HIGH': 'Высокий',
                                        'MEDIUM': 'Средний',
                                        'LOW': 'Низкий'
                                    }.get(risk_level, risk_level)
                                    
                                    st.markdown(f"""
                                    <div style="border-left: 3px solid {risk_color}; padding-left: 0.5rem; margin: 0.5rem 0;">
                                    <strong>{i}. Уровень риска: {risk_level_text}</strong><br>
                                    {clause.get('clause_text', 'Текст недоступен')}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    if clause.get('explanation'):
                                        st.write(f"*💡 Пояснение: {clause['explanation']}*")
                                    
                                    if i < len(unique_clauses):
                                        st.markdown("---")
                    
                    elif status == 'PROCESSING':
                        st.info("🔄 Анализ в процессе выполнения...")
                    elif status == 'QUEUED':
                        st.info("⏳ Анализ находится в очереди...")
                    elif status == 'ERROR':
                        st.error("❌ Анализ завершился с ошибкой")
                    else:
                        st.warning(f"❓ Неизвестный статус: {status}")
                        
                except Exception as e:
                    st.error(f"Ошибка проверки статуса: {str(e)}")
        
        with col2:
            if st.button("📋 Перейти к истории", use_container_width=True, key="goto_history"):
                st.session_state.analysis_created = False
                st.switch_page("pages/History.py")
        
        with col3:
            if st.button("📝 Создать еще один анализ", use_container_width=True, key="create_new"):
                st.session_state.analysis_created = False
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Перейти к истории", use_container_width=True, key="goto_history"):
                st.session_state.analysis_created = False
                st.switch_page("pages/History.py")
        
        with col2:
            if st.button("📝 Создать еще один анализ", use_container_width=True, key="create_new"):
                st.session_state.analysis_created = False
                st.rerun()

if st.session_state.get('show_wallet_button', False):
    st.markdown("---")
    if st.button("💳 Перейти к кошельку", use_container_width=True, key="goto_wallet"):
        st.session_state.show_wallet_button = False
        st.switch_page("pages/Wallet.py")

with st.sidebar:
    st.markdown('<h1 class="sidebar-main-title">Платформа для анализа договоров</h1>', unsafe_allow_html=True)
    st.markdown("Интеллектуальный анализ юридических документов")
    
    st.markdown("---")
    
    show_user_info()
    
    if st.button("Анализировать документ", use_container_width=True, disabled=True):
        pass 
    if st.button("История", use_container_width=True):
        st.switch_page("pages/History.py")
    if st.button("Баланс", use_container_width=True):
        st.switch_page("pages/Wallet.py")