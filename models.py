from sqlalchemy import Column, Integer, String
from .database import Base

class UserApi(Base):
    __tablename__ = "userApi"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)