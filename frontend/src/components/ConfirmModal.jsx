export default function ConfirmModal({ titulo, mensaje, onConfirmar, onCancelar, confirmando }) {
  return (
    <div className="modal-overlay" onClick={onCancelar}>
      <div className="modal-content" onClick={(event) => event.stopPropagation()}>
        <h3>{titulo}</h3>
        <p>{mensaje}</p>
        <div className="resumen-acciones">
          <button type="button" className="peligro" disabled={confirmando} onClick={onConfirmar}>
            {confirmando ? "Borrando..." : "Sí, borrar"}
          </button>
          <button type="button" className="secundario" disabled={confirmando} onClick={onCancelar}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
