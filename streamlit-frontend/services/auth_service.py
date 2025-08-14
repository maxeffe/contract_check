import streamlit as st
from services.api_client import get_api_client
from typing import Dict, Any

def check_authentication() -> bool:
    """Проверить, авторизован ли пользователь"""
    return hasattr(st.session_state, 'access_token') and st.session_state.access_token is not None

def require_auth():
    """Декоратор/функция для страниц, требующих авторизации"""
    if not check_authentication():
        st.error("🔒 Для доступа к этой странице необходимо войти в систему")
        st.info("👈 Перейдите на главную страницу для входа в систему")
        st.stop()

def init_session_state():
    """Инициализация состояния сессии"""
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None

def login_form():
    """Форма входа в систему"""
    st.header("🔐 Вход в систему")
    
    with st.form("login_form", clear_on_submit=True):
        email = st.text_input("📧 Email", placeholder="Введите email")
        password = st.text_input("🔑 Пароль", type="password", placeholder="Пароль")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submit = st.form_submit_button("🚀 Войти", use_container_width=True)
        
        if submit:
            if email and password:
                try:
                    with st.spinner("🔄 Выполняется вход..."):
                        api_client = get_api_client()
                        response = api_client.login(email, password)
                        
                        # Сохраняем токен в сессии
                        st.session_state.access_token = response["access_token"]
                        st.session_state.user_info = {
                            "username": response.get("user", {}).get("username", email),
                            "email": response.get("user", {}).get("email", email),
                            "user_id": response.get("user", {}).get("id"),
                            "role": response.get("user", {}).get("role", "USER"),
                            "token_type": response.get("token_type", "bearer")
                        }
                        
                        st.success("✅ Успешный вход в систему!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Ошибка входа: {str(e)}")
            else:
                st.error("⚠️ Пожалуйста, заполните все поля")

def register_form():
    """Форма регистрации"""
    st.header("📝 Регистрация нового пользователя")
    
    with st.form("register_form", clear_on_submit=True):
        username = st.text_input("👤 Имя пользователя", placeholder="Имя пользователя")
        email = st.text_input("📧 Email", placeholder="Email")
        password = st.text_input("🔑 Пароль", type="password", placeholder="Пароль")
        password_confirm = st.text_input("🔑 Подтвердите пароль", type="password", placeholder="Повтор пароля")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submit = st.form_submit_button("📝 Зарегистрироваться", use_container_width=True)
        
        if submit:
            if username and email and password and password_confirm:
                if password != password_confirm:
                    st.error("❌ Пароли не совпадают")
                    return
                
                if len(password) < 6:
                    st.error("❌ Пароль должен содержать минимум 6 символов")
                    return
                
                try:
                    with st.spinner("🔄 Создание аккаунта..."):
                        api_client = get_api_client()
                        user_data = {
                            "username": username,
                            "email": email,
                            "password": password
                        }
                        response = api_client.register(user_data)
                        st.success("✅ Регистрация успешна! Теперь можете войти в систему.")
                        
                except Exception as e:
                    st.error(f"❌ Ошибка регистрации: {str(e)}")
            else:
                st.error("⚠️ Пожалуйста, заполните все поля")

def logout():
    """Выход из системы"""
    # Очищаем токен и информацию о пользователе
    if 'access_token' in st.session_state:
        del st.session_state.access_token
    if 'user_info' in st.session_state:
        del st.session_state.user_info
    
    # Очищаем кеш
    st.cache_data.clear()
    
    st.success("✅ Вы успешно вышли из системы")
    st.rerun()

def get_current_user_info() -> Dict[str, Any]:
    """Получить информацию о текущем пользователе"""
    if not check_authentication():
        return {}
    
    try:
        api_client = get_api_client()
        return api_client.get_current_user()
    except Exception:
        # В случае ошибки возвращаем базовую информацию из сессии
        return st.session_state.get('user_info', {})

def show_user_info():
    """Показать информацию о пользователе в сайдбаре"""
    if check_authentication():
        user_info = st.session_state.get('user_info', {})
        username = user_info.get('username', 'Пользователь')
        
        st.sidebar.markdown(f'<div style="color: white; font-size: 16px; font-weight: 500; margin-bottom: 1rem;">👤 {username}</div>', unsafe_allow_html=True)
        
        if st.sidebar.button("🚪 Выйти", use_container_width=True):
            logout()
    else:
        pass  # Убрали сообщение о входе


def protected_page(page_func):
    """Декоратор для защищенных страниц"""
    def wrapper():
        init_session_state()
        require_auth()
        show_user_info()
        return page_func()
    return wrapper