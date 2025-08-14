import streamlit as st
import sys
import os
import pandas as pd

# Добавляем родительскую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import check_authentication, show_user_info
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

# Проверяем авторизацию
if check_authentication():
    show_user_info()
else:
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.stop()

st.title("История")
st.markdown("Просмотр всех выполненных анализов договоров и их результатов")

# Получаем API клиент
api_client = get_api_client()

# Управление обновлением данных
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("### 📊 Ваши проверки")
with col2:
    if st.button("🔄 Обновить", use_container_width=True):
        SessionManager.clear_cache()
        st.rerun()

# Фильтры и настройки
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
            ["COMPLETED", "ERROR", "PROCESSING", "QUEUED"],
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
        show_charts = st.checkbox(
            "📊 Показать графики",
            value=True,
            help="Отображать аналитические графики"
        )

# Загрузка данных с кешированием
@st.cache_data(ttl=30)  # Кешируем на 30 секунд
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

# Загружаем данные
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

# Применяем фильтры
filtered_jobs = filter_jobs_by_status(jobs, status_filter) if status_filter else jobs
filtered_jobs = sort_jobs_by_date(filtered_jobs, ascending=False)

st.info(f"📊 Показано {len(filtered_jobs)} из {total_count} анализов")

# Показываем метрики
if filtered_jobs:
    display_job_metrics(filtered_jobs)
    

# Таблица с анализами
st.markdown("### 📋 Детализация анализов")

# Создаем DataFrame для отображения
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
    
    # Интерактивная таблица
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

# Детальный просмотр
if show_details and filtered_jobs:
    st.markdown("### 🔍 Подробная информация")
    
    for job in filtered_jobs:
        job_id = job.get('id')
        status = job.get('status', 'UNKNOWN')
        
        # Определяем цвет рамки на основе статуса
        border_colors = {
            'COMPLETED': '#28a745',
            'ERROR': '#dc3545',
            'PROCESSING': '#ffc107',
            'QUEUED': '#17a2b8'
        }
        border_color = border_colors.get(status, '#6c757d')
        
        with st.container():
            # Создаем рамку с цветом статуса
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding-left: 1rem; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            with st.expander(
                f"{get_status_emoji(status)} Анализ #{job_id} - {format_job_status_text(status)}", 
                expanded=False
            ):
                # Основная информация
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
                        st.write(f"**Риск-индекс:** {risk_percent:.1f}% ({risk_level})")
                
                with col3:
                    st.markdown("**📅 Временные метки:**")
                    if job.get('started_at'):
                        st.write(f"**Создан:** {format_datetime(job['started_at'])}")
                    if job.get('finished_at'):
                        st.write(f"**Завершен:** {format_datetime(job['finished_at'])}")
                    
                    # Время выполнения
                    if job.get('started_at') and job.get('finished_at'):
                        try:
                            start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                            end = datetime.fromisoformat(job['finished_at'].replace('Z', '+00:00'))
                            duration = end - start
                            st.write(f"**Время выполнения:** {duration.total_seconds():.1f} сек")
                        except:
                            pass
                
                # Результаты анализа
                if job.get('summary_text'):
                    st.markdown("**📋 Результаты анализа:**")
                    st.text_area(
                        "Сводка анализа:",
                        job['summary_text'],
                        height=200,
                        disabled=True,
                        key=f"summary_{job_id}"
                    )
                
                # Рисковые пункты
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
                
                # Действия с результатами
                if job.get('summary_text'):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Экспорт результатов
                        if st.button(f"📄 Экспорт результатов", key=f"export_{job_id}"):
                            risk_index = f"{job['risk_score']*100:.1f}%" if job.get('risk_score') else 'N/A'
                            risk_clauses_text = chr(10).join([f"{i+1}. {clause.get('clause_text', '')}" for i, clause in enumerate(job.get('risk_clauses', []))]) if job.get('risk_clauses') else 'Не выявлены'
                            
                            export_text = f"""АНАЛИЗ ДОГОВОРА #{job_id}
========================

Статус: {format_job_status_text(status)}
Дата создания: {format_datetime(job.get('started_at', ''))}
Риск-индекс: {risk_index}
Стоимость: {format_currency(float(job.get('used_credits', 0)))}

РЕЗУЛЬТАТЫ АНАЛИЗА:
{job.get('summary_text', 'Нет данных')}

Рисковые пункты:
{risk_clauses_text}
"""
                            st.download_button(
                                label="💾 Скачать отчет",
                                data=export_text,
                                file_name=f"analysis_report_{job_id}_{datetime.now().strftime('%Y%m%d')}.txt",
                                mime="text/plain",
                                key=f"download_{job_id}"
                            )
                    
                    with col2:
                        # Кнопка повторного анализа
                        if st.button(f"🔄 Повторить анализ", key=f"repeat_{job_id}"):
                            st.info("🔄 Функция повторного анализа будет добавлена в следующих версиях")
            
            st.markdown("</div>", unsafe_allow_html=True)

