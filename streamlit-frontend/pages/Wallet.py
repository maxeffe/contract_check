import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Добавляем родительскую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import check_authentication, show_user_info
from services.api_client import get_api_client
from utils.helpers import (
    format_datetime, format_currency, SessionManager
)
from components.visualization import display_wallet_chart
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

# Проверяем авторизацию
if check_authentication():
    show_user_info()
else:
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.stop()

st.title("Управление кошельком")
st.markdown("Управление балансом и история финансовых операций")

# Получаем API клиент
api_client = get_api_client()

# Загрузка информации о кошельке
@st.cache_data(ttl=10)  # Кешируем на 10 секунд для актуальности баланса
def load_wallet_info():
    try:
        return api_client.get_wallet_info()
    except Exception as e:
        st.error(f"❌ Ошибка загрузки информации о кошельке: {e}")
        return None

@st.cache_data(ttl=30)  # Кешируем на 30 секунд
def load_transaction_history(limit=50):
    try:
        return api_client.get_transaction_history(limit=limit)
    except Exception as e:
        st.error(f"❌ Ошибка загрузки транзакций: {e}")
        return {"transactions": [], "total_count": 0}

# Управление обновлением
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Обновить", use_container_width=True):
        SessionManager.clear_cache()
        st.rerun()

# Загружаем данные
with st.spinner("💰 Загружаем информацию о кошельке..."):
    wallet_info = load_wallet_info()

