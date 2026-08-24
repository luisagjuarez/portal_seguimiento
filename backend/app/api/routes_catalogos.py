from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import EstatusOut, EstatusTareaOut, MiembroEquipoOut, TipoSolicitudOut
from app.db import repository
from app.db.connection import get_connection, release_connection

router = APIRouter(prefix="/api")


@router.get("/miembros-equipo", response_model=list[MiembroEquipoOut])
def listar_miembros_equipo() -> list[MiembroEquipoOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        miembros = repository.list_miembros(cursor)
    finally:
        release_connection(db_conn)
    return [MiembroEquipoOut(**m) for m in miembros]


@router.get("/tipos-solicitud", response_model=list[TipoSolicitudOut])
def listar_tipos_solicitud() -> list[TipoSolicitudOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        tipos = repository.list_tipos_solicitud(cursor)
    finally:
        release_connection(db_conn)
    return [TipoSolicitudOut(**t) for t in tipos]


@router.get("/estatus", response_model=list[EstatusOut])
def listar_estatus() -> list[EstatusOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        estatus = repository.list_estatus(cursor)
    finally:
        release_connection(db_conn)
    return [EstatusOut(**e) for e in estatus]


@router.get("/estatus-tarea", response_model=list[EstatusTareaOut])
def listar_estatus_tarea() -> list[EstatusTareaOut]:
    db_conn = get_connection()
    try:
        cursor = db_conn.cursor()
        estatus = repository.list_estatus_tarea(cursor)
    finally:
        release_connection(db_conn)
    return [EstatusTareaOut(**e) for e in estatus]
