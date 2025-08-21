import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import check_authentication, show_user_info, init_session_state
from services.api_client import get_api_client
from utils.helpers import (
    format_datetime, format_currency, format_percentage,
    get_status_emoji, format_job_status_text, get_unique_statuses,
    filter_jobs_by_status, sort_jobs_by_date, SessionManager
)
from components.visualization import (
    display_job_metrics, create_status_pie_chart, create_risk_histogram,
    create_cost_timeline, format_status_badge
)
from utils.style_loader import load_theme
from datetime import datetime


load_theme()


init_session_state()
if not check_authentication():
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.info("👈 Перейдите на главную страницу для входа в систему")
    st.stop()

st.title("История")
st.markdown("Просмотр всех выполненных анализов договоров и их результатов")

api_client = get_api_client()


col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("### 📊 Ваши проверки")
with col2:
    if st.button("🔄 Обновить", use_container_width=True):
        SessionManager.clear_cache()
        st.rerun()

with st.expander("🔧 Фильтры и настройки", expanded=False):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        limit = st.selectbox(
            "📊 Показать записей:",
            [10, 20, 50, 100],
            index=1,
            help="Количество записей для загрузки"
        )
    
    with col2:
        status_filter = st.multiselect(
            "📈 Статус:",
            ["DONE", "ERROR", "PROCESSING", "QUEUED"],
            default=[],
            help="Фильтр по статусу анализа"
        )
    
    with col3:
        show_details = st.checkbox(
            "📄 Показать детали",
            value=True,
            help="Отображать подробную информацию"
        )
    
    with col4:
        st.markdown("")


@st.cache_data(ttl=30)
def load_prediction_history(limit_param):
    try:
        return api_client.get_prediction_history(limit=limit_param)
    except Exception as e:
        error_msg = str(e)
        if "500" in error_msg:
            st.error("❌ Сервер временно недоступен. История не может быть загружена.")
            st.info("💡 Попробуйте обновить страницу через несколько минут или обратитесь к администратору.")
        elif "404" in error_msg:
            st.warning("⚠️ Endpoint истории анализов не найден.")
        elif "401" in error_msg or "403" in error_msg:
            st.error("🔒 Ошибка авторизации. Пожалуйста, войдите в систему заново.")
        else:
            st.error(f"❌ Ошибка загрузки истории: {error_msg}")
        return {"jobs": [], "total_count": 0}

with st.spinner("📊 Загружаем историю анализов..."):
    history_data = load_prediction_history(limit)

jobs = history_data.get("jobs", [])
total_count = history_data.get("total_count", 0)

if not jobs:
    st.info("📭 У вас пока нет выполненных анализов")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Создать первый анализ", use_container_width=True, type="primary"):
            st.switch_page("pages/New_Analysis.py")
    
    with col2:
        if st.button("🏠 Вернуться на главную", use_container_width=True):
            st.switch_page("app.py")
    
    st.stop()

filtered_jobs = filter_jobs_by_status(jobs, status_filter) if status_filter else jobs
filtered_jobs = sort_jobs_by_date(filtered_jobs, ascending=False)

st.info(f"📊 Показано {len(filtered_jobs)} из {total_count} анализов")

if filtered_jobs:
    display_job_metrics(filtered_jobs)
    


st.markdown("### 📋 Детализация анализов")


display_data = []
for job in filtered_jobs:
    display_data.append({
        'ID': job.get('id', 'N/A'),
        'Статус': format_status_badge(job.get('status', 'UNKNOWN')),
        'Риск-индекс': f"{job['risk_score']*100:.1f}%" if job.get('risk_score') is not None else "N/A",
        'Стоимость': format_currency(float(job.get('used_credits', 0))),
        'Глубина': job.get('summary_depth', 'N/A'),
        'Дата создания': format_datetime(job.get('started_at', '')),
        'Дата завершения': format_datetime(job.get('finished_at', '')) if job.get('finished_at') else "N/A"
    })

if display_data:
    df = pd.DataFrame(display_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn("Статус", width="small"),
            "Риск-индекс": st.column_config.TextColumn("Риск-индекс", width="small"),
            "Стоимость": st.column_config.TextColumn("Стоимость", width="small"),
        }
    )


