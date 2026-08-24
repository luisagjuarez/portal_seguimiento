import { useState } from "react";
import ChatBubble from "./ChatBubble.jsx";
import ClienteAutocomplete from "./ClienteAutocomplete.jsx";
import AdjuntosPaso from "./AdjuntosPaso.jsx";
import { crearSolicitudChat } from "../api.js";

const PASOS = ["titulo", "descripcion", "cliente", "adjuntos", "resumen", "listo"];
const SALUDO_INICIAL = "¡Hola! Vamos a registrar tu solicitud. ¿Cuál es el título breve de tu solicitud?";

function TextoInputPaso({ placeholder, multiline, onSubmit }) {
  const [valor, setValor] = useState("");

  const enviar = () => {
    const limpio = valor.trim();
    if (!limpio) return;
    onSubmit(limpio);
    setValor("");
  };

  if (multiline) {
    return (
      <div className="paso-input">
        <textarea
          rows={3}
          placeholder={placeholder}
          value={valor}
          onChange={(event) => setValor(event.target.value)}
        />
        <button type="button" onClick={enviar}>
          Enviar
        </button>
      </div>
    );
  }

  return (
    <div className="paso-input">
      <input
        type="text"
        placeholder={placeholder}
        value={valor}
        onChange={(event) => setValor(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && enviar()}
      />
      <button type="button" onClick={enviar}>
        Enviar
      </button>
    </div>
  );
}

export default function ChatWindow({ usuarioActual }) {
  const emailUsuario = usuarioActual?.correo_electronico || "";
  const [pasoIndex, setPasoIndex] = useState(0);
  const [datos, setDatos] = useState({
    email: emailUsuario,
    titulo: "",
    descripcion: "",
    cliente: null,
    adjuntos: [],
  });
  const [historial, setHistorial] = useState([{ from: "bot", texto: SALUDO_INICIAL }]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [resultado, setResultado] = useState(null);

  const paso = PASOS[pasoIndex];

  const avanzar = (siguienteHistorialBot) => {
    setHistorial((prev) => [...prev, { from: "bot", texto: siguienteHistorialBot }]);
    setPasoIndex((i) => i + 1);
  };

  const responderUsuario = (texto) => {
    setHistorial((prev) => [...prev, { from: "user", texto }]);
  };

  const manejarTitulo = (valor) => {
    responderUsuario(valor);
    setDatos((d) => ({ ...d, titulo: valor }));
    avanzar("Cuéntame con más detalle qué necesitas.");
  };

  const manejarDescripcion = (valor) => {
    responderUsuario(valor);
    setDatos((d) => ({ ...d, descripcion: valor }));
    avanzar("¿Para qué cliente es esta solicitud? (puedes buscar uno existente o escribir uno nuevo)");
  };

  const manejarCliente = (nombreClienteONull) => {
    responderUsuario(nombreClienteONull || "Definir después");
    setDatos((d) => ({ ...d, cliente: nombreClienteONull }));
    avanzar("¿Quieres adjuntar algún archivo? Puedes elegir uno o varios, o continuar sin adjuntar.");
  };

  const manejarAdjuntos = (archivos) => {
    responderUsuario(
      archivos.length > 0 ? `${archivos.length} archivo(s) adjunto(s)` : "Sin adjuntos"
    );
    setDatos((d) => ({ ...d, adjuntos: archivos }));
    avanzar("Este es el resumen de tu solicitud, ¿confirmamos?");
  };

  const confirmar = async () => {
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await crearSolicitudChat({
        solicitanteEmail: datos.email,
        titulo: datos.titulo,
        descripcion: datos.descripcion,
        cliente: datos.cliente,
        adjuntos: datos.adjuntos,
      });
      setResultado(respuesta);
      setHistorial((prev) => [
        ...prev,
        {
          from: "bot",
          texto: `Listo. Creé la solicitud #${respuesta.id_solicitud}: "${respuesta.titulo}" (estatus: ${respuesta.status_cd}).`,
        },
      ]);
      setPasoIndex(PASOS.indexOf("listo"));
    } catch (err) {
      setError(err.message || "No se pudo crear la solicitud. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-historial">
        {historial.map((mensaje, index) => (
          <ChatBubble key={index} from={mensaje.from}>
            {mensaje.texto}
          </ChatBubble>
        ))}
      </div>

      <div className="chat-paso-actual">
        {paso === "titulo" && (
          <TextoInputPaso placeholder="Ej. Reporte de gastos personalizado" onSubmit={manejarTitulo} />
        )}
        {paso === "descripcion" && (
          <TextoInputPaso
            placeholder="Describe con detalle tu solicitud..."
            multiline
            onSubmit={manejarDescripcion}
          />
        )}
        {paso === "cliente" && (
          <ClienteAutocomplete onSelect={manejarCliente} onSkip={() => manejarCliente(null)} />
        )}
        {paso === "adjuntos" && <AdjuntosPaso onSubmit={manejarAdjuntos} />}
        {paso === "resumen" && (
          <div className="resumen">
            <p>
              <strong>Correo:</strong> {datos.email}
            </p>
            <p>
              <strong>Título:</strong> {datos.titulo}
            </p>
            <p>
              <strong>Descripción:</strong> {datos.descripcion}
            </p>
            <p>
              <strong>Cliente:</strong> {datos.cliente || "Por definir"}
            </p>
            <p>
              <strong>Adjuntos:</strong>{" "}
              {datos.adjuntos.length > 0
                ? datos.adjuntos.map((archivo) => archivo.name).join(", ")
                : "Sin adjuntos"}
            </p>
            {error && <p className="error-text">{error}</p>}
            <div className="resumen-acciones">
              <button type="button" disabled={enviando} onClick={confirmar}>
                {enviando ? "Creando..." : "Confirmar y crear solicitud"}
              </button>
              <button type="button" className="secundario" disabled={enviando} onClick={() => setPasoIndex(0)}>
                Empezar de nuevo
              </button>
            </div>
          </div>
        )}
        {paso === "listo" && resultado && (
          <div className="resumen">
            <p>Puedes cerrar esta ventana o registrar otra solicitud.</p>
            <button
              type="button"
              onClick={() => {
                setDatos({ email: emailUsuario, titulo: "", descripcion: "", cliente: null, adjuntos: [] });
                setHistorial([{ from: "bot", texto: SALUDO_INICIAL }]);
                setResultado(null);
                setPasoIndex(0);
              }}
            >
              Registrar otra solicitud
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
