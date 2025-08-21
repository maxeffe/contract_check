from fastapi import FastAPI
from routes.home import home_route
from routes.user import user_route
from routes.wallet import wallet_route
from routes.prediction import prediction_route
from database.database import init_db
import uvicorn
import os
from config.logging_config import api_logger
from api_analytics.fastapi import Analytics

app = FastAPI(
    title="Contract Analysis API",
    description="REST API для системы анализа договоров с ML предсказаниями"
)

app.include_router(home_route)
app.include_router(user_route, prefix='/auth')
app.include_router(wallet_route, prefix='/wallet')
app.include_router(prediction_route)

app.add_middleware(Analytics, api_key=os.getenv('API_ANALITICS'))


@app.on_event('startup')
def startup():
    api_logger.info("Запуск приложения...")
    init_db()
    api_logger.info("База данных инициализирована..")

if __name__ == '__main__':
    api_logger.info("Запуск uvicorn сервера на порту 8000")
    uvicorn.run('api:app', host='0.0.0.0', port=8000, reload=True)