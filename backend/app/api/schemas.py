from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class ChatSolicitudRequest(BaseModel):
    solicitante_email: EmailStr
    titulo: str = Field(min_length=1, max_length=500)
    descripcion: str = Field(min_length=1)
    cliente: str | None = Field(default=None, max_length=100)


class ChatSolicitudResponse(BaseModel):
    id_solicitud: int
    titulo: str
    cliente: str | None
    status_cd: str


class ClienteSugerido(BaseModel):
    nombre: str


class HealthResponse(BaseModel):
    status: str = "ok"


class MiembroEquipoOut(BaseModel):
    id: int
    nombre_completo: str
    correo_electronico: str | None


class TipoSolicitudOut(BaseModel):
    id: int
    tipo: str


class EstatusOut(BaseModel):
    codigo: str
    descripcion: str


class SolicitudResumen(BaseModel):
    id: int
    nombre: str
    cliente: str | None
    tipo: str | None
    codigo_estatus: str
    estatus_descripcion: str | None
    solicitante: str | None
    creado_en: datetime


class SolicitudDetalle(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    cliente: str | None
    cliente_id: int | None
    tipo: str | None
    tipo_id: int | None
    codigo_estatus: str
    estatus_descripcion: str | None
    solicitante: str | None
    orden_prioridad: str | None
    creado_en: datetime
    actualizado_en: datetime
    actualizado_por: str


class SolicitudUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=500)
    descripcion: str = Field(min_length=1)
    cliente: str | None = Field(default=None, max_length=100)
    tipo: str = Field(min_length=1, max_length=100)
    codigo_estatus: str = Field(min_length=1, max_length=15)


class EstatusTareaOut(BaseModel):
    codigo: str
    descripcion: str


class TareaOut(BaseModel):
    id: int
    solicitud_id: int
    nombre: str
    descripcion: str | None
    responsable_id: int | None
    responsable: str | None
    codigo_estatus_tarea: str
    estatus_tarea_descripcion: str | None
    fecha_inicio: date
    fecha_fin: date
    horas_estimadas: int | None
    horas_reales: int | None
    creado_en: datetime
    actualizado_en: datetime


class TareaTableroOut(TareaOut):
    solicitud_nombre: str
    cliente: str | None


class TareaCreateUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=4000)
    responsable_id: int | None = None
    codigo_estatus_tarea: str = Field(default="POR HACER", min_length=1, max_length=20)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    horas_estimadas: int | None = None
    horas_reales: int | None = None


class HitoOut(BaseModel):
    id: int
    solicitud_id: int
    nombre: str
    descripcion: str | None
    fecha_vencimiento: date
    creado_en: datetime
    actualizado_en: datetime


class HitoCreateUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=4000)
    fecha_vencimiento: date


class ComentarioOut(BaseModel):
    id: int
    solicitud_id: int
    tarea_id: int | None
    texto_comentario: str
    creado_en: datetime
    creado_por: str
    actualizado_en: datetime
    actualizado_por: str


class ComentarioCreateUpdate(BaseModel):
    texto_comentario: str = Field(min_length=1, max_length=4000)
