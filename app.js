import { animate, spring, inView, stagger } from "https://cdn.jsdelivr.net/npm/motion@11.11.13/+esm";

document.addEventListener("DOMContentLoaded", () => {

  // ═══════════════════════════════════
  // 0. Animated dot grid background
  // ═══════════════════════════════════
  const canvas = document.getElementById("dot-grid");
  const ctx = canvas.getContext("2d");
  let mouseX = -1000, mouseY = -1000;

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas, { passive: true });

  document.addEventListener("mousemove", (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }, { passive: true });

  function drawDots() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const spacing = 40;
    const baseAlpha = 0.08;
    const hoverRadius = 150;

    for (let x = spacing; x < canvas.width; x += spacing) {
      for (let y = spacing; y < canvas.height; y += spacing) {
        const dx = x - mouseX;
        const dy = y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        let alpha = baseAlpha;
        let size = 1;

        if (dist < hoverRadius) {
          const factor = 1 - dist / hoverRadius;
          alpha = baseAlpha + factor * 0.25;
          size = 1 + factor * 1.5;
        }

        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(224, 90, 48, ${alpha})`;
        ctx.fill();
      }
    }

    requestAnimationFrame(drawDots);
  }
  drawDots();

  // ═══════════════════════════════════
  // 1. Navbar scroll effect
  // ═══════════════════════════════════
  const navbar = document.getElementById("navbar");
  window.addEventListener("scroll", () => {
    navbar.classList.toggle("scrolled", window.scrollY > 40);
  }, { passive: true });

  // ═══════════════════════════════════
  // 2. Hero entrance — staggered, organic
  // ═══════════════════════════════════
  const heroAnims = [
    { el: "[data-animate='eyebrow']", props: { opacity: [0, 1], x: [-20, 0] }, opts: { delay: 0.3, duration: 0.8 } },
    { el: ".hero-title-word", props: { opacity: [0, 1], y: [40, 0] }, opts: { delay: stagger(0.12, { startDelay: 0.5 }), duration: 1, easing: [0.22, 1, 0.36, 1] } },
    { el: "[data-animate='desc']", props: { opacity: [0, 1], y: [20, 0] }, opts: { delay: 1, duration: 0.8 } },
    { el: "[data-animate='actions']", props: { opacity: [0, 1], y: [15, 0] }, opts: { delay: 1.2, duration: 0.7, easing: spring({ stiffness: 120, damping: 14 }) } },
    { el: "[data-animate='mascot-row']", props: { opacity: [0, 1], y: [10, 0] }, opts: { delay: 1.5, duration: 0.6 } },
    { el: "[data-animate='terminal']", props: { opacity: [0, 1], y: [30, 0], scale: [0.97, 1] }, opts: { delay: 0.8, duration: 1.2, easing: [0.22, 1, 0.36, 1] } },
  ];

  heroAnims.forEach(({ el, props, opts }) => {
    try { animate(el, props, opts); } catch (e) { /* skip missing */ }
  });

  // ═══════════════════════════════════
  // 3. Terminal typing
  // ═══════════════════════════════════
  const termBody = document.getElementById("terminal-body");
  const termLines = [
    { type: "cmd", text: "aios doctor" },
    { type: "out", html: `<span class="t-success">✓</span> Python 3.12.4\n<span class="t-success">✓</span> Ollama running · qwen3:8b\n<span class="t-success">✓</span> 9 tools registered\nAll systems operational.` },
    { type: "cmd", text: 'aios code "add JWT auth to routes"' },
    { type: "out", html: `<span class="t-info">→</span> Reading src/routes/user.py\n<span class="t-info">→</span> Generating patch...\n<span class="t-success">✓</span> Applied 2 edits, 1 file changed\n<span class="t-success">✓</span> Auto-commit: <em>feat: add JWT auth</em>` },
  ];

  let lineIdx = 0;
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  async function typeLine() {
    if (lineIdx >= termLines.length) {
      const el = document.createElement("div");
      el.className = "t-line";
      el.style.opacity = "1";
      el.innerHTML = `<span class="t-prompt">❯ </span><span class="t-cursor"></span>`;
      termBody.appendChild(el);
      return;
    }

    const data = termLines[lineIdx];
    const el = document.createElement("div");
    el.className = "t-line";
    termBody.appendChild(el);
    animate(el, { opacity: [0, 1] }, { duration: 0.15 });

    if (data.type === "cmd") {
      el.innerHTML = `<span class="t-prompt">❯ </span><span class="t-cmd"></span>`;
      const cmdSpan = el.querySelector(".t-cmd");
      for (let i = 0; i < data.text.length; i++) {
        cmdSpan.textContent += data.text[i];
        await sleep(30 + Math.random() * 45);
      }
      await sleep(500);
    } else {
      el.innerHTML = `<div class="t-output">${data.html.replace(/\n/g, '<br>')}</div>`;
      await sleep(700);
    }

    lineIdx++;
    typeLine();
  }

  setTimeout(typeLine, 2200);

  // ═══════════════════════════════════
  // 4. Marquee
  // ═══════════════════════════════════
  const providers = [
    "Ollama", "OpenAI", "Gemini", "Anthropic", "Groq", "DeepSeek",
    "Mistral", "OpenRouter", "Together AI", "Fireworks", "Perplexity",
    "Replicate", "Cohere", "HuggingFace", "AWS Bedrock", "Azure",
    "LM Studio", "vLLM", "LocalAI", "Cerebras", "xAI Grok",
  ];

  const track = document.getElementById("marquee-track");
  for (let copy = 0; copy < 3; copy++) {
    providers.forEach(name => {
      const item = document.createElement("span");
      item.className = "marquee-item";
      item.textContent = name;
      track.appendChild(item);

      const sep = document.createElement("span");
      sep.className = "marquee-sep";
      sep.textContent = "·";
      track.appendChild(sep);
    });
  }

  animate(track, { x: ["0%", "-33.33%"] }, { duration: 45, repeat: Infinity, easing: "linear" });

  // ═══════════════════════════════════
  // 5. Stats — count-up animation
  // ═══════════════════════════════════
  inView(".stats-section", () => {
    animate("[data-stat]", { opacity: [0, 1], y: [20, 0] }, {
      delay: stagger(0.12),
      duration: 0.7,
      easing: spring({ stiffness: 100, damping: 14 })
    });

    // Count up numbers
    document.querySelectorAll("[data-count]").forEach(el => {
      const target = parseInt(el.dataset.count);
      const duration = 1500;
      const start = performance.now();

      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, { margin: "-60px" });

  // ═══════════════════════════════════
  // 6. Feature cards — staggered reveal + glow tracking
  // ═══════════════════════════════════
  inView(".features-grid", () => {
    animate("[data-feature]", { opacity: [0, 1], y: [30, 0] }, {
      delay: stagger(0.08, { startDelay: 0.1 }),
      duration: 0.7,
      easing: [0.22, 1, 0.36, 1]
    });
  }, { margin: "-80px" });

  document.querySelectorAll(".f-card").forEach(card => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mouse-x", ((e.clientX - rect.left) / rect.width * 100) + "%");
      card.style.setProperty("--mouse-y", ((e.clientY - rect.top) / rect.height * 100) + "%");
    });
  });

  // ═══════════════════════════════════
  // 7. Architecture diagram
  // ═══════════════════════════════════
  inView(".arch-section", () => {
    animate("[data-node]", { opacity: [0, 1], scale: [0.9, 1] }, {
      delay: stagger(0.1),
      duration: 0.6,
      easing: spring({ stiffness: 120, damping: 14 })
    });
  }, { margin: "-60px" });

  // ═══════════════════════════════════
  // 8. How-it-works steps reveal
  // ═══════════════════════════════════
  inView(".how-steps", () => {
    animate("[data-step]", { opacity: [0, 1], x: [-20, 0] }, {
      delay: stagger(0.15, { startDelay: 0.1 }),
      duration: 0.8,
      easing: [0.22, 1, 0.36, 1]
    });
  }, { margin: "-60px" });

  // ═══════════════════════════════════
  // 9. CTA entrance
  // ═══════════════════════════════════
  inView(".cta-box", () => {
    animate(".cta-box", { opacity: [0, 1], scale: [0.96, 1] }, {
      duration: 0.8,
      easing: spring({ stiffness: 100, damping: 16 })
    });
  }, { margin: "-60px" });

});

// ═══════════════════════════════════
// Copy install command
// ═══════════════════════════════════
window.copyInstall = function () {
  navigator.clipboard.writeText("pip install -e .").then(() => {
    const el = document.getElementById("cta-copy");
    el.classList.add("copied");
    el.querySelector(".copy-hint").innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      скопировано!
    `;
    setTimeout(() => {
      el.classList.remove("copied");
      el.querySelector(".copy-hint").innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
        скопировать
      `;
    }, 2500);
  });
};
