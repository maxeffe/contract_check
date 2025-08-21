import os
import requests
from typing import Dict, Any, Optional, List
from config.logging_config import prediction_logger
import time

class HuggingFaceService:
    """Сервис для работы с Hugging Face API"""
    
    def __init__(self):
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.base_url = "https://api-inference.huggingface.co/models"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}" if self.api_token else None,
            "Content-Type": "application/json"
        }
        
        self.russian_summarization_model = "IlyaGusev/rut5_base_sum_gazeta"
        self.alternative_russian_model = "RussianNLP/FRED-T5-Summarizer"
        
    def _make_request(self, model_name: str, payload: Dict[str, Any], retries: int = 3) -> Optional[Dict[str, Any]]:
        """Выполнить запрос к Hugging Face API с повторными попытками"""
        if not self.api_token:
            prediction_logger.error("HUGGINGFACE_API_TOKEN не установлен")
            return None
            
        url = f"{self.base_url}/{model_name}"
        
        for attempt in range(retries):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                
                if response.status_code == 503:
                    prediction_logger.info(f"Модель {model_name} загружается, ожидание...")
                    time.sleep(10)
                    continue
                    
                if response.status_code == 200:
                    return response.json()
                else:
                    prediction_logger.error(f"Ошибка API HuggingFace: {response.status_code}, {response.text}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                prediction_logger.error(f"Ошибка соединения с HuggingFace API: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None
        
        return None
    
    
    def summarize_russian_text(self, text: str) -> Optional[str]:
        """Создать краткое изложение русского текста"""
        if len(text) > 2000:
            text_to_summarize = text[:1500] + " " + text[-500:]
        else:
            text_to_summarize = text
        
        payload = {
            "inputs": text_to_summarize,
            "parameters": {
                "max_new_tokens": 200,
                "min_new_tokens": 50,
                "do_sample": True,
                "temperature": 0.7,
                "no_repeat_ngram_size": 4
            }
        }
        
        result = self._make_request(self.russian_summarization_model, payload)
        
        if result and isinstance(result, list) and len(result) > 0:
            summary = result[0].get('summary_text')
            if summary and len(summary.strip()) > 10:
                return summary.strip()
        
        prediction_logger.info("Пробуем альтернативную русскую модель FRED-T5")

        fred_input = f"<LM> Сократи текст.\n{text_to_summarize}"
        
        fred_payload = {
            "inputs": fred_input,
            "parameters": {
                "max_new_tokens": 200,
                "min_new_tokens": 17,
                "num_beams": 5,
                "do_sample": True,
                "no_repeat_ngram_size": 4,
                "top_p": 0.9
            }
        }
        
        result = self._make_request(self.alternative_russian_model, fred_payload)
        
        if result and isinstance(result, list) and len(result) > 0:
            summary = result[0].get('generated_text', result[0].get('summary_text', ''))
            if summary and len(summary.strip()) > 10:
                return summary.strip()
            
        return None
    
    def extract_key_terms(self, text: str) -> List[str]:
        """Извлечение ключевых терминов (простая реализация)"""
        import re
        from collections import Counter
        
        words = re.findall(r'\b[а-яё]{4,}\b', text.lower(), re.UNICODE)
        
        stop_words = {
            'который', 'которая', 'которое', 'которые', 'этот', 'этого', 'этой', 
            'этому', 'этом', 'этих', 'также', 'таким', 'образом', 'может', 'быть',
            'должен', 'должна', 'должно', 'должны', 'согласно', 'стороны', 'сторон'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(10)]
    
    def _clean_text_for_analysis(self, text: str) -> str:
        """Дополнительная очистка текста для анализа"""
        import re
        
        cleaned = re.sub(r'Russian words?[:\s]*', ' ', text)
        cleaned = re.sub(r'"[А-Я]{2,5}"[,\s]*', ' ', cleaned)
        cleaned = re.sub(r'[\'\"]{2,}', ' ', cleaned) 
        cleaned = re.sub(r'[-–—]{2,}', ' ', cleaned)
        cleaned = re.sub(r'\s+[а-яё]\s+', ' ', cleaned)
        cleaned = re.sub(r'\d{1,2}\s+г\.\s+\d{1,2}', ' ', cleaned) 
        
        cleaned = re.sub(r'"[^"]*fool[^"]*"', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"'[^']*fool[^']*'", ' ', cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def analyze_contract_risks(self, text: str) -> Dict[str, Any]:
        """Комплексный анализ рисков договора - фокус на саммаризации и рисках"""
        prediction_logger.info("Начинаем анализ договора с помощью HuggingFace API")
        
        clean_text = self._clean_text_for_analysis(text)
        prediction_logger.info(f"Текст очищен: {len(text)} -> {len(clean_text)} символов")
        
        results = {
            "processed_successfully": False,
            "summary": None,
            "key_terms": [],
            "risk_score": 0.0,
            "risk_clauses": [],
            "error_message": None
        }
        
        try:
            summary = self.summarize_russian_text(clean_text)
            if summary:
                results["summary"] = summary
                prediction_logger.info("Краткое изложение создано с помощью русской модели")
            
            key_terms = self.extract_key_terms(clean_text)
            results["key_terms"] = key_terms
            
            risk_keywords = {
                'неустойка': 0.9,
                'штраф': 0.8,
                'пеня': 0.8,
                'ответственность': 0.6,
                'расторжение': 0.9,
                'нарушение': 0.7,
                'просрочка': 0.6,
                'односторонний': 0.9,
                'арбитраж': 0.5,
                'суд': 0.6,
                'возмещение': 0.7,
                'ущерб': 0.8,
                'санкции': 0.8,
                'обязательство': 0.5,
                'гарантия': 0.4,
                'форс-мажор': 0.3 
            }
            
            risk_score = 0.0
            risk_clauses = []
            
            text_lower = clean_text.lower()
            for keyword, weight in risk_keywords.items():
                if keyword in text_lower:
                    risk_score += weight
                    sentences = clean_text.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower() and len(sentence.strip()) > 20:
                            risk_level = "HIGH" if weight > 0.7 else "MEDIUM" if weight > 0.4 else "LOW"
                            risk_clauses.append({
                                "clause_text": sentence.strip()[:200],
                                "risk_level": risk_level,
                                "explanation": f"Обнаружено ключевое слово: '{keyword}' (вес риска: {weight})"
                            })
                            break
            
            results["risk_score"] = min(1.0, risk_score / 6.0) 
            results["risk_clauses"] = risk_clauses[:8]
            
            if summary or key_terms:
                results["processed_successfully"] = True
                prediction_logger.info("Анализ договора успешно завершен")
            else:
                results["error_message"] = "API не смог обработать текст"
                prediction_logger.warning("API не вернул результатов")
                
        except Exception as e:
            results["error_message"] = f"Ошибка при анализе: {str(e)}"
            prediction_logger.error(f"Ошибка при анализе договора: {str(e)}")
        
        return results
    
    def is_api_available(self) -> bool:
        """Проверить доступность API"""
        if not self.api_token:
            return False
            
        test_payload = {"inputs": "Проверка работы API"}
        result = self._make_request(self.russian_summarization_model, test_payload)
        return result is not None

huggingface_service = HuggingFaceService()