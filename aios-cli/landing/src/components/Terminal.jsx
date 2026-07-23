import { useEffect, useState } from 'react';

const commands = [
  { cmd: 'aios doctor', desc: 'Environment and provider diagnostic' },
  { cmd: 'aios tools', desc: 'List available native tools' },
  { cmd: 'aios config --set-provider ollama', desc: 'Change provider on the fly' },
  { cmd: 'aios chat', desc: 'Launch interactive terminal chat' }
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
        }, Math.random() * 50 + 50);
        return () => clearTimeout(timeout);
      } else {
        const timeout = setTimeout(() => setIsTyping(false), 2000);
        return () => clearTimeout(timeout);
      }
    } else {
      if (typedText.length > 0) {
        const timeout = setTimeout(() => {
          setTypedText(typedText.slice(0, -1));
        }, 30);
        return () => clearTimeout(timeout);
      } else {
        setCurrentCmdIndex((prev) => (prev + 1) % commands.length);
        setIsTyping(true);
      }
    }
  }, [typedText, isTyping, currentCmdIndex]);

  return (
    <div style={{ fontFamily: 'var(--font-mono)' }}>
      <div style={{ marginBottom: '1rem', borderBottom: '1px dashed var(--accent-color)', paddingBottom: '0.5rem' }}>
        <span style={{ opacity: 0.5 }}>{'[ '}</span> 
        sys.log 
        <span style={{ opacity: 0.5 }}>{' ]'}</span>
      </div>
      <div>
        <div>
          <span style={{ color: 'var(--accent-color)', marginRight: '0.5rem' }}>$</span> 
          <span>{typedText}</span>
          <span style={{ display: 'inline-block', width: '8px', height: '1.2em', backgroundColor: 'var(--accent-color)', verticalAlign: 'middle', animation: 'blink 1s step-end infinite' }}></span>
        </div>
        <div style={{ minHeight: '1.5em', marginTop: '0.5rem', opacity: 0.7 }}>
          {typedText === commands[currentCmdIndex].cmd && !isTyping ? (
            <span># {commands[currentCmdIndex].desc}</span>
          ) : <br/>}
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes blink { 50% { opacity: 0; } }
      `}} />
    </div>
  );
}

