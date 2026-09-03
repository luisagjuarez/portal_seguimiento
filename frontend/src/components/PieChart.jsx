const CX = 50;
const CY = 50;
const R = 40;

function puntoEnCirculo(anguloGrados) {
  const anguloRad = ((anguloGrados - 90) * Math.PI) / 180;
  return [CX + R * Math.cos(anguloRad), CY + R * Math.sin(anguloRad)];
}

function construirRebanadas(data, total) {
  let anguloAcumulado = 0;
  return data.map((item) => {
    const porcentaje = total > 0 ? item.value / total : 0;
    const anguloInicio = anguloAcumulado;
    const anguloFin = anguloAcumulado + porcentaje * 360;
    anguloAcumulado = anguloFin;

    let path;
    if (porcentaje >= 0.9999) {
      path = `M ${CX - R},${CY} A ${R},${R} 0 1,1 ${CX + R},${CY} A ${R},${R} 0 1,1 ${CX - R},${CY} Z`;
    } else {
      const [x0, y0] = puntoEnCirculo(anguloInicio);
      const [x1, y1] = puntoEnCirculo(anguloFin);
      const largeArc = anguloFin - anguloInicio > 180 ? 1 : 0;
      path = `M ${CX},${CY} L ${x0},${y0} A ${R},${R} 0 ${largeArc},1 ${x1},${y1} Z`;
    }

    return { ...item, path, porcentaje };
  });
}

export default function PieChart({ titulo, data }) {
  const total = data.reduce((suma, item) => suma + item.value, 0);

  return (
    <div className="pie-chart">
      <h4>{titulo}</h4>
      {total === 0 ? (
        <p>Sin datos en este rango.</p>
      ) : (
        <div className="pie-chart-cuerpo">
          <svg viewBox="0 0 100 100" className="pie-chart-svg" role="img" aria-label={titulo}>
            {construirRebanadas(data, total).map((rebanada) => (
              <path
                key={rebanada.label}
                d={rebanada.path}
                style={{ fill: rebanada.color, stroke: "var(--bg-elevated)" }}
                strokeWidth="2"
              />
            ))}
          </svg>
          <ul className="pie-chart-leyenda">
            {data.map((item) => (
              <li key={item.label}>
                <span className="pie-chart-muestra" style={{ backgroundColor: item.color }} />
                <span className="pie-chart-etiqueta">{item.label}</span>
                <span className="pie-chart-valor">
                  {item.value} ({total > 0 ? Math.round((item.value / total) * 100) : 0}%)
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
