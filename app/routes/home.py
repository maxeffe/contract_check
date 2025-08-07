from fastapi import APIRouter

home_route = APIRouter(tags=['Home'])



@home_route.get('/')
async def index():
    return "Hellow world"