import './Header.css';

export default function Header() {
  return (
    <header className="header fade-in">
      <div className="logo">
        <span className="logo-icon">100</span>
        <div className="logo-text">
          <span className="logo-title">Red Panda</span>
          <span className="logo-subtitle">hero</span>
        </div>
      </div>
      
      <nav className="nav">
        <a href="#offres" className="nav-item">NOS OFFRES <span className="arrow-down">v</span></a>
        <a href="#realisations" className="nav-item">NOS RÉALISATIONS</a>
        <a href="#notes" className="nav-item">NOS NOTES</a>
      </nav>
      
      <div className="contact-btn-wrapper">
        <button className="contact-btn">
          <span className="icon-circle">➔</span>
          <span className="contact-text">Contact</span>
        </button>
      </div>
    </header>
  );
}
