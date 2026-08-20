from fastapi import APIRouter

router = APIRouter(prefix='/patient', tags=['Patient'])

@router.get('/')
async def list_patients():
    return {'message': 'List of patients'}

@router.get('/{patient_id}')
async def get_patient(patient_id: str):
    return {'message': f'Patient {patient_id}'}

@router.post('/')
async def create_patient():
    return {'message': 'Patient created'}
