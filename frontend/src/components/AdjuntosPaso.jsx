import { useState } from "react";
import AdjuntosInput from "./AdjuntosInput.jsx";

export default function AdjuntosPaso({ onSubmit }) {
  const [archivos, setArchivos] = useState([]);

  return (
    <div className="adjuntos-paso">
      <AdjuntosInput archivos={archivos} onChange={setArchivos} />
      <div className="resumen-acciones">
        <button type="button" onClick={() => onSubmit(archivos)}>
          {archivos.length > 0 ? "Continuar" : "Continuar sin adjuntar"}
        </button>
      </div>
    </div>
  );
}
