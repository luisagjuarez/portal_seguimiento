const STORAGE_KEY = "dovela:theme";

export function getPreferredTheme() {
  try {
    const guardado = localStorage.getItem(STORAGE_KEY);
    if (guardado === "light" || guardado === "dark") return guardado;
  } catch {
    // localStorage no disponible (p. ej. modo privado); seguimos con la preferencia del sistema
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function setTheme(tema) {
  document.documentElement.setAttribute("data-theme", tema);
  try {
    localStorage.setItem(STORAGE_KEY, tema);
  } catch {
    // el tema simplemente no persiste entre recargas
  }
}
