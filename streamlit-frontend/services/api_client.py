import requests
import streamlit as st
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Получить заголовки с токеном авторизации"""
        headers = {}
        if hasattr(st.session_state, 'access_token') and st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Обработка ответа API"""
        if response.status_code == 401:
            # Отладочная информация
            st.error(f"🔒 Ошибка авторизации при запросе: {response.url}")
            st.error(f"Токен в сессии: {'Есть' if hasattr(st.session_state, 'access_token') and st.session_state.access_token else 'Нет'}")
            
            # Очищаем сессию при 401 ошибке
            if hasattr(st.session_state, 'access_token'):
                del st.session_state.access_token
            if hasattr(st.session_state, 'user_info'):
                del st.session_state.user_info
            st.error("🔒 Сессия истекла. Пожалуйста, войдите заново.")
            st.stop()
        
        if not response.ok:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"HTTP {response.status_code} Error")
            except:
                error_detail = f"HTTP {response.status_code} Error"
            raise requests.HTTPError(error_detail)
        
        return response.json()
    
    # === АУТЕНТИФИКАЦИЯ ===
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Авторизация пользователя"""
        data = {
            "email": username,  # API ожидает email, а не username
            "password": password
        }
        response = self.session.post(
            f"{self.base_url}/auth/signin",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        return self._handle_response(response)
    
    def register(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Регистрация нового пользователя"""
        response = self.session.post(
            f"{self.base_url}/auth/signup",
            json=user_data
        )
        return self._handle_response(response)
    
    def get_current_user(self) -> Dict[str, Any]:
        """Получить информацию о текущем пользователе"""
        response = self.session.get(
            f"{self.base_url}/auth/profile",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    # === ПРЕДСКАЗАНИЯ ===
    def create_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новое предсказание"""
        headers = {'Content-Type': 'application/json'}
        headers.update(self._get_auth_headers())
        
        response = self.session.post(
            f"{self.base_url}/predict",
            json=prediction_data,
            headers=headers
        )
        return self._handle_response(response)
    
    def upload_file_prediction(self, file_content: bytes, filename: str, language: str = "UNKNOWN") -> Dict[str, Any]:
        """Загрузить файл для анализа"""
        files = {"file": (filename, file_content)}
        data = {"language": language}
        
        # Для multipart/form-data убираем Content-Type из заголовков
        headers = self._get_auth_headers()
        
        response = self.session.post(
            f"{self.base_url}/predict/upload",
            files=files,
            data=data,
            headers=headers
        )
        return self._handle_response(response)
    
    def get_prediction_history(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Получить историю предсказаний"""
        response = self.session.get(
            f"{self.base_url}/history?skip={skip}&limit={limit}",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    def get_job_details(self, job_id: int) -> Dict[str, Any]:
        """Получить детали задания"""
        response = self.session.get(
            f"{self.base_url}/jobs/{job_id}",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Получить доступные модели"""
        response = self.session.get(
            f"{self.base_url}/models",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    def get_user_documents(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Получить документы пользователя"""
        response = self.session.get(
            f"{self.base_url}/documents?skip={skip}&limit={limit}",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    # === КОШЕЛЕК ===
    def get_wallet_info(self) -> Dict[str, Any]:
        """Получить информацию о кошельке"""
        response = self.session.get(
            f"{self.base_url}/wallet/wallet",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    def get_transaction_history(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Получить историю транзакций"""
        response = self.session.get(
            f"{self.base_url}/wallet/transactions?skip={skip}&limit={limit}",
            headers=self._get_auth_headers()
        )
        return self._handle_response(response)
    
    def credit_wallet(self, amount: float) -> Dict[str, Any]:
        """Пополнить кошелек"""
        headers = {'Content-Type': 'application/json'}
        headers.update(self._get_auth_headers())
        
        response = self.session.post(
            f"{self.base_url}/wallet/topup",
            json={"amount": amount},
            headers=headers
        )
        return self._handle_response(response)

# Глобальный экземпляр клиента
@st.cache_resource
def get_api_client():
    """Получить синглтон API клиента"""
    return APIClient()