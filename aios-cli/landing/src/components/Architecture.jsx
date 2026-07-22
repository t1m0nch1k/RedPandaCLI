import './Architecture.css';

export default function Architecture() {
  return (
    <div className="arch-section fade-in">
      <div className="arch-header">
        <h2 className="arch-title">Архитектура под капотом</h2>
        <p className="arch-subtitle">Чистая и расширяемая структура проекта</p>
      </div>

      <div className="arch-content">
        <div className="arch-diagram">
          <div className="arch-block intent">
            <div className="arch-icon"><i className="fi fi-rr-terminal"></i></div>
            <span>Intent Engine</span>
          </div>
          <div className="arch-arrow">→</div>
          <div className="arch-block planner">
            <div className="arch-icon"><i className="fi fi-rr-list-check"></i></div>
            <span>Planner</span>
          </div>
          <div className="arch-arrow">→</div>
          <div className="arch-block executor">
            <div className="arch-icon"><i className="fi fi-rr-bolt"></i></div>
            <span>Executor</span>
          </div>
          <div className="arch-arrow">→</div>
          <div className="arch-block provider">
            <div className="arch-icon"><i className="fi fi-rr-robot"></i></div>
            <span>LLM Provider</span>
          </div>
        </div>

        <div className="arch-roadmap">
          <h3>Roadmap (Что дальше?)</h3>
          <ul className="roadmap-list">
            <li><span className="check"><i className="fi fi-rr-check-circle"></i></span> Rule-based планирование</li>
            <li><span className="loading"><i className="fi fi-rr-hourglass-end"></i></span> LLM-based планирование</li>
            <li><span className="loading"><i className="fi fi-rr-hourglass-end"></i></span> Plugin architecture</li>
            <li><span className="loading"><i className="fi fi-rr-hourglass-end"></i></span> Voice, Vision, Desktop UI</li>
            <li><span className="loading"><i className="fi fi-rr-hourglass-end"></i></span> Autonomous Agents</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
