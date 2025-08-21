import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import check_authentication, show_user_info, init_session_state
from services.api_client import get_api_client
from utils.helpers import (
    format_datetime, format_currency, SessionManager
)
from components.visualization import display_wallet_chart
from utils.style_loader import load_theme

load_theme()


init_session_state()
if not check_authentication():
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.info("👈 Перейдите на главную страницу для входа в систему")
    st.stop()

st.title("Управление кошельком")
st.markdown("Управление балансом и история финансовых операций")


api_client = get_api_client()

@st.cache_data(ttl=10)  
def load_wallet_info():
    try:
        return api_client.get_wallet_info()
    except Exception as e:
        st.error(f"❌ Ошибка загрузки информации о кошельке: {e}")
        return None

@st.cache_data(ttl=30) 
def load_transaction_history(limit=50):
    try:
        return api_client.get_transaction_history(limit=limit)
    except Exception as e:
        st.error(f"❌ Ошибка загрузки транзакций: {e}")
        return {"transactions": [], "total_count": 0}


col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Обновить", use_container_width=True):
        SessionManager.clear_cache()
        st.rerun()


with st.spinner("💰 Загружаем информацию о кошельке..."):
    wallet_info = load_wallet_info()

if wallet_info:

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

if wallet_info:
    balance = float(wallet_info.get('balance', 0))
    if balance < 10:
        st.error("⚠️ Критически низкий баланс! Пополните счет для продолжения работы.")
    elif balance < 50:
        st.warning("⚠️ Низкий баланс! Рекомендуем пополнить счет.")
    elif balance > 1000:
        st.success("💎 Отличный баланс! У вас достаточно средств для множества анализов.")

st.markdown("---")

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
            
            SessionManager.clear_cache()
            
            if response:
                st.info(f"🧾 ID транзакции: {response.get('transaction_id', 'N/A')}")
            
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Ошибка пополнения: {str(e)}")

st.markdown("---")

st.markdown("### 📊 История транзакций")

transactions_data = load_transaction_history()
transactions = transactions_data.get("transactions", [])

if transactions:
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
    
    filtered_transactions = transactions.copy()
    
    if tx_type_filter:
        filtered_transactions = [t for t in filtered_transactions if t['tx_type'] in tx_type_filter]
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_transactions = [
            t for t in filtered_transactions 
            if start_date <= datetime.fromisoformat(t['trans_time'].replace('Z', '+00:00')).date() <= end_date
        ]

    filtered_transactions = filtered_transactions[:limit_transactions]
    
    if filtered_transactions:
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
        
        st.markdown("#### 📋 Список операций")
        
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
    
    else:
        st.info("📭 Нет транзакций, соответствующих выбранным фильтрам")

else:
    st.info("📭 У вас пока нет финансовых операций")
    st.markdown("💡 Пополните баланс для начала работы с системой!")

with st.sidebar:
    st.markdown('<h1 class="sidebar-main-title">Платформа для анализа договоров</h1>', unsafe_allow_html=True)
    st.markdown("Интеллектуальный анализ юридических документов")
    
    st.markdown("---")
    
    show_user_info()

    if st.button("Анализировать документ", use_container_width=True):
        st.switch_page("pages/New_Analysis.py")
    if st.button("История", use_container_width=True):
        st.switch_page("pages/History.py")
    if st.button("Баланс", use_container_width=True, disabled=True):
        pass