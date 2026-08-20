from fastapi import APIRouter

router = APIRouter(prefix='/disease', tags=['Disease'])

@router.get('/')
async def list_diseases():
    return {'message': 'List of diseases'}

@router.get('/{disease_id}')
async def get_disease(disease_id: str):
    return {'message': f'Disease {disease_id}'}
