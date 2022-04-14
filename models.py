from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True)
    user_name = Column(String, unique=True)
    hashed_password = Column(String)

    jobs = relationship('Job', back_populates='owner')


class Job(Base):
    __tablename__ = 'Job'
    id = Column(Integer, primary_key=True)

    own_id = Column(Integer, ForeignKey("User.id"))
    owner = relationship('User', back_populates='jobs')
    images = relationship('Image', back_populates='job')


class Image(Base):
    __tablename__ = 'Image'
    id = Column(Integer, primary_key=True)
    created_at =  Column(String) # should be =, not :
    url =  Column(String)
    is_reference = Column(Boolean) # reference: True or target: False

    job_id = Column(Integer, ForeignKey("Job.id"))
    job = relationship('Job', back_populates='images')


