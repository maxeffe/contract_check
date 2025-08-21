from fastapi import APIRouter, HTTPException, status, Depends, Query, File, UploadFile, Form
from typing import Dict, Any, List, Optional, Union
from services.crud import document as DocumentService
from services.crud import mljob as MLJobService
from services.crud import model as ModelService
from services.prediction_service import process_prediction_request
from services.document_processor import document_processor
from database.database import get_session
from schemas.prediction import (
    PredictionRequest, 
    PredictionJobResponse, 
    DocumentResponse,
    PredictionHistoryResponse,
    MLJobResponse,
    RiskClauseResponse,
    ModelResponse
)
from auth.jwt_handler import get_current_user
import uuid
from typing import List, Optional
from config.logging_config import prediction_logger

prediction_route = APIRouter(tags=['Predictions'])

@prediction_route.post('/predict')
async def create_prediction(
    data: PredictionRequest,
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> dict:
    """Создать запрос на предсказание/анализ договора"""
    
    prediction_logger.info(f"Запрос на анализ договора от пользователя {current_user['user_id']}, модель: {data.model_name}")
    
    try:
        result = process_prediction_request(
            user_id=current_user["user_id"],
            document_text=data.document_text,
            filename=data.filename,
            language=data.language,
            model_name=data.model_name,
            summary_depth=data.summary_depth,
            session=session
        )
        
        prediction_logger.info(f"Анализ завершен успешно. Job ID: {result['job_id']}, стоимость: {result['cost']}")
        
        return {
            "message": result["message"],
            "job_id": result["job_id"],
            "document_id": result["document_id"],
            "status": result["status"],
            "cost": result["cost"],
            "tokens_processed": result["tokens_processed"]
        }
        
    except ValueError as e:
        if "Insufficient balance" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction processing failed: {str(e)}"
        )

@prediction_route.post('/predict/upload')
async def predict_from_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form("RU"),
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> dict:
    """Загрузить файл и создать запрос на предсказание"""
    

    allowed_types = ['text/plain', 'application/pdf', 'application/msword', 
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: txt, pdf, doc, docx"
        )
    
    try:
        contents = await file.read()
        
        is_valid, validation_message = document_processor.validate_file(contents, file.filename)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_message
            )
        
        text, processed_successfully = document_processor.process_file(contents, file.filename)
        
        if not processed_successfully or not text:
            error_message = "Не удалось обработать файл. "
            if file.content_type == 'application/pdf':
                error_message += "Требуется PyPDF2. Установите: pip install PyPDF2"
            elif file.content_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                error_message += "Требуется python-docx и docx2txt. Установите: pip install python-docx docx2txt"
            else:
                error_message += "Возможно, файл поврежден или пустой."
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_message
            )
        
        result = process_prediction_request(
            user_id=current_user["user_id"],
            document_text=text,
            filename=file.filename,
            language=language,
            model_name="default_model",
            summary_depth="BULLET", 
            session=session
        )
        
        return {
            "message": f"File {file.filename} uploaded and queued for analysis",
            "filename": file.filename,
            "job_id": result["job_id"],
            "document_id": result["document_id"],
            "status": result["status"],
            "cost": result["cost"],
            "tokens_processed": result["tokens_processed"]
        }
        
    except ValueError as e:
        if "Insufficient balance" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File processing failed: {str(e)}"
        )

@prediction_route.get('/documents')
async def get_user_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> dict:
    """Получить список документов пользователя"""
    
    documents = DocumentService.get_user_documents(
        current_user["user_id"], 
        session, 
        skip, 
        limit
    )
    
    total_count = DocumentService.count_user_documents(
        current_user["user_id"], 
        session
    )
    
    document_responses = [
        DocumentResponse(
            id=doc.id,
            user_id=doc.user_id,
            filename=doc.filename,
            pages=doc.pages,
            language=doc.language,
            uploaded_at=doc.uploaded_at
        ) for doc in documents
    ]
    
    return {
        "documents": document_responses,
        "total_count": total_count,
        "skip": skip,
        "limit": limit
    }

@prediction_route.get('/documents/{document_id}')
async def get_document_details(
    document_id: int,
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> DocumentResponse:
    """Получить детали конкретного документа"""
    
    document = DocumentService.get_document_by_id(document_id, session)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )
    
    return DocumentResponse(
        id=document.id,
        user_id=document.user_id,
        filename=document.filename,
        pages=document.pages,
        language=document.language,
        uploaded_at=document.uploaded_at
    )

