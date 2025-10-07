from datetime import datetime, timedelta
import os
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
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
def get_productos(filtro: FiltroFecha, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fechaInicio = filtro.fecha_inicio
    fechaFin = filtro.fecha_fin
    
    # Convertir a objetos datetime
    try:
        fecha_inicio = datetime.strptime(filtro.fecha_inicio, "%Y%m%d")
        fecha_fin = datetime.strptime(filtro.fecha_fin, "%Y%m%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa AAAAMMDD.")

    # Validar rango de fechas
    hoy = datetime.now()
    hace_dos_meses = hoy - timedelta(days=60)

    if fecha_inicio < hace_dos_meses or fecha_fin < hace_dos_meses:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten consultas de los últimos 2 meses."
        )

    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio no puede ser posterior a la fecha fin."
        )
        
    productos = (
    db.query(Producto)
    .filter(
        Producto.fecha.between(fechaInicio, fechaFin), 
        Producto.marca.in_(["0020", "0394"])
    ).all())
    # Convertir los objetos SQLAlchemy en diccionarios
    productos_dict = [p.__dict__ for p in productos]

    # Quitar metadata de SQLAlchemy (la clave "_sa_instance_state")
    for p in productos_dict:
        p.pop("_sa_instance_state", None)

    salida = []
    for p in productos:
        # ✅ Solo aplicar hash si p.tpdc == "C"
        # if p.tpdc == "C":
        #     ven_cob_val = short_hash(p.ven_cob)
        #     ccnit_val = short_hash(p.ccnit)
        #     ven_nom_val = "vendedor_" + ven_cob_val
        #     ccnit_nom_val = "cliente_" + ccnit_val
        # else:
        #     ven_cob_val = short_hash(p.ven_cob)
        #     ccnit_val = p.ccnit
        #     ven_nom_val = "vendedor_" + str(ven_cob_val)
        #     ccnit_nom_val = p.cliente_nom
        
        ven_cob_val = short_hash(p.ven_cob)
        ccnit_val = p.ccnit
        ven_nom_val = "vendedor_" + str(ven_cob_val)
        ccnit_nom_val = p.cliente_nom
        producto_dict = {
            "numero": p.numero,
            "zona": p.zona,
            "tipo": p.tipo,
            "indinv": p.indinv,
            "sku": p.sku,
            "sku_nom": p.sku_nom,
            "umd": p.umd,
            "fecha": p.fecha,   # aseguramos formato string
            "cantidad": p.cantidad,
            "venta": p.venta,
            "subtotal": p.subtotal,
            "ven_cob": ven_cob_val,
            "ven_nom": ven_nom_val,
            "ccnit": ccnit_val,
            "cliente_nom": ccnit_nom_val,
            "ciudad": p.ciudad,
            "ciudad_nom": p.ciudad_nom
        }

        # Si el tipo está en la lista, agregamos el campo extra
        if p.tipo in ["A4", "B2", "C3", "T1"]:
            producto_dict["nombre_documento"] = "FACTURA DE VENTA"
        else:
            producto_dict["nombre_documento"] = "DEVOLUCION DE VENTA"

        salida.append(producto_dict)
    
    # df = pd.DataFrame(salida)
    # df.to_excel("productos_filtrados.xlsx", index=False)
    # print("Archivo productos_filtrados.xlsx creado.")

    return sorted(salida, key=lambda x: x["cliente_nom"])

# @app.get("/ventas")
# def get_ventas(db: Session = Depends(get_db)):
#     ventas = db.query(Producto).all()
#     # Convertir los objetos SQLAlchemy en diccionarios
#     productos_dict = [p.__dict__ for p in ventas]

#     # Quitar metadata de SQLAlchemy (la clave "_sa_instance_state")
#     for p in productos_dict:
#         p.pop("_sa_instance_state", None)

#     # Obtener las columnas del modelo Producto
#     columnas = [c.name for c in Producto.__table__.columns]
    
#     # Convertir a DataFrame
#     df = pd.DataFrame(productos_dict)[columnas]
#     df.to_excel("ventas_enero2024-junio2025.xlsx", index=False)
#     print("Archivo productos.xlsx creado.")
#     return ventas


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway asigna PORT automáticamente
    uvicorn.run(app, host="0.0.0.0", port=port)