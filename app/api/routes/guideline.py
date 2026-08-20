from fastapi import APIRouter

router = APIRouter(prefix='/guideline', tags=['Guideline'])

@router.get('/')
async def list_guidelines():
    return {'message': 'List of clinical guidelines'}

@router.get('/{guideline_id}')
async def get_guideline(guideline_id: str):
    return {'message': f'Guideline {guideline_id}'}
