import { useState } from "react";

export const MAX_ADJUNTOS = 5;
export const MAX_TAMANO_BYTES = 10 * 1024 * 1024;

export default function AdjuntosInput({ archivos, onChange }) {
  const [error, setError] = useState(null);

  const agregarArchivos = (event) => {
    const nuevos = Array.from(event.target.files || []);
    event.target.value = "";
    if (!nuevos.length) return;

    if (archivos.length + nuevos.length > MAX_ADJUNTOS) {
      setError(`Puedes adjuntar máximo ${MAX_ADJUNTOS} archivos.`);
      return;
    }
    const demasiadoGrande = nuevos.find((archivo) => archivo.size > MAX_TAMANO_BYTES);
    if (demasiadoGrande) {
      setError(`"${demasiadoGrande.name}" supera el límite de 10 MB.`);
      return;
    }

    setError(null);
    onChange([...archivos, ...nuevos]);
  };

  const quitarArchivo = (index) => {
    onChange(archivos.filter((_, i) => i !== index));
  };

  return (
    <div className="adjuntos-input">
      <p className="adjuntos-ayuda">
        Puedes adjuntar hasta {MAX_ADJUNTOS} archivos (máx. 10 MB cada uno), o dejarlo vacío.
      </p>
      <label className="adjuntos-dropzone">
        <input type="file" multiple onChange={agregarArchivos} />
        Elegir archivo(s)...
      </label>
      {error && <p className="error-text">{error}</p>}
      {archivos.length > 0 && (
        <ul className="adjuntos-lista">
          {archivos.map((archivo, index) => (
            <li key={`${archivo.name}-${index}`}>
              <span>{archivo.name}</span>
              <button type="button" className="secundario" onClick={() => quitarArchivo(index)}>
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
