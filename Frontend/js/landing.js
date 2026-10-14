/**
 * ORCA landing page: routing between the landing page and the app views,
 * theme preference, live data on the landing page, and its motion layer.
 * Loaded before orca-dashboard.js; talks to it only through window.ORCA and
 * the 'orca:telemetry' event.
 *
 * Motion is tied to meaning:
 *   - swell lines in the hero move with the LIVE wave height and period;
 *   - stats count up when new live values arrive;
 *   - the decision flow lights up source by source, then shows the advice.
 * Everything collapses to a static frame under prefers-reduced-motion.
 */
(function () {
  'use strict';

  const APP_VIEWS = ['dashboard', 'map', 'alerts', 'species', 'analytics', 'chat'];
  const reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  // ------------------------------------------------------------ theme
  function applyInitialTheme() {
    let saved = null;
    try { saved = localStorage.getItem('orca_theme'); } catch (e) {}
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    const light = saved ? saved === 'light' : prefersLight;
    document.body.classList.toggle('deck-sunlight', light);
  }

  function toggleTheme() {
    const sunlight = document.getElementById('btnSunlightToggle');
    if (sunlight) { sunlight.click(); return; }
    const light = document.body.classList.toggle('deck-sunlight');
    try { localStorage.setItem('orca_theme', light ? 'light' : 'dark'); } catch (e) {}
  }

  // ------------------------------------------------------------ routing
  function currentView() {
    return (window.location.hash || '').replace('#', '');
  }

  // ------------------------------------------------------------ page transition
  // Entering the app, the new page opens as a circle from the control you
  // pressed while the old one sinks away; going Home reverses it. Uses the View
  // Transitions API where available, otherwise the switch is instant.
  let booted = false;
  let lastPress = null;
  document.addEventListener('pointerdown', event => {
    lastPress = { x: event.clientX, y: event.clientY, at: Date.now() };
  }, true);

  function canTransition() {
    return typeof document.startViewTransition === 'function' && !reduceMotion.matches && !document.hidden;
  }

  function setRevealOrigin() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    let x = w / 2;
    let y = h / 2;
    if (lastPress && Date.now() - lastPress.at < 1500) {
      x = lastPress.x;
      y = lastPress.y;
    } else if (document.activeElement && document.activeElement !== document.body) {
      // Keyboard activation: grow from the focused control.
      const r = document.activeElement.getBoundingClientRect();
      if (r.width) { x = r.left + r.width / 2; y = r.top + r.height / 2; }
    }
    const radius = Math.hypot(Math.max(x, w - x), Math.max(y, h - y));
    const root = document.documentElement.style;
    root.setProperty('--vt-x', `${Math.round(x)}px`);
    root.setProperty('--vt-y', `${Math.round(y)}px`);
    root.setProperty('--vt-r', `${Math.ceil(radius)}px`);
  }

  function route() {
    const view = currentView();
    const inApp = APP_VIEWS.includes(view);
    const wasApp = document.body.classList.contains('mode-app');
    const animate = booted && inApp !== wasApp && canTransition();

    const apply = () => {
      document.body.classList.toggle('mode-app', inApp);
      document.body.classList.toggle('mode-landing', !inApp);
      if (inApp && !wasApp && window.ORCA && window.ORCA.switchActiveView) {
        // Inside a transition the view must be in place before the new frame
        // is captured; otherwise wait a frame so Leaflet and Plotly can measure.
        if (animate) window.ORCA.switchActiveView(view, { instant: true });
        else requestAnimationFrame(() => window.ORCA.switchActiveView(view, { instant: true }));
      }
      if (!inApp && (view === '' || view === 'home')) window.scrollTo({ top: 0 });
      if (swell) (inApp ? swell.stop() : swell.start());
    };

    booted = true;
    if (!animate) { apply(); return; }
    const root = document.documentElement;
    setRevealOrigin();
    root.dataset.vt = inApp ? 'enter-app' : 'leave-app';
    const transition = document.startViewTransition(apply);
    transition.finished.finally(() => { delete root.dataset.vt; });
  }

  // ------------------------------------------------------------ helpers
  function text(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function escapeHtml(value) {
    return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Count a number up/down to its new value; signals "this just updated".
  function countTo(id, value, decimals, suffix) {
    const el = document.getElementById(id);
    if (!el) return;
    if (typeof value !== 'number' || !Number.isFinite(value)) { el.textContent = '-'; return; }
    const from = Number(el.dataset.value);
    el.dataset.value = String(value);
    const render = v => { el.textContent = `${v.toFixed(decimals)}${suffix}`; };
    if (reduceMotion.matches || !Number.isFinite(from) || from === value) { render(value); return; }
    el.classList.add('is-updating');
    const start = performance.now();
    const duration = 900;
    const step = now => {
      const k = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      render(from + (value - from) * eased);
      if (k < 1) requestAnimationFrame(step);
      else el.classList.remove('is-updating');
    };
    requestAnimationFrame(step);
  }

  // ------------------------------------------------------------ live swell canvas
  function createSwell(canvas) {
    if (!canvas || !canvas.getContext) return null;
    const ctx = canvas.getContext('2d');
    let width = 0, height = 0;
    let waveHeight = 0.8, period = 10, level = '';
    let stroke = '#E0559A';
    let raf = 0, running = false, onScreen = true;
    const born = performance.now();

    function readColor() {
      const name = level === 'HIGH' || level === 'CRITICAL' ? '--bad' : level === 'MEDIUM' ? '--warn' : '--accent';
      stroke = getComputedStyle(document.body).getPropertyValue(name).trim() || stroke;
    }

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw(performance.now());
    }

    function draw(now) {
      const t = (now - born) / 1000;
      ctx.clearRect(0, 0, width, height);
      // Amplitude follows the real significant wave height; spacing and speed follow the period.
      const amp = Math.min(44, 4 + waveHeight * 12);
      const wavelength = 150 + Math.max(4, period) * 22;
      const speed = wavelength / Math.max(4, period);
      const lines = 9;
      ctx.strokeStyle = stroke;
      for (let i = 0; i < lines; i++) {
        const depth = i / (lines - 1);
        const y0 = height * (0.16 + depth * 0.8);
        const a = amp * (0.3 + depth * 0.7);
        const L = wavelength * (0.55 + depth * 0.65);
        const drift = t * speed * (0.5 + depth * 0.7);
        ctx.globalAlpha = 0.08 + depth * 0.3;
        ctx.lineWidth = 0.8 + depth * 1.2;
        ctx.beginPath();
        for (let x = -8; x <= width + 8; x += 8) {
          const phase = ((x - drift) / L) * Math.PI * 2 + i * 0.9;
          const y = y0 + Math.sin(phase) * a + Math.sin(phase * 0.47 + i * 1.7) * a * 0.32;
          if (x === -8) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    function loop(now) {
      draw(now);
      raf = requestAnimationFrame(loop);
    }

    function start() {
      if (running || reduceMotion.matches || !onScreen || document.hidden || !document.body.classList.contains('mode-landing')) return;
      running = true;
      raf = requestAnimationFrame(loop);
    }

    function stop() {
      running = false;
      cancelAnimationFrame(raf);
    }

    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(canvas);
    window.addEventListener('resize', resize);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => {
        onScreen = entry.isIntersecting;
        onScreen ? start() : stop();
      }).observe(canvas);
    }
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    new MutationObserver(() => { readColor(); if (!running) draw(performance.now()); })
      .observe(document.body, { attributes: true, attributeFilter: ['class'] });

    readColor();
    resize();

    return {
      start,
      stop,
      update(h, p, lv) {
        if (typeof h === 'number' && Number.isFinite(h)) waveHeight = h;
        if (typeof p === 'number' && Number.isFinite(p)) period = p;
        level = lv || '';
        readColor();
        if (!running) draw(performance.now());
      }
    };
  }

  let swell = null;

  // ------------------------------------------------------------ live data on the landing page
  const HEADLINES = { LOW: 'Suitable to go out', MEDIUM: 'Go out with caution', HIGH: 'Return to shore', CRITICAL: 'Do not go to sea' };

  function renderLive(detail) {
    const data = (detail && detail.data) || {};
    const place = (detail && detail.place) || 'your position';
    const offline = data.status === 'offline';
    const noSea = data.marine_available === false;
    const level = offline || noSea ? '' : (data.risk_level || '');
    const headline = offline ? 'Live data unavailable' : noSea ? 'No sea data here' : (HEADLINES[level] || 'Checking conditions');

    const card = document.getElementById('lpLiveCard');
    if (card) card.dataset.level = level;
    text('lpLivePlace', place);
    text('lpLiveTagText', offline ? 'Offline' : (level ? `${level.charAt(0)}${level.slice(1).toLowerCase()} risk` : 'Live'));
    text('lpLiveHeadline', headline);
    countTo('lpLiveWave', data.wave_height, 1, ' m');
    countTo('lpLiveWind', data.wind_speed, 0, ' kt');
    countTo('lpLiveAlerts', Array.isArray(data.official_alerts) ? data.official_alerts.length : NaN, 0, '');

    if (typeof data.wave_height === 'number') {
      const per = typeof data.wave_period === 'number' ? `, a new wave every ${Math.round(data.wave_period)} s` : '';
      text('lpSwellNote', `The lines behind this page move with the live waves here: ${data.wave_height.toFixed(1)} m${per}.`);
    }
    if (swell) swell.update(data.wave_height, data.wave_period, level);

    // Decision flow: the real verdict and its first reason.
    const advice = document.getElementById('lpFlowAdvice');
    if (advice) advice.dataset.level = level;
    text('lpFlowPlace', place);
    text('lpFlowVerdict', headline);
    const reason = Array.isArray(data.reasons) && data.reasons.length
      ? String(data.reasons[0]).replace(/^OFFICIAL /, 'Official ')
      : (offline ? 'The agents could not be reached.' : 'No hazards now or in the next 12 hours.');
    text('lpFlowReason', reason);

    // Real consensus findings for the "how it decides" cell.
    const list = document.getElementById('lpFindings');
    const findings = ((data.consensus || {}).findings || []).slice(0, 3);
    if (list && findings.length) {
      list.innerHTML = findings.map(f => {
        const msg = String(f.message || '').replace(/^(INCOIS|GDACS) /, 'Official $1 ');
        const short = msg.length > 150 ? `${msg.slice(0, 147).trim()}...` : msg;
        return `<li data-type="${escapeHtml(f.type)}">${escapeHtml(short)}</li>`;
      }).join('');
      text('lpFindingsSrc', `Live findings for ${place}`);
    }
  }

  // ------------------------------------------------------------ headline words
  function splitHeadline() {
    const h1 = document.getElementById('lpHeroTitle');
    if (!h1 || h1.dataset.split) return;
    const words = h1.textContent.trim().split(/\s+/);
    h1.setAttribute('aria-label', h1.textContent.trim());
    h1.innerHTML = words.map((w, i) => `<span class="w" aria-hidden="true"><span style="--w:${i}">${escapeHtml(w)}</span></span>`).join(' ');
    h1.dataset.split = '1';
  }

  // ------------------------------------------------------------ reveals
  function observe(selector, onVisible, options) {
    const items = document.querySelectorAll(selector);
    if (!('IntersectionObserver' in window)) { items.forEach(onVisible); return; }
    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          onVisible(entry.target);
          io.unobserve(entry.target);
        }
      });
    }, options);
    items.forEach(el => io.observe(el));
  }

  function initNavBorder() {
    const nav = document.querySelector('.lp-nav');
    const sentinel = document.getElementById('lpTop');
    if (!nav || !sentinel || !('IntersectionObserver' in window)) return;
    new IntersectionObserver(([entry]) => nav.classList.toggle('is-scrolled', !entry.isIntersecting)).observe(sentinel);
  }

  // Cursor-following highlight on the bento cells (feedback, pointer only).
  function initSpotlight() {
    document.querySelectorAll('.lp-cell').forEach(cell => {
      cell.addEventListener('pointermove', event => {
        const r = cell.getBoundingClientRect();
        cell.style.setProperty('--mx', `${event.clientX - r.left}px`);
        cell.style.setProperty('--my', `${event.clientY - r.top}px`);
      });
    });
  }

  // ------------------------------------------------------------ boot
  applyInitialTheme();
  route();
  window.addEventListener('hashchange', route);
  document.addEventListener('orca:telemetry', event => renderLive(event.detail));
  document.addEventListener('DOMContentLoaded', () => {
    splitHeadline();
    swell = createSwell(document.getElementById('lpSwell'));
    if (swell && document.body.classList.contains('mode-landing')) swell.start();
    observe('[data-reveal]', el => el.classList.add('is-visible'), { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    observe('#lpFlow', el => el.classList.add('is-live'), { threshold: 0.35 });
    initNavBorder();
    initSpotlight();
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => btn.addEventListener('click', toggleTheme));
    if (window.lastBridgeTelemetry) renderLive({ data: window.lastBridgeTelemetry });
  });
})();
