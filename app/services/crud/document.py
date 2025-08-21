from models.document import Document
from sqlmodel import Session, select
from typing import List, Optional

def create_document(
    user_id: int,
    filename: str,
    raw_text: str,
    token_count: int,
    session: Session,
    language: str = "UNKNOWN"
) -> Document:
    """Создать новый документ"""
    document = Document(
        user_id=user_id,
        filename=filename,
        raw_text=raw_text,
        token_count=token_count,
        language=language
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

def get_document_by_id(document_id: int, session: Session) -> Optional[Document]:
    """Получить документ по ID"""
    statement = select(Document).where(Document.id == document_id)
    result = session.exec(statement)
    return result.first()


def count_user_documents(user_id: int, session: Session) -> int:
    """Подсчитать общее количество документов пользователя"""
    statement = select(Document).where(Document.user_id == user_id)
    result = session.exec(statement)
    return len(list(result.all()))

def delete_document(document_id: int, session: Session) -> bool:
    """Удалить документ по ID"""
    document = get_document_by_id(document_id, session)
    if not document:
        return False
    
    session.delete(document)
    session.commit()
    return True