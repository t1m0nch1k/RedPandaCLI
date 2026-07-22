import { useState } from 'react';
import './Cta.css';

export default function Cta() {
  const [copied, setCopied] = useState(false);
  const installCode = 'uv pip install -e .';

  const handleCopy = () => {
    navigator.clipboard.writeText(installCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="cta-section fade-in">
      <div className="cta-content">
        <h2 className="cta-title">Готовы к новому уровню CLI?</h2>
        <p className="cta-subtitle">Установите AIOS CLI прямо сейчас и начните строить агентов будущего.</p>
        
        <div className="install-box">
          <code>{installCode}</code>
          <button className="copy-btn" onClick={handleCopy}>
            {copied ? 'Скопировано!' : 'Копировать'}
          </button>
        </div>
      </div>
      
      <footer className="footer">
        <p>© {new Date().getFullYear()} AIOS Ecosystem. All rights reserved.</p>
      </footer>
    </div>
  );
}
