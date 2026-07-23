import './Features.css';

export default function Features() {
  return (
    <div className="features-container">
      <div className="features-header fade-in">
        <h2 className="features-title">Что умеет AIOS CLI</h2>
        <p className="features-subtitle">Мощный локальный движок под капотом вашего терминала</p>
      </div>
      
      <div className="bento-grid">
        {/* Large item spanning 2 columns */}
        <div className="bento-item col-span-2 fade-in">
          <div className="bento-icon"><i className="fi fi-rr-bolt"></i></div>
          <h3>Local Intent Engine</h3>
          <p>Мгновенный перехват и выполнение простых команд (вроде <code>open chrome</code> или <code>git status</code>) локально, экономя время и токены. Всё остальное маршрутизируется к LLM.</p>
        </div>
        
        {/* Regular items */}
        <div className="bento-item fade-in" style={{ transitionDelay: '0.1s' }}>
          <div className="bento-icon"><i className="fi fi-rr-plug"></i></div>
          <h3>Provider Agnostic</h3>
          <p>Легко переключайтесь между Ollama, OpenAI и другими совместимыми провайдерами одной командой.</p>
        </div>
        
        <div className="bento-item fade-in" style={{ transitionDelay: '0.2s' }}>
          <div className="bento-icon"><i className="fi fi-rr-wrench-simple"></i></div>
          <h3>Tool Registry</h3>
          <p>Архитектура Open/Closed позволяет добавлять новые инструменты без изменения существующего кода.</p>
        </div>
        
        <div className="bento-item col-span-2 fade-in" style={{ transitionDelay: '0.3s' }}>
          <div className="bento-icon"><i className="fi fi-rr-brain"></i></div>
          <h3>Rule-Based Planner</h3>
          <p>Интеллектуальное построение плана выполнения задач на основе перехваченных интентов и доступных инструментов.</p>
        </div>
      </div>
    </div>
  );
}
