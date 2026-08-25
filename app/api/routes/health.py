from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_db_connection

router = APIRouter(prefix='/health', tags=['Health'])

@router.get('/')
async def health_check():
    database_reachable = check_db_connection()
    return {
        'status': 'healthy',
        'application_running': True,
        'database_reachable': database_reachable,
        'mistral_configured': bool(settings.MISTRAL_API_KEY),
    }


@router.get('')
async def health_check_without_trailing_slash():
    return await health_check()

@router.get('/metrics')
async def get_metrics():
    return {'message': 'Health metrics'}
