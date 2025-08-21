import time
import requests
import json
from typing import Tuple
from config.logging_config import app_logger

class LightweightMLService:
    """Облегченный ML сервис, использует API Hugging Face"""
    
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models"
        
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        hf_token = os.getenv('HF_TOKEN')
        
        if hf_token:
            self.headers = {
                "Authorization": f"Bearer {hf_token}"
            }
            app_logger.info("Используется HF токен для API")
        else:
            self.headers = {}
            app_logger.warning("HF токен не найден, используется публичный API с ограничениями")
        
    def _call_hf_api(self, model_name: str, inputs: str, task: str = "summarization") -> dict:
        """Вызов API Hugging Face"""
        try:
            url = f"{self.api_url}/{model_name}"
            
            payload = {
                "inputs": inputs,
                "parameters": {
                    "max_length": 100,
                    "min_length": 30,
                    "do_sample": False
                } if task == "summarization" else {}
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                app_logger.warning(f"HF API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            app_logger.error(f"Ошибка вызова HF API: {e}")
            return None
    
    def _summarize_text(self, text: str) -> str:
        """Суммаризация через API"""
        if len(text) > 1000:
            text = text[:1000]
        
        models = [
            "facebook/bart-large-cnn",
            "csebuetnlp/mT5_multilingual_XLSum"
        ]
        
        for model in models:
            result = self._call_hf_api(model, text, "summarization")
            if result and isinstance(result, list) and len(result) > 0:
                return result[0].get('summary_text', '')
        
        return ""
    
    def _analyze_sentiment(self, text: str) -> float:
        """Анализ тональности через API"""
        if len(text) > 500:
            text = text[:500]
            
        result = self._call_hf_api("cardiffnlp/twitter-xlm-roberta-base-sentiment", text, "classification")
        
        if result and isinstance(result, list) and len(result) > 0:
            first_result = result[0]
            if isinstance(first_result, list) and len(first_result) > 0:
                first_result = first_result[0]
            
            label = first_result.get('label', 'NEUTRAL').upper()
            score = first_result.get('score', 0.5)
            
            if 'NEGATIVE' in label:
                return min(0.7 + (score * 0.3), 1.0)
            elif 'POSITIVE' in label:
                return max(0.1, 0.4 - (score * 0.3))
            else:
                return 0.5
        
        return self._fallback_risk_analysis(text)
    
    def _fallback_risk_analysis(self, text: str) -> float:
        """Резервный анализ через ключевые слова"""
        risk_keywords = [
            'штраф', 'пеня', 'неустойка', 'ответственность', 
            'обязательство', 'гарантия', 'возмещение', 'ущерб',
            'санкции', 'нарушение', 'просрочка',
            'penalty', 'fine', 'liability', 'damages',
            'breach', 'default', 'forfeit', 'sanction'
        ]
        
        text_lower = text.lower()
        risk_count = sum(1 for keyword in risk_keywords if keyword in text_lower)
        
        base_risk = 0.2
        keyword_risk = min(risk_count * 0.1, 0.6)
        
        return min(base_risk + keyword_risk, 1.0)
    
    def _extract_risk_clauses(self, text: str, risk_score: float) -> list:
        """Извлечение рискованных пунктов из текста"""
        risk_clauses = []
        
        risk_keywords = {
            'штраф': 'HIGH',
            'пеня': 'HIGH', 
            'неустойка': 'HIGH',
            'ответственность': 'MEDIUM',
            'обязательство': 'MEDIUM',
            'гарантия': 'MEDIUM',
            'возмещение': 'HIGH',
            'ущерб': 'HIGH',
            'санкции': 'HIGH',
            'нарушение': 'MEDIUM',
            'просрочка': 'MEDIUM',
            'penalty': 'HIGH',
            'fine': 'HIGH',
            'liability': 'MEDIUM',
            'damages': 'HIGH',
            'breach': 'MEDIUM',
            'default': 'HIGH'
        }
        
        sentences = text.split('.')
        
        for i, sentence in enumerate(sentences[:10]):
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            found_keywords = []
            for keyword, level in risk_keywords.items():
                if keyword.lower() in sentence.lower():
                    found_keywords.append((keyword, level))
            
            if found_keywords:
                max_risk_level = 'LOW'
                for _, level in found_keywords:
                    if level == 'HIGH':
                        max_risk_level = 'HIGH'
                        break
                    elif level == 'MEDIUM' and max_risk_level == 'LOW':
                        max_risk_level = 'MEDIUM'
                
                explanation_map = {
                    'HIGH': 'Выявлены критические условия, требующие особого внимания',
                    'MEDIUM': 'Обнаружены потенциальные риски, рекомендуется проверка',
                    'LOW': 'Стандартные условия с минимальными рисками'
                }
                
                risk_clauses.append({
                    'clause_text': sentence[:200] + ('...' if len(sentence) > 200 else ''),
                    'risk_level': max_risk_level,
                    'explanation': explanation_map[max_risk_level]
                })
        
        if not risk_clauses and risk_score > 0.3:
            if risk_score > 0.7:
                level = 'HIGH'
                explanation = 'Высокий интегральный риск документа'
            elif risk_score > 0.4:
                level = 'MEDIUM'  
                explanation = 'Средний уровень риска в документе'
            else:
                level = 'LOW'
                explanation = 'Обнаружены незначительные риски'
                
            risk_clauses.append({
                'clause_text': text[:200] + ('...' if len(text) > 200 else ''),
                'risk_level': level,
                'explanation': explanation
            })
        
        return risk_clauses
    
    def analyze_contract(self, text: str, depth: str = "BULLET", model_name: str = "api") -> Tuple[str, float, list]:
        """
        Анализ договора через API Hugging Face
        
        Args:
            text: Текст договора
            depth: Глубина анализа
            model_name: Название модели
            
        Returns:
            Tuple[str, float, list]: (суммаризация, риск-скор, риск-клаузы)
        """
        start_time = time.time()
        app_logger.info(f"Начат облегченный анализ договора через API")
        
        api_summary = self._summarize_text(text)
        
        risk_score = self._analyze_sentiment(text)
        
        risk_clauses = self._extract_risk_clauses(text, risk_score)
        
        if api_summary:
            if depth == "BULLET":
                summary = f"""• {api_summary}
• Анализ выполнен через API Hugging Face
• Риск-скор: {risk_score:.2f}
• Поддержка русского и английского языков"""
            else:
                summary = f"""АНАЛИЗ ДОГОВОРА (API режим)

КРАТКОЕ СОДЕРЖАНИЕ:
{api_summary}

ОЦЕНКА РИСКОВ:
Интегральная оценка риска: {risk_score:.2f} из 1.0

ТЕХНИЧЕСКИЕ ДЕТАЛИ:
- Использован API Hugging Face
- Поддержка многоязычного анализа
- Облегченная версия без локальных моделей"""
        else:
            words = len(text.split())
            summary = f"""БАЗОВЫЙ АНАЛИЗ (API недоступен)

СТАТИСТИКА:
- Количество слов: {words}
- Размер текста: {len(text)} символов
- Риск-скор: {risk_score:.2f}

ПРИМЕЧАНИЕ: API Hugging Face временно недоступен. Выполнен базовый анализ."""
        
        processing_time = time.time() - start_time
        app_logger.info(f"Облегченный анализ завершен за {processing_time:.2f}s, найдено {len(risk_clauses)} риск-клауз")
        
        return summary, risk_score, risk_clauses

_lightweight_service = None

def get_lightweight_service() -> LightweightMLService:
    """Возвращает singleton экземпляр облегченного сервиса"""
    global _lightweight_service
    if _lightweight_service is None:
        _lightweight_service = LightweightMLService()
    return _lightweight_service