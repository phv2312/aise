from sqlalchemy.orm import Session
import models
import schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_name(db:Session, user_name: str):
    return db.query(models.User).filter(models.User.user_name == user_name).first()


def get_all_users(db:Session, limit=1000):
    return db.query(models.User).offset(0).limit(limit).all()


def create_user(db:Session, user: schemas.User):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(user_name=user.user_name, hashed_password=hashed_password, )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


async def authenticate_user(db: Session, user_name: str, password: str):
    existing_user = get_user_by_name(db, user_name)
    if not existing_user:
        return False

    # verify password
    # if not existing_user.hashed_password == pwd_context.hash(password):
    #     return False

    return existing_user

def update_user(db:Session, new_user: schemas.User, user_id: int):
    db.query(models.User).filter(models.User.id == user_id).update({
        models.User.hashed_password: pwd_context.hash(new_user.password)
    }, synchronize_session=False)
    db.commit()


def delete_user(db:Session, user_id: int):
    db.query(models.User).filter(models.User.id == user_id).delete(synchronize_session=False)
    db.commit()

    return


def create_job(db: Session, new_job: schemas.Job):
    db_job = models.Job(own_id=new_job.own_id)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return db_job


def create_image(db: Session, new_image: schemas.Image):
    db_image = models.Image(created_at=new_image.created_at, url=new_image.url, is_reference=new_image.is_reference,
                            job_id=new_image.job_id)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return db_image