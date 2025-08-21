from models.model import Model
from sqlmodel import Session, select
from typing import List, Optional

def get_all_models(session: Session) -> List[Model]:
    """Получить все модели"""
    statement = select(Model)
    result = session.exec(statement)
    return list(result.all())

def get_active_models(session: Session) -> List[Model]:
    """Получить активные модели"""
    statement = select(Model).where(Model.active == True)
    result = session.exec(statement)
    return list(result.all())

def get_model_by_id(model_id: int, session: Session) -> Optional[Model]:
    """Получить модель по ID"""
    statement = select(Model).where(Model.id == model_id)
    result = session.exec(statement)
    return result.first()

def get_model_by_name(name: str, session: Session) -> Optional[Model]:
    """Получить модель по имени"""
    statement = select(Model).where(Model.name == name)
    result = session.exec(statement)
    return result.first()

def create_model(
    name: str,
    session: Session,
    price_per_token: float = 0.001,
    active: bool = True
) -> Model:
    """Создать новую модель"""
    model = Model(
        name=name,
        price_per_token=price_per_token,
        active=active
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return model

def update_model(
    model_id: int,
    session: Session,
    name: str = None,
    price_per_token: float = None,
    active: bool = None
) -> Optional[Model]:
    """Обновить модель"""
    model = get_model_by_id(model_id, session)
    if not model:
        return None
    
    if name is not None:
        model.name = name
    if price_per_token is not None:
        model.price_per_token = price_per_token
    if active is not None:
        model.active = active
    
    session.add(model)
    session.commit()
    session.refresh(model)
    return model