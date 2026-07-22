import { useEffect, useState } from 'react';
import './Terminal.css';

const commands = [
  { cmd: 'aios doctor', desc: 'Диагностика окружения и провайдера' },
  { cmd: 'aios tools', desc: 'Список доступных инструментов' },
  { cmd: 'aios config --set-provider ollama', desc: 'Смена провайдера на лету' },
  { cmd: 'aios chat', desc: 'Запуск интерактивного чата' }
];

export default function Terminal() {
  const [currentCmdIndex, setCurrentCmdIndex] = useState(0);
  const [typedText, setTypedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    const currentCommand = commands[currentCmdIndex].cmd;
    
    if (isTyping) {
      if (typedText.length < currentCommand.length) {
        const timeout = setTimeout(() => {
          setTypedText(currentCommand.slice(0, typedText.length + 1));
        }, Math.random() * 50 + 50); // random typing speed between 50-100ms
        return () => clearTimeout(timeout);
      } else {
        // Finished typing, pause then erase
        const timeout = setTimeout(() => setIsTyping(false), 2000);
        return () => clearTimeout(timeout);
      }
    } else {
      if (typedText.length > 0) {
        const timeout = setTimeout(() => {
          setTypedText(typedText.slice(0, -1));
        }, 30); // faster erase
        return () => clearTimeout(timeout);
      } else {
        // Finished erasing, move to next command
        setCurrentCmdIndex((prev) => (prev + 1) % commands.length);
        setIsTyping(true);
      }
    }
  }, [typedText, isTyping, currentCmdIndex]);

  return (
    <div className="terminal-section fade-in">
      <div className="terminal-header">
        <h2 className="terminal-title">Управление из терминала</h2>
        <p className="terminal-subtitle">Всё что вам нужно — прямо под рукой.</p>
      </div>

      <div className="terminal-window">
        <div className="terminal-bar">
          <div className="terminal-dots">
            <span className="dot red"></span>
            <span className="dot yellow"></span>
            <span className="dot green"></span>
          </div>
          <div className="terminal-title-bar">bash — aios-cli</div>
        </div>
        <div className="terminal-body">
          <div className="terminal-line">
            <span className="prompt">$</span> 
            <span className="command">{typedText}</span>
            <span className="cursor"></span>
          </div>
          <div className="terminal-output fade-in">
            {typedText === commands[currentCmdIndex].cmd && !isTyping ? (
              <span className="output-text"># {commands[currentCmdIndex].desc}</span>
            ) : <br/>}
          </div>
        </div>
      </div>
    </div>
  );
}
