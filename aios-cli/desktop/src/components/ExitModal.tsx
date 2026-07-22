
import { invoke } from "@tauri-apps/api/core";

interface ExitModalProps {
  onClose: () => void;
}

export default function ExitModal({ onClose }: ExitModalProps) {
  const handleExit = async () => {
    await invoke("exit_app");
  };

  const handleMinimize = async () => {
    await invoke("minimize_to_tray");
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="confirm-modal">
        <div className="modal-header">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
          <h2>Выход из системы</h2>
        </div>
        <div className="modal-body">
          Желаете полностью закрыть программу или свернуть её в трей?
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Отмена
          </button>
          <button className="btn-secondary" onClick={handleMinimize}>
            Свернуть в трей
          </button>
          <button className="btn-danger" onClick={handleExit}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
