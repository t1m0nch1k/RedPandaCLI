import { useEffect, useRef } from 'react';
import Lenis from 'lenis';
import Header from './components/Header';
import Hero from './components/Hero';
import Features from './components/Features';
import Terminal from './components/Terminal';
import Architecture from './components/Architecture';
import Cta from './components/Cta';
import './App.css';

function App() {
  const containerRef = useRef(null);

  useEffect(() => {
    // Initialize Lenis for smooth scrolling
    const lenis = new Lenis({
      autoRaf: true,
      duration: 1.8, // Increased duration for slower, smoother scroll
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 0.8, // Slightly softer mouse wheel effect
      touchMultiplier: 1.5,
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      {
        root: null, // use viewport instead of containerRef since we removed overflow
        threshold: 0.2, // Trigger when 20% visible
      }
    );

    // Observe all elements with fade-in class
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach((el) => observer.observe(el));

    return () => {
      fadeElements.forEach((el) => observer.unobserve(el));
      lenis.destroy();
    };
  }, []);

  return (
    <div className="scroll-container" ref={containerRef}>
      <Header />
      
      {/* Hero Section */}
      <section className="section" id="home">
        <Hero />
      </section>

      {/* Features Bento Grid */}
      <section className="section" id="features">
        <Features />
      </section>

      {/* Terminal Simulation */}
      <section className="section" id="terminal">
        <Terminal />
      </section>

      {/* Architecture & Roadmap */}
      <section className="section" id="architecture">
        <Architecture />
      </section>

      {/* CTA / Installation */}
      <section className="section" id="install">
        <Cta />
      </section>
    </div>
  );
}

export default App;
