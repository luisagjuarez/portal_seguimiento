import { useState } from "react";
import { getPreferredTheme, setTheme } from "../theme.js";

export default function ThemeToggle() {
  const [tema, setTemaLocal] = useState(getPreferredTheme);

  const alternar = () => {
    const siguiente = tema === "dark" ? "light" : "dark";
    setTheme(siguiente);
    setTemaLocal(siguiente);
  };

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={alternar}
      aria-label={tema === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={tema === "dark" ? "Modo claro" : "Modo oscuro"}
    >
      {tema === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
