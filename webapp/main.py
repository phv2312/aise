import os
import jwt

from fastapi import FastAPI, Depends, HTTPException, status, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from celery import Celery

from webapp import models
from webapp import schemas
from webapp import crud
from webapp.database import engine, SessionLocal

#
app  = FastAPI()
models.Base.metadata.create_all(engine)
templates = Jinja2Templates(directory="webapp/templates")

#
STORAGE_DIR = os.getenv('STORAGE_DIR')
os.makedirs(STORAGE_DIR, exist_ok=True)

#
JWT_SECRET = 'myjwtsecret'
oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')

#
celery = Celery('simple_worker', broker=os.getenv('BROKER_URL'), backend=os.getenv('BACKEND_URL'))
celery.conf.task_serializer = 'pickle'
celery.conf.result_serializer = 'pickle'
celery.conf.accept_content = ['application/json', 'application/x-python-serialize']


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_existing_user(id: Optional[int] = None, user_name: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Validator, ensure that the user: User has existed, given either id or user_name
    """
    if id is None and user_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Please input the <user_name> or <id>!')
    existing_user = None
    exception_message = ""
    if id is not None:
        existing_user = crud.get_user_by_id(db, user_id=id)
        exception_message = "User id: %d has not existed !!" % id
    elif user_name is not None:
        existing_user = crud.get_user_by_name(db, user_name=user_name)
        exception_message = "User name: %d has not existed !!" % user_name

    if not existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exception_message)

    return existing_user


@app.post('/token', tags=['Authentication'])
async def get_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = await crud.authenticate_user(db=db, user_name=form_data.username, password=form_data.password)
    if not user:
        return {'error': 'invalid credentials'}

    user_obj = schemas.UserOut(id=user.id, user_name=user.user_name, skills=user.skills)

    token = jwt.encode(user_obj.dict(), JWT_SECRET)
    return {'access_token': token, 'token_type' : 'bearer'}


@app.get('/home/', response_class=HTMLResponse, tags=['Authentication'])
async def to_home(request: Request, token: str = Depends(oauth2_schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms =['HS256'])
        print ('token:', token)
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return templates.TemplateResponse('home.html', context={"request": request, "user_id": payload['id']})


@app.post('/create_job/', status_code=status.HTTP_200_OK, tags=['Celery Workers'])
async def create_job(user_id: str = Form(...), reference: UploadFile = File(...), target: UploadFile = File(...)):

    reference_buffer_data = await reference.read()
    target_buffer_data = await target.read()

    # Send to celery ...
    result = celery.send_task('webapp.worker.start_interpolation_job', kwargs={
        'reference_buffer_data': reference_buffer_data,
        'target_buffer_data': target_buffer_data,
        'user_id': user_id,
    }, serializer= 'pickle')

    return {'message': 'request_id: %s is under processing ...' % result.id}


@app.get('/worker_status/{request_id}', tags=['Celery Workers'])
async def get_request_status(request_id: str):
    request_status = celery.AsyncResult(request_id, app=celery)
    return {"request_status": request_status.state}


@app.post('/user/', response_model=schemas.UserOut, description='Create new user', tags=['Users'])
async def create_user(user: schemas.User, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_name(db, user_name=user.user_name)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User name: %s has been existed !!" % user.user_name)
    return crud.create_user(db, user)


@app.get('/user/', response_model=List[schemas.UserOut], description='Get current users', tags=['Users'])
async def get_all(db: Session = Depends(get_db)):
    users = crud.get_all_users(db)
    return users


@app.get('/user/{id}', response_model=schemas.UserOut, description="Get user by ID", tags=['Users'])
async def get_by_id(existing_user: schemas.User = Depends(ensure_existing_user)):
    return existing_user


@app.get('/user/{user_name}', response_model=schemas.UserOut, description="Get user by name", tags=['Users'])
async def get_by_name(existing_user: schemas.User = Depends(ensure_existing_user)):
    return existing_user


@app.put('/user/{id}', status_code=status.HTTP_202_ACCEPTED, description="Update attributes of User by ID", tags=['Users'])
async def update_by_id(*, existing_user: schemas.User = Depends(ensure_existing_user), update_user: schemas.UserUpdate,
                       db: Session = Depends(get_db)):
    return crud.update_user(db, update_user, existing_user.id)


@app.delete('/user/{id}', status_code=status.HTTP_200_OK, description="Delete user by ID", tags=['Users'])
async def delete_by_id(*, existing_user: schemas.User = Depends(ensure_existing_user),
                       db: Session = Depends(get_db)):

    return crud.delete_user(db, user_id=existing_user.id)


