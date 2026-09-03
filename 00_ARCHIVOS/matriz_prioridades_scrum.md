# Especificación de Niveles de Prioridad para Backlog y Solicitudes

Este documento establece el estándar de priorización (escala 1 al 5) para solicitudes.
---

## 1. Tabla de Mapeo de Prioridades

| Nivel (Código) | Etiqueta en Español | Etiqueta Técnica / Inglés | Color Visual | Código Hex | SLA / Criterio de Atención Ágil |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | **Crítica** | Blocker / Critical | Rojo Carmesí | `#D32F2F` | Bloqueo total en producción, caída de servicios, fallo de seguridad o afectación financiera/operativa inmediata. Detiene el sprint activo. |
| **2** | **Alta** | Urgent / Major | Naranja Ámbar | `#F57C00` | Funcionalidad core afectada sin solución alterna (*workaround* viable) o hito comprometido para el cierre del sprint actual. |
| **3** | **Media** | Standard / Normal | Amarillo Mostaza | `#FBC02D` | Flujo principal afectado pero con solución temporal, o historias de usuario del backlog regular a planificar en el sprint. |
| **4** | **Baja** | Minor / Low | Azul Celeste | `#0288D1` | Mejoras de usabilidad menores, deuda técnica residual, optimizaciones no urgentes o ajustes visuales secundarios. |
| **5** | **Trivial** | Trivial / Nice-to-have | Gris Pizarra | `#757575` | Sugerencias estéticas, ideas de mejora a futuro (*backlog icebox*), sin impacto en negocio ni bloqueo funcional. |

---

## 2. Reglas de Negocio y Operación para el Tablero

1. **Prioridad por Defecto (Default = 3 - Media):**
   - Toda solicitud entrante se inicializa con nivel `3 (Media)` hasta su evaluación en sesión de refinamiento (*Backlog Refinement*) o triaje técnico.

2. **Criterio de Excepción para Nivel 1 (Crítica):**
   - Requiere notificación inmediata al Scrum Master / Tech Lead.
   - Habilita la suspensión temporal de tareas planificadas para atender el bloqueo (*interrupt handler*).

3. **Separación de Semántica de Color:**
   - Se evita el color verde para niveles bajos, reservando los tonos verdes exclusivamente para estados completados (`Done`, `Released`, `Approved`).
   - El azul (`#0288D1`) y gris (`#757575`) proporcionan neutralidad visual y evitan fatiga en el tablero.

---

## 3. Estructura JSON para Configuración / Adecuación de Software

```json
{
  "priority_scheme": {
    "levels": [
      {
        "id": 1,
        "name_es": "Crítica",
        "name_en": "Critical / Blocker",
        "color_name": "Crimson Red",
        "hex": "#D32F2F",
        "is_interrupt": true,
        "description": "Fallo crítico en producción o bloqueo absoluto del sprint."
      },
      {
        "id": 2,
        "name_es": "Alta",
        "name_en": "Urgent / Major",
        "color_name": "Amber Orange",
        "hex": "#F57C00",
        "is_interrupt": false,
        "description": "Afectación de flujo clave sin workaround viable."
      },
      {
        "id": 3,
        "name_es": "Media",
        "name_en": "Standard / Normal",
        "color_name": "Mustard Yellow",
        "hex": "#FBC02D",
        "is_interrupt": false,
        "is_default": true,
        "description": "Historias estándar de sprint y fallos con solución temporal."
      },
      {
        "id": 4,
        "name_es": "Baja",
        "name_en": "Minor / Low",
        "color_name": "Sky Blue",
        "hex": "#0288D1",
        "is_interrupt": false,
        "description": "Deuda técnica residual o mejoras cosméticas secundarias."
      },
      {
        "id": 5,
        "name_es": "Trivial",
        "name_en": "Trivial / Nice-to-have",
        "color_name": "Slate Grey",
        "hex": "#757575",
        "is_interrupt": false,
        "description": "Deseos, mejoras estéticas o ideas sin urgencia técnica."
      }
    ]
  }
}
```
