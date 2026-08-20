from fastapi import APIRouter

router = APIRouter(prefix='/health', tags=['Health'])

@router.get('/')
async def health_check():
    return {'status': 'healthy'}

@router.get('/metrics')
async def get_metrics():
    return {'message': 'Health metrics'}
