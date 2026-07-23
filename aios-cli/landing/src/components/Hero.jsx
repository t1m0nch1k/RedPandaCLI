import './Hero.css';
import { Canvas } from '@react-three/fiber';
import { Environment, OrbitControls, ContactShadows } from '@react-three/drei';
import PandaModel from './PandaModel';

export default function Hero() {
  return (
    <div className="hero-container fade-in">
      <div className="hero-left">
        <div className="image-wrapper" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          <Canvas camera={{ position: [0, 0, 5], fov: 45 }} style={{ background: 'transparent' }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1.5} />
            <Environment preset="city" />
            
            <PandaModel position={[0, -1, 0]} scale={2} />
            
            <OrbitControls enableZoom={false} enablePan={false} />
            <ContactShadows position={[0, -1.5, 0]} opacity={0.4} scale={10} blur={2} far={4} color="#000000" />
          </Canvas>
        </div>
      </div>
      
      <div className="hero-right">
        <div className="hero-content">
          <div className="hero-subtitle">
            Первый клиент экосистемы AIOS
          </div>
          
          <h1 className="hero-title">
            AIOS<br />
            CLI
          </h1>
          
          <div className="hero-description">
            <div className="desc-column">
              Провайдер-агностичный CLI-ассистент с мгновенным выполнением команд.
            </div>
            <div className="desc-column">
              Локальный intent engine, rule-based планировщик и встроенный реестр инструментов.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
