from fastapi import APIRouter

router = APIRouter(prefix='/mimic', tags=['MIMIC'])

@router.get('/')
async def list_mimic_data():
    return {'message': 'MIMIC data list'}

@router.get('/{patient_id}')
async def get_mimic_patient(patient_id: str):
    return {'message': f'MIMIC patient {patient_id}'}