if show_details and filtered_jobs:
    st.markdown("### 🔍 Подробная информация")
    
    for job in filtered_jobs:
        job_id = job.get('id')
        status = job.get('status', 'UNKNOWN')
        

        border_colors = {
            'DONE': '#28a745',
            'COMPLETED': '#28a745', 
            'ERROR': '#dc3545',
            'PROCESSING': '#ffc107',
            'QUEUED': '#17a2b8'
        }
        border_color = border_colors.get(status, '#6c757d')
        
        with st.container():
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding-left: 1rem; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            with st.expander(
                f"{get_status_emoji(status)} Анализ #{job_id} - {format_job_status_text(status)}", 
                expanded=False
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**📊 Основные данные:**")
                    st.write(f"**Статус:** {format_job_status_text(status)}")
                    st.write(f"**Глубина анализа:** {job.get('summary_depth', 'N/A')}")
                
                with col2:
                    st.markdown("**💰 Финансовая информация:**")
                    if job.get('used_credits'):
                        st.write(f"**Стоимость:** {format_currency(float(job['used_credits']))}")
                    if job.get('risk_score') is not None:
                        risk_percent = job['risk_score'] * 100
                        risk_level = "Высокий" if risk_percent > 70 else "Средний" if risk_percent > 30 else "Низкий"
                        if risk_percent > 70:
                            color = "#dc3545" 
                        elif risk_percent > 30:
                            color = "#ffc107" 
                        else:
                            color = "#28a745" 
                        
                        st.write(f"**Риск-индекс:** {risk_percent:.1f}% ({risk_level})")
                        st.progress(risk_percent / 100, text=f"Уровень риска: {risk_level}")
        
                    if job.get('risk_clauses'):
                        risk_count = len(job['risk_clauses'])
                        high_risk_count = len([c for c in job['risk_clauses'] if c.get('risk_level') == 'HIGH'])
                        st.write(f"**Найдено рисков:** {risk_count} (критических: {high_risk_count})")
                
                with col3:
                    st.markdown("**📅 Временные метки:**")
                    if job.get('started_at'):
                        st.write(f"**Создан:** {format_datetime(job['started_at'])}")
                    if job.get('finished_at'):
                        st.write(f"**Завершен:** {format_datetime(job['finished_at'])}")
                    
                    if job.get('started_at') and job.get('finished_at'):
                        try:
                            start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                            end = datetime.fromisoformat(job['finished_at'].replace('Z', '+00:00'))
                            duration = end - start
                            st.write(f"**Время выполнения:** {duration.total_seconds():.1f} сек")
                        except:
                            pass
                
                if job.get('summary_text'):
                    st.markdown("**📋 Результаты анализа:**")
                    st.text_area(
                        "Сводка анализа:",
                        job['summary_text'],
                        height=200,
                        disabled=True,
                        key=f"summary_{job_id}"
                    )
                
    
                if job.get('risk_clauses') and len(job['risk_clauses']) > 0:
                    st.markdown("**⚠️ Выявленные рисковые пункты:**")
                    
                    for i, clause in enumerate(job['risk_clauses'], 1):
                        risk_level = clause.get('risk_level', 'UNKNOWN')
                        risk_colors = {
                            'HIGH': '#dc3545',
                            'MEDIUM': '#ffc107', 
                            'LOW': '#28a745'
                        }
                        risk_color = risk_colors.get(risk_level, '#6c757d')
                        
                        st.markdown(f"""
                        <div style="border-left: 3px solid {risk_color}; padding-left: 0.5rem; margin: 0.5rem 0;">
                        <strong>{i}. Уровень риска: {risk_level}</strong><br>
                        {clause.get('clause_text', 'Текст недоступен')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if clause.get('explanation'):
                            st.write(f"*💡 Пояснение: {clause['explanation']}*")
                        
                        if i < len(job['risk_clauses']):
                            st.markdown("---")
                
            
            st.markdown("</div>", unsafe_allow_html=True)

if total_count > len(jobs):
    st.markdown("---")
    st.info(f"📊 Показано {len(jobs)} из {total_count} записей")
    
    if st.button("📈 Загрузить больше данных"):
        new_limit = min(limit * 2, total_count)
        st.session_state.history_limit = new_limit
        SessionManager.clear_cache()
        st.rerun()

if filtered_jobs:
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Очистить фильтры", use_container_width=True):
            st.rerun()
    
    with col2:
        st.empty()

with st.sidebar:
    st.markdown('<h1 class="sidebar-main-title">Платформа для анализа договоров</h1>', unsafe_allow_html=True)
    st.markdown("Интеллектуальный анализ юридических документов")
    
    st.markdown("---")
    
    show_user_info()
    
    if st.button("Анализировать документ", use_container_width=True):
        st.switch_page("pages/New_Analysis.py")
    if st.button("История", use_container_width=True, disabled=True):
        pass
    if st.button("Баланс", use_container_width=True):
        st.switch_page("pages/Wallet.py")
    
