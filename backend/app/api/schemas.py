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
    usuario: str
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
    orden_prioridad: int
    fecha_entrega: date | None
    responsable_atencion: str | None
    responsable_atencion_area: str
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
    solicitante_id: int | None
    orden_prioridad: int
    canal: str | None
    canal_id: int | None
    fecha_completado: date | None
    fecha_entrega: date | None
    responsable_atencion_id: int | None
    responsable_atencion: str | None
    responsable_atencion_area: str
    sr_ebs: str | None
    creado_en: datetime
    actualizado_en: datetime
    actualizado_por: str


# Estatus a partir de los cuales una solicitud ya fue planeada (orden_visualizacion >= el de
# PLANEADO): desde aquí, fecha_entrega y responsable_atencion_id son obligatorios.
ESTATUS_REQUIERE_FECHA_ENTREGA = {"PLANEADO", "EN PROGRESO", "COMPLETADO"}


class SolicitudUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=500)
    descripcion: str = Field(min_length=1)
    cliente: str | None = Field(default=None, max_length=100)
    tipo: str = Field(min_length=1, max_length=100)
    canal: str = Field(min_length=1, max_length=100)
    codigo_estatus: str = Field(min_length=1, max_length=15)
    orden_prioridad: int = Field(default=3, ge=1, le=5)
    fecha_completado: date | None = None
    fecha_entrega: date | None = None
    responsable_atencion_id: int | None = None
    sr_ebs: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _fecha_completado_obligatoria_si_completado(self) -> "SolicitudUpdate":
        if self.codigo_estatus == "COMPLETADO" and self.fecha_completado is None:
            raise ValueError(
                "fecha_completado es obligatoria cuando el estatus es Completado"
            )
        return self

    @model_validator(mode="after")
    def _fecha_entrega_y_responsable_obligatorios_si_planeada(self) -> "SolicitudUpdate":
        if self.codigo_estatus in ESTATUS_REQUIERE_FECHA_ENTREGA:
            if self.fecha_entrega is None or self.responsable_atencion_id is None:
                raise ValueError(
                    "fecha_entrega y responsable_atencion_id son obligatorios a partir del "
                    "estatus Planeado"
                )
        return self


class SolicitudUpdateExterno(BaseModel):
    """Edición restringida para el rol EXTERNO: los mismos 4 campos que ya puede llenar al
    crear la solicitud, nada de estatus/prioridad/fechas/responsable de atención."""

    nombre: str = Field(min_length=1, max_length=500)
    descripcion: str = Field(min_length=1)
    cliente: str | None = Field(default=None, max_length=100)
    tipo: str = Field(min_length=1, max_length=100)


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
    solicitud_prioridad: int
    solicitud_fecha_entrega: date | None
    solicitud_codigo_estatus: str
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


class TareaResumenMonitorOut(BaseModel):
    id: int
    solicitud_id: int
    solicitud_nombre: str
    cliente: str | None
    nombre: str
    responsable_id: int | None
    responsable: str | None
    codigo_estatus_tarea: str
    estatus_tarea_descripcion: str | None
    fecha_fin: date
    dias: int


class CargaResponsableOut(BaseModel):
    responsable_id: int | None
    responsable: str | None
    tareas_abiertas: int


class DistribucionEstatusOut(BaseModel):
    codigo_estatus_tarea: str
    descripcion: str
    total: int


class CumplimientoOut(BaseModel):
    total_con_fecha_real: int
    cumplidas: int
    atrasadas: int
    porcentaje_cumplimiento: float | None
    promedio_dias_atraso: float | None


class MonitorKpisOut(BaseModel):
    vencidas: list[TareaResumenMonitorOut]
    por_vencer: list[TareaResumenMonitorOut]
    carga_por_responsable: list[CargaResponsableOut]
    distribucion_estatus: list[DistribucionEstatusOut]
    cumplimiento: CumplimientoOut


class ResumenPorValor(BaseModel):
    valor: str
    descripcion: str
    total: int


class ResumenBloque(BaseModel):
    total: int
    por_estatus: list[ResumenPorValor]
    por_prioridad: list[ResumenPorValor]


class InicioResumenOut(BaseModel):
    mis_solicitudes: ResumenBloque | None = None
    solicitudes_responsable: ResumenBloque | None = None
    mis_tareas: ResumenBloque | None = None
    solicitudes_totales: ResumenBloque | None = None
    tareas_totales: ResumenBloque | None = None
    solicitudes_por_area: list[ResumenPorValor] | None = None


class DireccionGeneralTotalesOut(BaseModel):
    solicitudes_en_proceso: int
    tareas_en_proceso: int
    solicitudes_concluidas_periodo: int
    tareas_concluidas_periodo: int
    solicitudes_nuevas_periodo: int
    tareas_nuevas_periodo: int
    horas_estimadas_periodo: int


class DireccionGeneralGrupoOut(BaseModel):
    grupo_id: int | str | None
    grupo: str
    solicitudes_en_proceso: int
    solicitudes_concluidas_periodo: int
    solicitudes_nuevas_periodo: int
    tareas_en_proceso: int
    tareas_concluidas_periodo: int
    tareas_nuevas_periodo: int
    horas_estimadas_periodo: int


class DistribucionEstatusSolicitudOut(BaseModel):
    codigo_estatus: str
    descripcion: str
    total: int


class DireccionGeneralKpisOut(BaseModel):
    totales: DireccionGeneralTotalesOut
    por_cliente: list[DireccionGeneralGrupoOut]
    por_tipo: list[DireccionGeneralGrupoOut]
    por_area: list[DireccionGeneralGrupoOut]
    solicitudes_por_estatus: list[DistribucionEstatusSolicitudOut]
    tareas_por_estatus: list[DistribucionEstatusOut]


class SolicitudDireccionGeneralOut(BaseModel):
    id: int
    nombre: str
    cliente: str | None
    area: str
    solicitante: str | None
    creado_en: datetime


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


class PorHacerOut(BaseModel):
    id: int
    solicitud_id: int
    tarea_id: int
    tarea_nombre: str | None
    responsable_id: int | None
    responsable: str | None
    nombre: str
    descripcion: str | None
    esta_completa: bool
    creado_en: datetime
    creado_por: str
    creado_por_nombre: str
    actualizado_en: datetime
    actualizado_por: str


class PorHacerCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=4000)
    responsable_id: int | None = None


class PorHacerUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=4000)
    responsable_id: int | None = None
    esta_completa: bool = False


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


class NotificacionOut(BaseModel):
    id: int
    tipo: str
    mensaje: str
    entidad_tipo: str | None
    entidad_id: int | None
    leido_en: datetime | None
    creado_en: datetime


class NotificacionesNoLeidasCountOut(BaseModel):
    no_leidas: int


class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(min_length=1, max_length=255)
    password_nueva: str = Field(min_length=8, max_length=255)