# Пагинация (если есть больше записей)
if total_count > len(jobs):
    st.markdown("---")
    st.info(f"📊 Показано {len(jobs)} из {total_count} записей")
    
    if st.button("📈 Загрузить больше данных"):
        # Увеличиваем лимит и перезагружаем
        new_limit = min(limit * 2, total_count)
        st.session_state.history_limit = new_limit
        SessionManager.clear_cache()
        st.rerun()

# Экспорт всех данных
if filtered_jobs:
    st.markdown("---")
    st.markdown("### 📊 Экспорт данных")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Экспорт в CSV", use_container_width=True):
            csv_data = pd.DataFrame([{
                'ID': job.get('id'),
                'Статус': job.get('status'),
                'Риск_индекс': job.get('risk_score'),
                'Стоимость': job.get('used_credits'),
                'Дата_создания': job.get('started_at'),
                'Дата_завершения': job.get('finished_at'),
                'Сводка': job.get('summary_text', '')[:100] + '...' if job.get('summary_text') else ''
            } for job in filtered_jobs]).to_csv(index=False)
            
            st.download_button(
                label="💾 Скачать CSV",
                data=csv_data,
                file_name=f"analysis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Экспорт статистики", use_container_width=True):
            stats_text = f"""
СТАТИСТИКА АНАЛИЗОВ
===================

Общее количество анализов: {len(filtered_jobs)}
Завершено успешно: {len([j for j in filtered_jobs if j.get('status') == 'COMPLETED'])}
Ошибок: {len([j for j in filtered_jobs if j.get('status') == 'ERROR'])}
В обработке: {len([j for j in filtered_jobs if j.get('status') == 'PROCESSING'])}

Общая стоимость: {sum([float(j.get('used_credits', 0)) for j in filtered_jobs]):.2f}₽
Средняя стоимость: {sum([float(j.get('used_credits', 0)) for j in filtered_jobs])/len(filtered_jobs):.2f}₽

Средний риск-индекс: {sum([j.get('risk_score', 0) for j in filtered_jobs if j.get('risk_score')])/len([j for j in filtered_jobs if j.get('risk_score')])*100:.1f}%
"""
            
            st.download_button(
                label="💾 Скачать статистику",
                data=stats_text,
                file_name=f"analysis_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    with col3:
        if st.button("🔄 Очистить фильтры", use_container_width=True):
            st.rerun()

# Боковая панель с дополнительными функциями
with st.sidebar:
    if st.button("🏠 Главное меню", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("### 📊 Статистика")
    
    if filtered_jobs:
        # Общая статистика
        total_cost = sum([float(j.get('used_credits', 0)) for j in filtered_jobs])
        avg_cost = total_cost / len(filtered_jobs) if filtered_jobs else 0
        
        st.metric("💰 Общая стоимость", format_currency(total_cost))
        st.metric("📊 Средняя стоимость", format_currency(avg_cost))
        
        # Статусы
        status_counts = {}
        for job in filtered_jobs:
            status = job.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        st.markdown("**📈 По статусам:**")
        for status, count in status_counts.items():
            emoji = get_status_emoji(status)
            st.write(f"{emoji} **{format_job_status_text(status)}:** {count}")
    
