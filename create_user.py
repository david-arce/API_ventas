# create_user.py
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import User
from auth import get_password_hash

def create_user(username: str, password: str, is_active: bool = True):
    db = SessionLocal()
    try:
        user = User(
            username=username,
            hashed_password=get_password_hash(password),
            is_active=is_active
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ Usuario creado: id={user.id}, username={user.username}")
    except IntegrityError:
        db.rollback()
        print("⚠️ El username ya existe. Elige otro.")
    finally:
        db.close()

if __name__ == "__main__":
    # Cambia estas credenciales por las que quieras
    create_user("david", "david21")
