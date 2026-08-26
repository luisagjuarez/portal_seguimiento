from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


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


class AdjuntoOut(BaseModel):
    id: int
    nombre_archivo: str
    tipo_mime: str | None
    tamano_bytes: int | None
    fecha_carga: datetime


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


class CanalSolicitudOut(BaseModel):
    id: int
    canal: str


class SolicitudResumen(BaseModel):
    id: int
    nombre: str
    cliente: str | None
    tipo: str | None
    codigo_estatus: str
    estatus_descripcion: str | None
    solicitante: str | None
    orden_prioridad: str | None
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
    canal: str | None
    canal_id: int | None
    fecha_completado: date | None
    creado_en: datetime
    actualizado_en: datetime
    actualizado_por: str


class SolicitudUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=500)
    descripcion: str = Field(min_length=1)
    cliente: str | None = Field(default=None, max_length=100)
    tipo: str = Field(min_length=1, max_length=100)
    canal: str = Field(min_length=1, max_length=100)
    codigo_estatus: str = Field(min_length=1, max_length=15)
    orden_prioridad: str | None = Field(default=None, max_length=20)
    fecha_completado: date | None = None

    @model_validator(mode="after")
    def _fecha_completado_obligatoria_si_completado(self) -> "SolicitudUpdate":
        if self.codigo_estatus == "COMPLETADO" and self.fecha_completado is None:
            raise ValueError(
                "fecha_completado es obligatoria cuando el estatus es Completado"
            )
        return self


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
    fecha_inicio_real: date | None
    fecha_fin_real: date | None
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
    fecha_inicio_real: date | None = None
    fecha_fin_real: date | None = None
    horas_estimadas: int | None = None
    horas_reales: int | None = None


class HitoOut(BaseModel):
    id: int
    solicitud_id: int
    tarea_id: int | None
    tarea_nombre: str | None
    nombre: str
    descripcion: str | None
    fecha_vencimiento: date
    creado_en: datetime
    creado_por: str
    creado_por_nombre: str
    actualizado_en: datetime


class HitoCreateUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=4000)
    fecha_vencimiento: date


class EnlaceTareaOut(BaseModel):
    id: int
    solicitud_id: int
    tarea_id: int
    tarea_nombre: str | None
    tipo_enlace: str
    url: str | None
    aplicacion_id: int | None
    pagina_aplicacion: int | None
    descripcion: str | None
    creado_en: datetime
    creado_por: str
    creado_por_nombre: str
    actualizado_en: datetime
    actualizado_por: str


class EnlaceTareaCreate(BaseModel):
    tipo_enlace: str = Field(min_length=1, max_length=20)
    url: str | None = Field(default=None, max_length=255)
    aplicacion_id: int | None = None
    pagina_aplicacion: int | None = None
    descripcion: str | None = Field(default=None, max_length=4000)


class ComentarioOut(BaseModel):
    id: int
    solicitud_id: int
    tarea_id: int | None
    tarea_nombre: str | None
    texto_comentario: str
    creado_en: datetime
    creado_por: str
    creado_por_nombre: str
    actualizado_en: datetime
    actualizado_por: str


class ComentarioCreateUpdate(BaseModel):
    texto_comentario: str = Field(min_length=1, max_length=4000)


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class UsuarioActualOut(BaseModel):
    id: int
    usuario: str
    nombre_completo: str
    codigo_rol_scrum: str | None
    correo_electronico: str | None
    debe_cambiar_password: bool


class LoginResponse(BaseModel):
    access_token: str
    usuario_actual: UsuarioActualOut


class RolScrumOut(BaseModel):
    codigo: str
    descripcion: str


class MiembroAccesoOut(BaseModel):
    id: int
    usuario: str
    nombre_completo: str
    correo_electronico: str | None
    codigo_rol_scrum: str | None
    rol_scrum_descripcion: str | None
    acceso_activo: bool


class OtorgarAccesoRequest(BaseModel):
    password: str = Field(min_length=8, max_length=255)
    codigo_rol_scrum: str = Field(min_length=1, max_length=20)


class CrearMiembroRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=255)
    nombre_completo: str = Field(min_length=1, max_length=255)
    correo_electronico: EmailStr | None = None


class ActualizarMiembroRequest(BaseModel):
    usuario: str | None = Field(default=None, min_length=1, max_length=255)
    nombre_completo: str | None = Field(default=None, min_length=1, max_length=255)
    correo_electronico: EmailStr | None = None
    codigo_rol_scrum: str | None = Field(default=None, min_length=1, max_length=20)
    acceso_activo: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)


class ForgotPasswordRequest(BaseModel):
    correo_electronico: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password_nueva: str = Field(min_length=8, max_length=255)


class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(min_length=1, max_length=255)
    password_nueva: str = Field(min_length=8, max_length=255)
