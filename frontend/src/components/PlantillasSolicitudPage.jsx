import { useEffect, useState } from "react";
import CrearPlantillaSolicitudFormulario from "./CrearPlantillaSolicitudFormulario.jsx";
import EditarPlantillaSolicitudFormulario from "./EditarPlantillaSolicitudFormulario.jsx";
import ConfirmModal from "./ConfirmModal.jsx";
import {
  darDeBajaPlantillaSolicitud,
  fetchPlantillaSolicitudDetalle,
  fetchPlantillasSolicitud,
} from "../api.js";

export default function PlantillasSolicitudPage() {
  const [plantillas, setPlantillas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [mostrarCrear, setMostrarCrear] = useState(false);
  const [plantillaEnEdicion, setPlantillaEnEdicion] = useState(null);
  const [plantillaABajar, setPlantillaABajar] = useState(null);
  const [bajando, setBajando] = useState(false);

  const cargar = () => {
    setCargando(true);
    setError(null);
    fetchPlantillasSolicitud(true)
      .then(setPlantillas)
      .catch((err) => setError(err.message || "No se pudo cargar la lista de plantillas."))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar();
  }, []);

  const alCrear = () => {
    setMostrarCrear(false);
    cargar();
  };

  const alGuardarEdicion = () => {
    setPlantillaEnEdicion(null);
    cargar();
  };

  const abrirEdicion = async (plantillaResumen) => {
    setError(null);
    try {
      const detalle = await fetchPlantillaSolicitudDetalle(plantillaResumen.id);
      setPlantillaEnEdicion(detalle);
    } catch (err) {
      setError(err.message || "No se pudo cargar la plantilla.");
    }
  };

  const confirmarBaja = async () => {
    setBajando(true);
    try {
      await darDeBajaPlantillaSolicitud(plantillaABajar.id);
      setPlantillaABajar(null);
      cargar();
    } catch (err) {
      setError(err.message || "No se pudo dar de baja la plantilla.");
    } finally {
      setBajando(false);
    }
  };

  if (cargando) {
    return <p>Cargando plantillas de solicitud...</p>;
  }

  return (
    <div className="solicitudes-page">
      <div className="solicitudes-encabezado">
        <h2>Plantillas de solicitud recurrente</h2>
        <button type="button" onClick={() => setMostrarCrear(true)}>
          Crear plantilla
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="solicitud-detalle-info">
        <table className="tabla-usuarios">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo de solicitud</th>
              <th>Prioridad por defecto</th>
              <th># Tareas</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {plantillas.map((plantilla) => (
              <tr key={plantilla.id}>
                <td>{plantilla.nombre}</td>
                <td>{plantilla.tipo_solicitud}</td>
                <td>{plantilla.orden_prioridad_default}</td>
                <td>{plantilla.cantidad_tareas}</td>
                <td>
                  <span className={plantilla.activo ? "tarea-estado tarea-estado-completa" : "tarea-estado"}>
                    {plantilla.activo ? "Activa" : "Inactiva"}
                  </span>
                </td>
                <td>
                  <button type="button" className="secundario" onClick={() => abrirEdicion(plantilla)}>
                    Editar
                  </button>
                  {plantilla.activo && (
                    <button type="button" className="peligro" onClick={() => setPlantillaABajar(plantilla)}>
                      Dar de baja
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {mostrarCrear && (
        <div className="modal-overlay" onClick={() => setMostrarCrear(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Crear plantilla de solicitud</h3>
            <CrearPlantillaSolicitudFormulario onCreada={alCrear} onCancelar={() => setMostrarCrear(false)} />
          </div>
        </div>
      )}

      {plantillaEnEdicion && (
        <div className="modal-overlay" onClick={() => setPlantillaEnEdicion(null)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <h3>Editar plantilla de solicitud</h3>
            <EditarPlantillaSolicitudFormulario
              plantilla={plantillaEnEdicion}
              onGuardado={alGuardarEdicion}
              onCancelar={() => setPlantillaEnEdicion(null)}
            />
          </div>
        </div>
      )}

      {plantillaABajar && (
        <ConfirmModal
          titulo="Dar de baja"
          mensaje={`¿Seguro que quieres dar de baja la plantilla "${plantillaABajar.nombre}"? Dejará de aparecer como opción al crear una solicitud nueva.`}
          confirmando={bajando}
          textoConfirmar="Sí, dar de baja"
          textoConfirmando="Procesando..."
          onConfirmar={confirmarBaja}
          onCancelar={() => setPlantillaABajar(null)}
        />
      )}
    </div>
  );
}
