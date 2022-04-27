import os
import tempfile
import numpy as np
import cv2
from datetime import datetime
import jwt

from fastapi import FastAPI, Depends, HTTPException, status, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session, mapper
from typing import List, Optional


import models
import schemas
import crud
from database import engine, SessionLocal


app  = FastAPI()
models.Base.metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")


STORAGE_DIR = os.getenv('STORAGE_DIR')
os.makedirs(STORAGE_DIR, exist_ok=True)


JWT_SECRET = 'myjwtsecret'
oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_image_into_numpy_array(data):
    np_image = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame


def get_temp_path(np_image):
    temp_dir = tempfile.mkdtemp(dir=STORAGE_DIR)
    output_path = os.path.join(temp_dir, 'image.png')

    cv2.imwrite(output_path, np_image)

    return output_path


@app.post('/token')
async def get_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = await crud.authenticate_user(db=db, user_name=form_data.username, password=form_data.password)
    if not user:
        return {'error': 'invalid credentials'}

    user_obj = schemas.UserOut(id=user.id, user_name=user.user_name)

    token = jwt.encode(user_obj.dict(), JWT_SECRET)
    return {'access_token': token, 'token_type' : 'bearer'}


@app.get('/home/', response_class=HTMLResponse)
async def to_home(request: Request, token: str ):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms =['HS256'])
        print ('token:', token)
    except:
        raise HTTPException(status_code=status.HTTP_201)

    return templates.TemplateResponse('home.html', context={"request": request, "user_id": payload['id']})


@app.post('/create_job/', status_code=status.HTTP_200_OK)
async def create_job(user_id: str = Form(...), reference: UploadFile = File(...), target: UploadFile = File(...), db: Session = Depends(get_db)):

    reference_np_image = load_image_into_numpy_array(await reference.read())
    target_np_image = load_image_into_numpy_array(await target.read())
    reference_output_path = get_temp_path(reference_np_image)
    target_output_path = get_temp_path(target_np_image)

    # Create the job & images
    job = schemas.Job(own_id=user_id)
    job_db = crud.create_job(db, job)

    reference_image = schemas.Image(created_at=str(datetime.now()), url=reference_output_path, is_reference=True, job_id=job_db.id)
    target_image = schemas.Image(created_at=str(datetime.now()), url=target_output_path, is_reference=False, job_id=job_db.id)
    crud.create_image(db, reference_image)
    crud.create_image(db, target_image)

    return {'message': 'ok'}


@app.post('/user/', response_model=schemas.UserOut, description='Create new user')
async def create_user(user: schemas.User, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_name(db, user_name=user.user_name)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User name: %s has been existed !!" % user.user_name)
    return crud.create_user(db, user)


@app.get('/user/', response_model=List[schemas.UserOut], description='Get current users')
async def get_all(db: Session = Depends(get_db)):
    users = crud.get_all_users(db)
    return users


@app.get('/user/{id}', response_model=schemas.UserOut, description="Get user by ID")
async def get_by_id(id: int, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_id(db, user_id=id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User id: %d has not existed !!" % id)
    return existing_user


@app.get('/user/{user_name}', response_model=schemas.UserOut, description="Get user by name")
async def get_by_name(user_name: str, db:Session = Depends(get_db)):
    existing_user = crud.get_user_by_name(db, user_name=user_name)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User name: %s has not existed !!" % user_name)
    return existing_user


@app.put('/user/{id}', status_code=status.HTTP_202_ACCEPTED, description="Update attributes of User by ID")
async def update_by_id(id: int, new_user: schemas.User, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_id(db, user_id=id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User id: %d has not existed !!" % id)
    return crud.update_user(db, new_user, id)


@app.delete('/user/{id}', status_code=status.HTTP_200_OK, description="Delete user by ID")
async def delete_by_id(id: int, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_id(db, user_id=id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User id: %d has not existed !!" % id)
    return crud.delete_user(db, user_id=id)

