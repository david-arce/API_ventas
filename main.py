from datetime import datetime, timedelta
import os
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
from database import Base, engine, SessionLocal
from models import Producto, User, Inventario
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

@app.get("/api/cogancevalle/sendInvoice/{fecha_inicio}/{fecha_fin}")
def get_productos(fecha_inicio:str, fecha_fin:str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Convertir a objetos datetime
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa AAAAMMDD.")
    
    # Validar fecha, solo se permiten consultas desde el 1 de enero del año en curso
    hoy = datetime.now().date()
    fecha_limite = datetime(hoy.year, 1, 1).date()

    if fecha_inicio < fecha_limite or fecha_fin < fecha_limite:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten consultas del año en curso."
        )

    if fecha_inicio > fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio no puede ser posterior a la fecha fin."
        )
    # convertir fechas a strings para la consulta
    fecha_inicio = fecha_inicio.strftime("%Y%m%d")
    fecha_fin = fecha_fin.strftime("%Y%m%d")
    productos = (
    db.query(Producto)
    .filter(
        Producto.fecha.between(fecha_inicio, fecha_fin), 
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
        ven_cob_val = short_hash(p.ven_cob)
        ven_nom_val = "vendedor_" + ven_cob_val
        # 1 natural o 2 juridica
        if p.tpper == 1:
            ccnit_val = short_hash(p.ccnit)
            ccnit_nom_val = "cliente_" + ccnit_val
        else:
            ccnit_val = p.ccnit
            ccnit_nom_val = p.cliente_nom
        # Si el tipo está en la lista, agregamos el campo extra
        dopr_ven = ""
        if p.tipo in ["A4", "B2", "C3", "T1"]:
            dopr_ven = "venta"
        else:
            dopr_ven = "devolución"
        producto_dict = {
            "codi_ven": p.numero,
            "codi_rev": p.zona,
            "nume_ven": p.numero,
            "oper_ven": p.tipo,
            "dopr_ven": dopr_ven,
            "tipo_ven": p.indinv,
            "sfac_ven": ".",
            "codi_pro": p.sku,
            "desc_pro": p.sku_nom,
            "unid_pro": p.umd,
            "lote_pro": None,
            "fech_ven": p.fecha,   # aseguramos formato string
            "cant_ven": p.cantidad,
            "pbru_ven": p.venta,
            "pliq_ven": p.subtotal,
            "chav_ven": p.tipo,
            "codi_ved": ven_cob_val,
            "nome_ved": ven_nom_val,
            "codi_dlr": ccnit_val,
            "nomb_dlr": ccnit_nom_val,
            "nitd_dlr": p.tpper,
            "cciu_dlr": p.ciudad,
            "node_dlr": p.ciudad_nom
        }

        salida.append(producto_dict)
    
    # df = pd.DataFrame(salida)
    # df.to_excel("productos_filtrados.xlsx", index=False)
    # print("Archivo productos_filtrados.xlsx creado.")

    return salida

@app.get("/api/cogancevalle/sendDistributor")
def get_productos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    productos = (
    db.query(Producto)
    .filter(
        Producto.marca.in_(["0020", "0394"])
    ).all())
    # Convertir los objetos SQLAlchemy en diccionarios
    productos_dict = [p.__dict__ for p in productos]

    # Quitar metadata de SQLAlchemy (la clave "_sa_instance_state")
    for p in productos_dict:
        p.pop("_sa_instance_state", None)

    salida = []
    for p in productos:
        producto_dict = {
            "codi_rev": p.bod,
            "cnpj_rev": "800193348",
            "razo_rev": "cooperativa de ganaderos del centro y norte del valle del cauca",
            "fant_rev": "cogancevalle",
            "muni_rev": None,
            "cepc_rev": "763010",
        }
        salida.append(producto_dict)
    
    # df = pd.DataFrame(salida)
    # df.to_excel("productos_filtrados.xlsx", index=False)
    # print("Archivo productos_filtrados.xlsx creado.")

    return salida

@app.get("/api/cogancevalle/sendStock")
def get_productos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    productos = (
    db.query(Inventario)
    .filter(
        Inventario.marca.in_(["0020", "0394"])
    ).all())
    # Convertir los objetos SQLAlchemy en diccionarios
    productos_dict = [p.__dict__ for p in productos]

    # Quitar metadata de SQLAlchemy (la clave "_sa_instance_state")
    for p in productos_dict:
        p.pop("_sa_instance_state", None)

    salida = []
    for p in productos:
        # Buscar en Productos usando AND (sku y sku_nom deben coincidir)
        producto_ref = (
            db.query(Producto)
            .filter(
                Producto.sku == p.sku,
                Producto.sku_nom == p.sku_nom
            )
            .first()
        )
        umd_val = producto_ref.umd if producto_ref else None
        producto_dict = {
            "codi_rev": p.bod,
            "codi_pro": p.sku,
            "desc_pro": p.sku_nom,
            "unid_pro": umd_val,
            "data_pro": p.lpt,
            "qtde_pro": p.inv_saldo,
            "qtdi_pro": p.inv_saldo + p.inv_trsto,
        }
        salida.append(producto_dict)
    
    # df = pd.DataFrame(salida)
    # df.to_excel("productos_filtrados.xlsx", index=False)
    # print("Archivo productos_filtrados.xlsx creado.")

    return salida

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway asigna PORT automáticamente
    uvicorn.run(app, host="0.0.0.0", port=port)