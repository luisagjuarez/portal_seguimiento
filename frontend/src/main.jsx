import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./styles.css";

// El portal se sirve bajo /dovela_control (subpath fijo pedido por infraestructura) pero la
// raíz también debe seguir funcionando en paralelo con el mismo build — el basename se calcula
// según por dónde entró el usuario, no se fija en duro.
const basename = window.location.pathname.startsWith("/dovela_control") ? "/dovela_control" : "/";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
