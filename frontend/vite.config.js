import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/dovela_control/",
  plugins: [react()],
  server: {
    port: 5173,
  },
});