if wallet_info:
    # Основная информация о балансе
    st.markdown("### 💰 Текущий баланс")
    
    balance = float(wallet_info.get('balance', 0))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💵 Доступно средств",
            format_currency(balance),
            help="Доступная сумма для проведения анализов"
        )
    
    with col2:
        total_transactions = wallet_info.get('total_transactions', 0)
        st.metric(
            "📊 Всего транзакций",
            total_transactions,
            help="Общее количество операций с кошельком"
        )
    
    with col3:
        avg_cost = wallet_info.get('average_analysis_cost', 0)
        if avg_cost > 0:
            remaining_analyses = int(balance // avg_cost)
            st.metric(
                "🔢 Доступно анализов",
                f"~{remaining_analyses}",
                help="Примерное количество анализов на текущий баланс"
            )
        else:
            st.empty()
    
    with col4:
        st.empty()

# Предупреждения о балансе
if wallet_info:
    balance = float(wallet_info.get('balance', 0))
    if balance < 10:
        st.error("⚠️ Критически низкий баланс! Пополните счет для продолжения работы.")
    elif balance < 50:
        st.warning("⚠️ Низкий баланс! Рекомендуем пополнить счет.")
    elif balance > 1000:
        st.success("💎 Отличный баланс! У вас достаточно средств для множества анализов.")

st.markdown("---")

# Пополнение баланса
st.markdown("### 💵 Пополнение баланса")

with st.form("credit_wallet_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        amount = st.number_input(
            "Сумма пополнения (₽):",
            min_value=1.0,
            max_value=100000.0,
            step=10.0,
            value=100.0,
            help="Введите сумму для пополнения кошелька"
        )
    
    with col2:
        st.empty()
    
    # Прогнозирование
    if wallet_info and amount > 0:
        current_balance = float(wallet_info.get('balance', 0))
        new_balance = current_balance + amount
        avg_cost = wallet_info.get('average_analysis_cost', 1.0)
        
        if avg_cost > 0:
            new_analyses_available = int(new_balance // avg_cost)
            st.info(f"💡 После пополнения у вас будет {format_currency(new_balance)} (примерно {new_analyses_available} анализов)")
    
    submitted = st.form_submit_button("💳 Пополнить баланс", use_container_width=True, type="primary")
    
    if submitted and amount > 0:
        try:
            with st.spinner(f"💳 Обрабатывается пополнение на {format_currency(amount)}..."):
                response = api_client.credit_wallet(amount)
                
            st.success(f"✅ Баланс успешно пополнен на {format_currency(amount)}!")
            
            # Очищаем кеш для обновления данных
            SessionManager.clear_cache()
            
            # Показываем информацию об операции
            if response:
                st.info(f"🧾 ID транзакции: {response.get('transaction_id', 'N/A')}")
            
            st.balloons()  # Анимация успеха
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Ошибка пополнения: {str(e)}")

st.markdown("---")

# История транзакций
st.markdown("### 📊 История транзакций")

transactions_data = load_transaction_history()
transactions = transactions_data.get("transactions", [])

if transactions:
    # Фильтры для транзакций
    with st.expander("🔧 Фильтры транзакций", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tx_type_filter = st.multiselect(
                "💰 Тип операции:",
                ['CREDIT', 'DEBIT'],
                default=[],
                format_func=lambda x: {'CREDIT': '💰 Пополнение', 'DEBIT': '💸 Списание'}[x],
                help="Фильтр по типу финансовых операций"
            )
        
        with col2:
            date_range = st.date_input(
                "📅 Период:",
                value=[],
                help="Выберите диапазон дат для фильтрации"
            )
        
        with col3:
            limit_transactions = st.selectbox(
                "📊 Показать записей:",
                [10, 25, 50, 100],
                index=2,
                help="Количество транзакций для отображения"
            )
    
    # Применяем фильтры
    filtered_transactions = transactions.copy()
    
    if tx_type_filter:
        filtered_transactions = [t for t in filtered_transactions if t['tx_type'] in tx_type_filter]
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_transactions = [
            t for t in filtered_transactions 
            if start_date <= datetime.fromisoformat(t['trans_time'].replace('Z', '+00:00')).date() <= end_date
        ]
    
    # Ограничиваем количество записей
    filtered_transactions = filtered_transactions[:limit_transactions]
    
    if filtered_transactions:
        # Статистика по отфильтрованным транзакциям
        total_credit = sum([float(t['amount']) for t in filtered_transactions if t['tx_type'] == 'CREDIT'])
        total_debit = sum([float(t['amount']) for t in filtered_transactions if t['tx_type'] == 'DEBIT'])
        net_amount = total_credit - total_debit
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💰 Пополнения", format_currency(total_credit))
        with col2:
            st.metric("💸 Списания", format_currency(total_debit))
        with col3:
            st.metric(
                "📊 Баланс операций",
                format_currency(net_amount),
                delta=format_currency(net_amount)
            )
        
        # Таблица транзакций
        st.markdown("#### 📋 Список операций")
        
        # Подготавливаем данные для таблицы
        table_data = []
        for transaction in filtered_transactions:
            table_data.append({
                'ID': transaction.get('id', 'N/A'),
                'Дата и время': format_datetime(transaction.get('trans_time', '')),
                'Тип операции': '💰 Пополнение' if transaction['tx_type'] == 'CREDIT' else '💸 Списание',
                'Сумма': format_currency(float(transaction.get('amount', 0))),
                'Подписанная сумма': f"+{transaction['amount']}" if transaction['tx_type'] == 'CREDIT' else f"-{transaction['amount']}"
            })
        
        df = pd.DataFrame(table_data)
        
        st.dataframe(
            df[['Дата и время', 'Тип операции', 'Сумма']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Тип операции": st.column_config.TextColumn("Тип операции", width="medium"),
                "Сумма": st.column_config.TextColumn("Сумма", width="small"),
            }
        )
        
        
        # Экспорт транзакций
        st.markdown("#### 📊 Экспорт данных")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Экспорт в CSV", use_container_width=True):
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="💾 Скачать CSV",
                    data=csv_data,
                    file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            if st.button("📊 Экспорт отчета", use_container_width=True):
                report_text = f"""
ОТЧЕТ ПО ТРАНЗАКЦИЯМ КОШЕЛЬКА
============================

Период: {date_range[0] if len(date_range) > 0 else 'Не указан'} - {date_range[1] if len(date_range) > 1 else 'Не указан'}
Сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

СВОДКА:
-------
Всего операций: {len(filtered_transactions)}
Пополнений: {format_currency(total_credit)}
Списаний: {format_currency(total_debit)}
Итоговый баланс операций: {format_currency(net_amount)}

ДЕТАЛИЗАЦИЯ:
------------
{chr(10).join([f"{t.get('trans_time', 'N/A')[:19]} | {t['tx_type']} | {t.get('amount', 0)}₽" for t in filtered_transactions])}
"""
                
                st.download_button(
                    label="💾 Скачать отчет",
                    data=report_text,
                    file_name=f"wallet_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
    
    else:
        st.info("📭 Нет транзакций, соответствующих выбранным фильтрам")

else:
    st.info("📭 У вас пока нет финансовых операций")
    st.markdown("💡 Пополните баланс для начала работы с системой!")

# Боковая панель с дополнительной информацией
with st.sidebar:
    if st.button("🏠 Главное меню", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("### 💡 Информация о кошельке")
    
    if wallet_info:
        balance = float(wallet_info.get('balance', 0))
        st.metric("💰 Текущий баланс", format_currency(balance))
        
        # Прогноз расходов
        avg_cost = wallet_info.get('average_analysis_cost', 0)
        if avg_cost > 0:
            remaining_analyses = int(balance // avg_cost)
            st.write(f"**📊 Доступно анализов:** ~{remaining_analyses}")
    
    
    st.markdown("### 🔒 Безопасность")
    st.success("""
    **✅ Ваши средства в безопасности:**
    
    • Все транзакции логируются и отслеживаются
    
    • Автоматический возврат средств при ошибках обработки
    
    • Защищенное SSL соединение
    
    • Мгновенная обработка пополнений
    """)
    
    st.markdown("### ⚙️ Быстрые действия")
    
    if st.button("📝 Анализировать документ", use_container_width=True):
        st.switch_page("pages/New_Analysis.py")
    
    if st.button("📋 История", use_container_width=True):
        st.switch_page("pages/History.py")
    
    if st.button("🏠 Главная страница", use_container_width=True):
        st.switch_page("app.py")
    
    # Техническая информация
    st.markdown("### 🔧 Техническая информация")
    st.text(f"""
Валюта: RUB (₽)
Комиссия: 0%
Минимальная сумма: 1₽
Максимальная сумма: 100,000₽
    """)