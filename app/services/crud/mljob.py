from models.mljob import MLJob
from models.riskclause import RiskClause
from sqlmodel import Session, select
from typing import List, Optional
from models.other import JobStatus

def create_mljob(
    document_id: int,
    model_id: int,
    session: Session,
    summary_depth: str = "BULLET"
) -> MLJob:
    """Создать новое ML задание"""
    job = MLJob(
        document_id=document_id,
        model_id=model_id,
        status=JobStatus.QUEUED,
        summary_depth=summary_depth
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def get_job_by_id(job_id: int, session: Session) -> Optional[MLJob]:
    """Получить задание по ID"""
    statement = select(MLJob).where(MLJob.id == job_id)
    result = session.exec(statement)
    return result.first()


def count_user_jobs(user_id: int, session: Session) -> int:
    """Подсчитать общее количество заданий пользователя"""
    from models.document import Document
    
    statement = (
        select(MLJob)
        .join(Document)
        .where(Document.user_id == user_id)
    )
    result = session.exec(statement)
    return len(list(result.all()))

def update_job_status(
    job_id: int, 
    status: JobStatus, 
    session: Session
) -> Optional[MLJob]:
    """Обновить статус задания"""
    job = get_job_by_id(job_id, session)
    if not job:
        return None
    
    job.status = status
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def complete_job(
    job_id: int,
    summary_text: str,
    risk_score: float,
    risk_clauses: List[dict],
    session: Session
) -> Optional[MLJob]:
    """Завершить задание с результатами"""
    job = get_job_by_id(job_id, session)
    if not job:
        return None
    
    # Обновляем задание
    job.status = JobStatus.DONE
    job.summary_text = summary_text
    job.risk_score = risk_score
    
    # Создаем рискованные пункты
    for clause_data in risk_clauses:
        risk_clause = RiskClause(
            job_id=job.id,
            clause_text=clause_data.get("text", ""),
            risk_level=clause_data.get("risk_level", "LOW"),
            explanation=clause_data.get("explanation", "")
        )
        session.add(risk_clause)
    
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def get_job_risk_clauses(job_id: int, session: Session) -> List[RiskClause]:
    """Получить рискованные пункты для задания"""
    statement = select(RiskClause).where(RiskClause.job_id == job_id)
    result = session.exec(statement)
    return list(result.all())