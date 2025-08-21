import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any

def create_status_pie_chart(jobs: List[Dict[str, Any]]) -> go.Figure:
    """Создать круговую диаграмму распределения статусов"""
    if not jobs:
        return None
    
    status_counts = {}
    for job in jobs:
        status = job.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    colors = {
        'COMPLETED': '#1a1a1a',
        'ERROR': '#666666',
        'PROCESSING': '#4a4a4a',
        'QUEUED': '#333333'
    }
    
    fig = px.pie(
        values=list(status_counts.values()),
        names=list(status_counts.keys()),
        title="📊 Распределение по статусам",
        color_discrete_map=colors
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=True, height=400)
    
    return fig

def create_risk_histogram(jobs: List[Dict[str, Any]]) -> go.Figure:
    """Создать гистограмму распределения риск-индексов"""
    risk_scores = []
    for job in jobs:
        if job.get('risk_score') is not None:
            risk_scores.append(job['risk_score'] * 100) 
    
    if not risk_scores:
        return None
    
    fig = px.histogram(
        x=risk_scores,
        nbins=10,
        title="📈 Распределение риск-индексов",
        labels={'x': 'Риск-индекс (%)', 'y': 'Количество анализов'},
        color_discrete_sequence=['#1a1a1a']
    )
    
    fig.update_layout(
        xaxis_title="Риск-индекс (%)",
        yaxis_title="Количество",
        showlegend=False,
        height=400
    )
    
    return fig

def create_cost_timeline(jobs: List[Dict[str, Any]]) -> go.Figure:
    """Создать временную линию затрат"""
    if not jobs:
        return None
    
    timeline_data = []
    for job in jobs:
        if job.get('started_at') and job.get('used_credits'):
            timeline_data.append({
                'date': job['started_at'][:10],
                'cost': float(job['used_credits']),
                'status': job.get('status', 'UNKNOWN')
            })
    
    if not timeline_data:
        return None
    
    df = pd.DataFrame(timeline_data)
    df['date'] = pd.to_datetime(df['date'])

    daily_costs = df.groupby('date')['cost'].sum().reset_index()
    
    fig = px.line(
        daily_costs,
        x='date',
        y='cost',
        title="💰 Затраты по дням",
        labels={'date': 'Дата', 'cost': 'Затраты (₽)'},
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Затраты (₽)",
        showlegend=False,
        height=400
    )
    
    return fig

def create_risk_gauge(average_risk: float) -> go.Figure:
    """Создать датчик среднего риска"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = average_risk * 100, 
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "⚠️ Средний риск-индекс (%)"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

def display_job_metrics(jobs: List[Dict[str, Any]]):
    """Отобразить метрики по заданиям"""
    if not jobs:
        st.info("📭 Нет данных для отображения")
        return
    

    total_jobs = len(jobs)
    completed_jobs = len([j for j in jobs if j.get('status') in ['COMPLETED', 'DONE']])
    total_cost = sum([float(j.get('used_credits', 0)) for j in jobs])
    

    risk_scores = [j.get('risk_score') for j in jobs if j.get('risk_score') is not None]
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Всего анализов",
            value=total_jobs
        )
    
    with col2:
        st.metric(
            label="✅ Завершено",
            value=completed_jobs,
            delta=f"{(completed_jobs/total_jobs*100):.1f}%" if total_jobs > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="💰 Потрачено",
            value=f"{total_cost:.2f}₽"
        )
    
    with col4:
        st.metric(
            label="⚠️ Средний риск",
            value=f"{avg_risk*100:.1f}%" if avg_risk > 0 else "N/A",
            delta=f"{'Высокий' if avg_risk > 0.7 else 'Средний' if avg_risk > 0.3 else 'Низкий'}" if avg_risk > 0 else None
        )

def display_wallet_chart(transactions: List[Dict[str, Any]]):
    """Отобразить график транзакций кошелька"""
    if not transactions:
        st.info("📭 Нет транзакций для отображения")
        return
    
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['trans_time']).dt.date
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['amount_signed'] = df.apply(
        lambda row: row['amount'] if row['tx_type'] == 'CREDIT' else -row['amount'], 
        axis=1
    )
    
    daily_transactions = df.groupby(['date', 'tx_type'])['amount'].sum().reset_index()
    
    fig = px.bar(
        daily_transactions,
        x='date',
        y='amount',
        color='tx_type',
        title="💳 История транзакций",
        color_discrete_map={
            'CREDIT': '#1a1a1a',
            'DEBIT': '#666666'
        },
        labels={'amount': 'Сумма (₽)', 'date': 'Дата', 'tx_type': 'Тип'}
    )
    
    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Сумма (₽)",
        legend_title="Тип транзакции",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def format_status_badge(status: str) -> str:
    """Format status with monochrome badge"""
    symbols = {
        'DONE': '●',
        'COMPLETED': '●', 
        'ERROR': '○',
        'PROCESSING': '◐',
        'QUEUED': '◯'
    }
    
    symbol = symbols.get(status, '•')
    return f"{symbol} {status}"

def show_job_summary_card(job: Dict[str, Any]):
    """Показать карточку с сводкой задания"""
    with st.container():
        st.markdown("---")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**📄 Анализ #{job['id']}**")
            st.write(f"Статус: {format_status_badge(job.get('status', 'UNKNOWN'))}")
        
        with col2:
            if job.get('risk_score') is not None:
                risk_percent = job['risk_score'] * 100
                st.metric("⚠️ Риск", f"{risk_percent:.1f}%")
            else:
                st.write("⚠️ Риск: N/A")
        
        with col3:
            cost = job.get('used_credits', 0)
            st.metric("💰 Стоимость", f"{cost}₽")
        
        if job.get('summary_text'):
            with st.expander(f"📋 Результаты анализа #{job['id']}", expanded=False):
                st.text_area(
                    "Сводка:",
                    job['summary_text'],
                    height=150,
                    disabled=True,
                    key=f"summary_{job['id']}"
                )