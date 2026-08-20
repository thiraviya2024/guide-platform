from fastapi import APIRouter

router = APIRouter(prefix='/analytics', tags=['Analytics'])

@router.get('/')
async def get_analytics():
    return {'message': 'Analytics endpoint'}

@router.get('/summary')
async def get_summary():
    return {'message': 'Analytics summary'}
