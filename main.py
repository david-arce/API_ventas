# main.py
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import Producto, User
from auth import get_db, authenticate_user, create_access_token, get_current_user
from datetime import timedelta
from hash import short_hash

from schema import FiltroFecha

app = FastAPI(title="API Productos")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=60))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/productos")
def get_productos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    productos = (
    db.query(Producto)
    .filter(Producto.fecha.between("2025-01-01", "2025-01-03")
    ).all())
    
    # Convertir los objetos SQLAlchemy en diccionarios
    productos_dict = [p.__dict__ for p in productos]

    # Quitar metadata de SQLAlchemy (la clave "_sa_instance_state")
    for p in productos_dict:
        p.pop("_sa_instance_state", None)

    # Obtener las columnas del modelo Producto
    columnas = [c.name for c in Producto.__table__.columns]
    
    # Convertir a DataFrame
    # df = pd.DataFrame(productos_dict)[columnas]
    # df.to_excel("productos.xlsx", index=False)
    # print("Archivo productos.xlsx creado.")
    salida = []
    for p in productos:
        # Convertimos el objeto SQLAlchemy en dict
        ven_cob_hash = short_hash(p.ven_cob)
        # combinar 'vendedorcob' con su hash
        ven_nom_hash = "vendedor_" + ven_cob_hash
        producto_dict = {
            "numero": p.numero,
            "zona": p.zona,
            "numero": p.numero,
            "tipo": p.tipo,
            "indinv": p.indinv,
            "sku": p.sku,
            "sku_nom": p.sku_nom,
            "umd": p.umd,
            "fecha": p.fecha,   # aseguramos formato string
            "cantidad": p.cantidad,
            "venta": p.venta,
            "subtotal": p.subtotal,
            "ven_cob": ven_cob_hash,
            "ven_nom": ven_nom_hash,
            "ccnit": p.ccnit,
            "cliente_nom": p.cliente_nom,
            "ciudad": p.ciudad,
            "ciudad_nom": p.ciudad_nom
        }

        # Si el tipo está en la lista, agregamos el campo extra
        if p.tipo in ["A4", "B2", "C3", "T1"]:
            producto_dict["nombre_documento"] = "FACTURA DE VENTA"
        else:
            producto_dict["nombre_documento"] = "DEVOLUCION DE VENTA"

        salida.append(producto_dict)

    return sorted(salida, key=lambda x: x["cliente_nom"])