@prediction_route.get('/history')
async def get_prediction_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> PredictionHistoryResponse:
    """Получить историю ML заданий пользователя"""
    
    jobs = MLJobService.get_user_jobs(
        current_user["user_id"], 
        session, 
        skip, 
        limit
    )
    
    total_count = MLJobService.count_user_jobs(
        current_user["user_id"], 
        session
    )
    
    job_responses = []
    for job in jobs:
        risk_clauses = MLJobService.get_job_risk_clauses(job.id, session)
        risk_clause_responses = [
            RiskClauseResponse(
                id=clause.id,
                clause_text=clause.clause_text,
                risk_level=clause.risk_level,
                explanation=clause.explanation
            ) for clause in risk_clauses
        ]
        
        job_responses.append(MLJobResponse(
            id=job.id,
            document_id=job.document_id,
            model_id=job.model_id,
            status=job.status,
            summary_depth=job.summary_depth,
            used_credits=job.used_credits,
            summary_text=job.summary_text,
            risk_score=job.risk_score,
            started_at=job.started_at,
            finished_at=job.finished_at,
            risk_clauses=risk_clause_responses
        ))
    
    return PredictionHistoryResponse(
        jobs=job_responses,
        total_count=total_count
    )

@prediction_route.get('/models')
async def get_available_models(
    session=Depends(get_session)
) -> List[ModelResponse]:
    """Получить список доступных ML моделей"""
    
    models = ModelService.get_active_models(session)
    
    return [
        ModelResponse(
            id=model.id,
            name=model.name,
            price_per_token=model.price_per_token,
            active=model.active
        ) for model in models
    ]

from pydantic import BaseModel
from fastapi import Request as FastAPIRequest

class EstimateRequest(BaseModel):
    document_text: str

@prediction_route.post('/estimate')  
async def estimate_cost(
    request: FastAPIRequest,
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Предварительная оценка стоимости анализа"""
    
    try:
        text = None
        
        content_type = request.headers.get("content-type", "")
        
        if "multipart/form-data" in content_type:
            form = await request.form()
            if "file" in form:
                file = form["file"]
                contents = await file.read()
                
                is_valid, validation_message = document_processor.validate_file(contents, file.filename)
                if not is_valid:
                    raise HTTPException(status_code=400, detail=validation_message)
                
                text, processed_successfully = document_processor.process_file(contents, file.filename)
                
                if not processed_successfully or not text:
                    raise HTTPException(
                        status_code=422, 
                        detail="Не удалось обработать файл. Возможно, требуются дополнительные библиотеки или файл поврежден."
                    )
        
        elif "application/json" in content_type:
            try:
                body = await request.json()
                if "document_text" in body and body["document_text"]:
                    text = body["document_text"]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text or file provided")
        
        from models.document import Document
        token_count = Document.count_tokens(text)
        
        models = ModelService.get_active_models(session)
        if not models:
            raise HTTPException(status_code=404, detail="No models available")
        
        model = models[0] 
        cost = token_count * model.price_per_token
        
        return {
            "token_count": token_count,
            "estimated_cost": float(cost),
            "model_name": model.name,
            "price_per_token": float(model.price_per_token)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Estimation failed: {str(e)}")

@prediction_route.get('/jobs/{job_id}')
async def get_job_details(
    job_id: int,
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> MLJobResponse:
    """Получить детали конкретного ML задания"""
    
    job = MLJobService.get_job_by_id(job_id, session)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    document = DocumentService.get_document_by_id(job.document_id, session)
    if not document or document.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job"
        )

    risk_clauses = MLJobService.get_job_risk_clauses(job.id, session)
    risk_clause_responses = [
        RiskClauseResponse(
            id=clause.id,
            clause_text=clause.clause_text,
            risk_level=clause.risk_level,
            explanation=clause.explanation
        ) for clause in risk_clauses
    ]
    
    return MLJobResponse(
        id=job.id,
        document_id=job.document_id,
        model_id=job.model_id,
        status=job.status,
        summary_depth=job.summary_depth,
        used_credits=job.used_credits,
        summary_text=job.summary_text,
        risk_score=job.risk_score,
        started_at=job.started_at,
        finished_at=job.finished_at,
        risk_clauses=risk_clause_responses
    )