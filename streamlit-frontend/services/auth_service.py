import streamlit as st
from services.api_client import get_api_client
from typing import Dict, Any
import json
import re

def parse_validation_error(error_str: str) -> str:
    """Парсит ошибки валидации Pydantic и возвращает понятное сообщение"""
    try:
        if '[{' in error_str and '}]' in error_str:
            json_match = re.search(r'\[\{.*\}\]', error_str)
            if json_match:
                error_data = json.loads(json_match.group())
                if error_data and isinstance(error_data, list) and len(error_data) > 0:
                    first_error = error_data[0]
                    field = first_error.get('loc', [''])[-1] if first_error.get('loc') else ''
                    msg = first_error.get('msg', '')
                    
                    if 'email' in field:
                        if 'not a valid email' in msg:
                            return 'Некорректный формат email адреса'
                    elif 'username' in field:
                        if 'too short' in msg or 'at least' in msg:
                            return 'Имя пользователя слишком короткое'
                    elif 'password' in field:
                        if 'too short' in msg or 'at least' in msg:
                            return 'Пароль слишком короткий (минимум 6 символов)'
                    
                    if 'required' in msg:
                        field_names = {'email': 'Поле Email', 'username': 'Поле Имя', 'password': 'Поле Пароль'}
                        return f'{field_names.get(field, "Поле")} обязательно для заполнения'
        
        if 'already registered' in error_str or 'already exists' in error_str:
            return 'Пользователь с таким email уже существует'
        
        return 'Ошибка регистрации. Проверьте введенные данные'
        
    except Exception:
        return 'Ошибка регистрации. Попробуйте позже'

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
    
    query_params = st.query_params
    if 'token' in query_params and not st.session_state.access_token:
        token = query_params['token']
        if token:
            try:
                st.session_state.access_token = token
                api_client = get_api_client()
                user_info = api_client.get_current_user()
                st.session_state.user_info = user_info
                st.query_params.clear()
                st.rerun()
            except Exception:
                st.session_state.access_token = None
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
                        
                        st.session_state.access_token = response["access_token"]
                        st.session_state.user_info = {
                            "username": response.get("user", {}).get("username", email),
                            "email": response.get("user", {}).get("email", email),
                            "user_id": response.get("user", {}).get("id"),
                            "role": response.get("user", {}).get("role", "USER"),
                            "token_type": response.get("token_type", "bearer")
                        }
                        
                        st.query_params["token"] = response["access_token"]
                        
                        st.success("✅ Успешный вход в систему!")
                        st.rerun()
                        
                except Exception as e:
                    error_message = parse_validation_error(str(e))
                    if 'not a valid email' in str(e) or '401' in str(e) or 'Unauthorized' in str(e):
                        st.error("❌ Неверные данные для входа")
                    else:
                        st.error(f"❌ {error_message}")
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
                    error_message = parse_validation_error(str(e))
                    st.error(f"❌ {error_message}")
            else:
                st.error("⚠️ Пожалуйста, заполните все поля")

def logout():
    """Выход из системы"""
    if 'access_token' in st.session_state:
        del st.session_state.access_token
    if 'user_info' in st.session_state:
        del st.session_state.user_info
    
    st.query_params.clear()
    
    st.cache_data.clear()
    

    st.switch_page("app.py")

def get_current_user_info() -> Dict[str, Any]:
    """Получить информацию о текущем пользователе"""
    if not check_authentication():
        return {}
    
    try:
        api_client = get_api_client()
        return api_client.get_current_user()
    except Exception:
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
        pass 

def protected_page(page_func):
    """Декоратор для защищенных страниц"""
    def wrapper():
        init_session_state()
        require_auth()
        show_user_info()
        return page_func()
    return wrapper