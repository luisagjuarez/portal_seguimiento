import { useEffect, useState } from "react";
import { fetchClientes } from "../api.js";

export default function ClienteAutocomplete({ onSelect, onSkip }) {
  const [texto, setTexto] = useState("");
  const [sugerencias, setSugerencias] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!texto) {
      setSugerencias([]);
      return;
    }
    const timeoutId = setTimeout(() => {
      fetchClientes(texto)
        .then(setSugerencias)
        .catch(() => setError("No se pudieron cargar sugerencias de clientes."));
    }, 250);
    return () => clearTimeout(timeoutId);
  }, [texto]);

  return (
    <div className="cliente-autocomplete">
      <input
        type="text"
        placeholder="Escribe el nombre del cliente..."
        value={texto}
        onChange={(event) => setTexto(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && texto.trim()) {
            onSelect(texto.trim());
          }
        }}
      />
      {error && <p className="error-text">{error}</p>}
      {sugerencias.length > 0 && (
        <ul className="sugerencias">
          {sugerencias.map((nombre) => (
            <li key={nombre}>
              <button type="button" onClick={() => onSelect(nombre)}>
                {nombre}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="cliente-acciones">
        <button
          type="button"
          disabled={!texto.trim()}
          onClick={() => onSelect(texto.trim())}
        >
          Usar "{texto.trim() || "..."}" como cliente nuevo
        </button>
        <button type="button" className="secundario" onClick={onSkip}>
          Definir después
        </button>
      </div>
    </div>
  );
}
