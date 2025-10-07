from pydantic import BaseModel

class FiltroFecha(BaseModel):
    fecha_inicio: str
    fecha_fin: str

