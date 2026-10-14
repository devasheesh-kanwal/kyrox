/**
 * ORCA app shell interactions. Loaded after orca-dashboard.js and talks to it
 * only through window.ORCA and DOM events ('orca:telemetry', 'orca:asking',
 * 'orca:answer'), like landing.js.
 *
 *   - keys 1-6 switch views, "/" jumps to Ask ORCA (ignored while typing);
 *   - anything with data-goto ("view" or "view:variable") opens that view;
 *   - the sidebar status card and the overview gauge mirror the live verdict;
 *   - 12 h trend lines (overview) and per-variable trend lines (forecast
 *     rail) come from the real /predictions/forecast endpoint;
 *   - the agent board in Ask ORCA shows each agent working on a question;
 *   - the URL hash follows the open view, so a reload keeps your place.
 */
(function () {
  'use strict';

  const VIEWS = ['dashboard', 'map', 'alerts', 'species', 'analytics', 'chat'];
  const HEADLINES = { LOW: 'Suitable to go out', MEDIUM: 'Go out with caution', HIGH: 'Return to shore', CRITICAL: 'Do not go to sea' };
  const FORECAST_VARS = ['wave_height', 'wind_speed', 'swell_wave_height', 'ocean_current_velocity', 'risk_score'];
  const DIGITS = { wave_height: 1, swell_wave_height: 1, wind_speed: 0, ocean_current_velocity: 1, risk_score: 0 };
  const reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  function orca() { return window.ORCA || {}; }

  function text(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function num(value, digits) {
    return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : null;
  }

  function rememberView(view) {
    if (!VIEWS.includes(view) || window.location.hash === `#${view}`) return;
    // replaceState does not fire hashchange, so the router is not re-run.
    try { history.replaceState(null, '', `#${view}`); } catch (e) {}
  }

  function goTo(view, then) {
    const app = orca();
    if (!app.switchActiveView || !VIEWS.includes(view)) return;
    app.switchActiveView(view);
    rememberView(view);
    const stage = document.getElementById('orcaWorkspaceStage');
    if (stage) stage.focus({ preventScroll: true });
    if (typeof then === 'function') then(app);
  }

  // ------------------------------------------------------------ keyboard
  function isTyping(target) {
    if (!target) return false;
    const tag = target.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
  }

  function initShortcuts() {
    document.addEventListener('keydown', event => {
      if (!document.body.classList.contains('mode-app')) return;
      if (event.metaKey || event.ctrlKey || event.altKey || isTyping(event.target)) return;
      if (/^[1-6]$/.test(event.key)) {
        event.preventDefault();
        goTo(VIEWS[Number(event.key) - 1]);
      } else if (event.key === '/') {
        event.preventDefault();
        goTo('chat', () => {
          const input = document.getElementById('tacticalQueryInput');
          if (input) requestAnimationFrame(() => input.focus());
        });
      }
    });
  }

  function initHashSync() {
    document.addEventListener('click', event => {
      const btn = event.target.closest('.sidebar-nav-btn, .mobile-dock-btn');
      if (btn && btn.dataset.view) rememberView(btn.dataset.view);
    });
  }

  // ------------------------------------------------------------ data-goto links (metrics, outlook rows)
  function openGoto(el) {
    const [view, variable] = String(el.dataset.goto || '').split(':');
    goTo(view, app => { if (variable && app.loadRegressionData) app.loadRegressionData(variable); });
  }

  function initGotoLinks() {
    document.addEventListener('click', event => {
      const el = event.target.closest('[data-goto]');
      if (el && document.body.classList.contains('mode-app')) openGoto(el);
    });
    // Buttons already turn Enter/Space into clicks; the metric cards are articles.
    document.addEventListener('keydown', event => {
      const el = event.target.closest && event.target.closest('[data-goto]');
      if (!el || el.tagName === 'BUTTON' || (event.key !== 'Enter' && event.key !== ' ')) return;
      event.preventDefault();
      openGoto(el);
    });
  }

  // ------------------------------------------------------------ live verdict: sidebar, gauge, chat chips
  function renderStatus(detail) {
    const data = (detail && detail.data) || {};
    const place = (detail && detail.place) || 'your position';
    const offline = data.status === 'offline';
    const noSea = data.marine_available === false;
    const level = offline || noSea ? '' : (data.risk_level || '');

    const card = document.getElementById('sbStatus');
    if (card) card.dataset.level = offline ? 'OFFLINE' : level;
    text('sbStatusLevel', offline ? 'Offline' : noSea ? 'Not at sea' : level ? `${level.charAt(0)}${level.slice(1).toLowerCase()} risk` : 'Checking');
    text('sbStatusHeadline', offline ? 'Live data unavailable' : noSea ? 'No sea data here' : (HEADLINES[level] || 'Reading the sea'));
    text('sbStatusPlace', place);

    // 270 degree gauge: the arc covers 75 of the circle's 100 path units.
    const gauge = document.getElementById('gaugeValue');
    if (gauge) {
      const score = offline || noSea ? 0 : Math.max(0, Math.min(100, Number(data.risk_score) || 0));
      gauge.style.strokeDasharray = `${(score * 0.75).toFixed(2)} 100`;
    }

    const chips = document.getElementById('chatConditions');
    if (chips) {
      if (offline) {
        chips.innerHTML = '<span class="cc-chip is-off"><i class="ph ph-wifi-slash icon" aria-hidden="true"></i>Live data offline</span>';
      } else {
        const wave = num(data.wave_height, 1);
        const wind = num(data.wind_speed, 0);
        const alerts = Array.isArray(data.official_alerts) ? data.official_alerts.length : null;
        const parts = [];
        if (level) parts.push(`<span class="cc-chip cc-level" data-level="${escapeHtml(level)}"><span class="cc-dot" aria-hidden="true"></span>${escapeHtml(HEADLINES[level] || level)}</span>`);
        if (wave) parts.push(`<span class="cc-chip"><i class="ph ph-waves icon" aria-hidden="true"></i>Waves <strong>${wave} m</strong></span>`);
        if (wind) parts.push(`<span class="cc-chip"><i class="ph ph-wind icon" aria-hidden="true"></i>Wind <strong>${wind} kt</strong></span>`);
        if (alerts !== null) parts.push(`<span class="cc-chip"><i class="ph ph-siren icon" aria-hidden="true"></i>Warnings <strong>${alerts}</strong></span>`);
        chips.innerHTML = parts.join('');
      }
    }

    maybeRefreshForecasts();
  }

  function initStatusCard() {
    const card = document.getElementById('sbStatus');
    if (card) card.addEventListener('click', () => goTo('dashboard'));
  }

  // ------------------------------------------------------------ forecast trend lines
  let forecastKey = '';
  let forecastStamp = 0;

  function apiBase() {
    return orca().apiBase || '';
  }

  function maybeRefreshForecasts() {
    const loc = orca().getLocation && orca().getLocation();
    if (!loc || !Number.isFinite(Number(loc.latitude))) return;
    const key = `${Number(loc.latitude).toFixed(3)},${Number(loc.longitude).toFixed(3)}`;
    // Same place: refresh at most every 10 minutes (the backend caches upstream data).
    if (key === forecastKey && Date.now() - forecastStamp < 600000) return;
    forecastKey = key;
    forecastStamp = Date.now();
    FORECAST_VARS.forEach(variable => loadTrend(variable, loc, key));
  }

  async function loadTrend(variable, loc, key) {
    const params = new URLSearchParams({ variable, lat: loc.latitude, lon: loc.longitude, horizon_hours: 24, past_hours: 6 });
    let body = null;
    try {
      const res = await fetch(`${apiBase()}/predictions/forecast?${params}`);
      body = res.ok ? await res.json() : null;
    } catch (e) { body = null; }
    if (key !== forecastKey) return; // location changed while loading
    if (!body || body.success === false) {
      markTrendUnavailable(variable);
      return;
    }
    drawTrend(variable, body);
  }

  function statusColor(value, thresholds) {
    const t = thresholds || {};
    if (Number.isFinite(t.danger_min) && value >= t.danger_min) return 'var(--bad)';
    if (Number.isFinite(t.safe_max) && value > t.safe_max) return 'var(--warn)';
    return 'var(--ok)';
  }

  function sparkPath(values, width, height, pad) {
    const lo = Math.min(...values);
    const hi = Math.max(...values);
    const span = hi - lo || 1;
    const step = values.length > 1 ? width / (values.length - 1) : width;
    const points = values.map((v, i) => [i * step, pad + (height - 2 * pad) * (1 - (v - lo) / span)]);
    const line = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
    const area = `${line} L${width} ${height} L0 ${height} Z`;
    return { line, area, last: points[points.length - 1] };
  }

  function renderSpark(svg, values, color, width, height) {
    if (!svg) return;
    if (values.length < 2) { svg.innerHTML = ''; return; }
    const { line, area, last } = sparkPath(values, width, height, 4);
    const id = `g${Math.random().toString(36).slice(2, 8)}`;
    svg.innerHTML = `
      <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity="0.28"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
      <path d="${area}" fill="url(#${id})" stroke="none"/>
      <path class="spark-line" d="${line}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" pathLength="100"/>
      <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3" fill="${color}"/>`;
    // Draw the line in on update (it carries new data); static under reduced motion.
    svg.classList.remove('is-drawn');
    if (reduceMotion.matches) svg.classList.add('is-drawn');
    else requestAnimationFrame(() => requestAnimationFrame(() => svg.classList.add('is-drawn')));
  }

  function drawTrend(variable, body) {
    const unit = body.unit || '';
    const digits = DIGITS[variable] ?? 1;
    const preds = (body.predictions || []).filter(p => Number.isFinite(Number(p.predicted_value)));
    const now = Number(body.current_value);
    // The risk index is unitless (0-100); everything else keeps its unit.
    const fmt = v => `${Number(v).toFixed(digits)}${unit && !['score', 'idx'].includes(unit) ? ` ${unit}` : ''}`;

    // Overview: next 12 hours only.
    const next12 = preds.filter(p => Number(p.hour_offset) <= 12).map(p => Number(p.predicted_value));
    if (document.getElementById(`olSpark-${variable}`) && next12.length) {
      const series = Number.isFinite(now) ? [now, ...next12] : next12;
      const peak = Math.max(...series);
      const low = Math.min(...series);
      const color = statusColor(peak, body.thresholds);
      // Show the 12 h peak: the live "now" value lives in the instrument column
      // (consensus of models), and two different "now" figures would conflict.
      text(`olNow-${variable}`, `peak ${fmt(peak)}`);
      renderSpark(document.getElementById(`olSpark-${variable}`), series, color, 200, 44);
      const peakAt = preds.find(p => Number(p.predicted_value) === peak);
      text(`olRange-${variable}`, fmt(low) === fmt(peak)
        ? `Steady near ${fmt(peak)}`
        : `${fmt(low)} to ${fmt(peak)}${peakAt ? `, highest in ${peakAt.hour_offset} h` : ', highest now'}`);
    }

    // Forecast rail: past 6 h + next 24 h.
    const history = (body.history || []).map(h => Number(h.value)).filter(Number.isFinite);
    const full = history.concat(preds.map(p => Number(p.predicted_value)));
    const railSvg = document.getElementById(`gvSpark-${variable}`);
    if (railSvg && full.length) {
      renderSpark(railSvg, full, statusColor(Math.max(...full), body.thresholds), 200, 40);
      text(`gvNow-${variable}`, Number.isFinite(now) ? fmt(now) : '--');
    }
  }

  function markTrendUnavailable(variable) {
    text(`olRange-${variable}`, 'Forecast unavailable');
    text(`olNow-${variable}`, '--');
    text(`gvNow-${variable}`, 'n/a');
    ['olSpark-', 'gvSpark-'].forEach(prefix => { const svg = document.getElementById(prefix + variable); if (svg) svg.innerHTML = ''; });
  }

  // ------------------------------------------------------------ agent board (Ask ORCA)
  let askedAt = 0;
  let boardTimer = 0;

  function boardRows() {
    return Array.from(document.querySelectorAll('#agentBoard li[data-agent]'));
  }

  function setRow(row, state, label) {
    row.dataset.state = state;
    const el = row.querySelector('.ab-state');
    if (el) el.textContent = label;
  }

  function onAsking() {
    askedAt = performance.now();
    window.clearInterval(boardTimer);
    const rows = boardRows();
    rows.forEach(row => setRow(row, 'queued', 'Queued'));
    text('agentBoardNote', 'Agents are reading the latest data for your position.');
    // The backend runs them together; light them up in order so the work is visible.
    let i = 0;
    boardTimer = window.setInterval(() => {
      if (i < rows.length) setRow(rows[i], 'running', 'Working');
      i += 1;
      if (i >= rows.length) window.clearInterval(boardTimer);
    }, reduceMotion.matches ? 0 : 160);
  }

  function onAnswer(detail) {
    window.clearInterval(boardTimer);
    const data = detail && detail.data;
    const rows = boardRows();
    const elapsed = askedAt ? (performance.now() - askedAt) / 1000 : null;
    const seconds = elapsed === null ? null : elapsed < 0.1 ? 'under 0.1' : elapsed.toFixed(1);
    if (!data) {
      rows.forEach(row => setRow(row, 'failed', 'Unreachable'));
      text('agentBoardNote', 'ORCA could not reach its agents, so no advice was given.');
      return;
    }
    const trace = new Map((data.agent_trace || []).map(a => [a.agent, a]));
    // Reveal each agent's real result in turn (the answer itself is not delayed).
    rows.forEach((row, i) => {
      const t = trace.get(row.dataset.agent);
      const apply = () => {
        if (!t) setRow(row, 'skipped', 'Not needed');
        else if (t.status === 'ok') setRow(row, 'done', Number(t.ms) >= 1 ? `${Math.round(t.ms)} ms` : 'Done');
        else setRow(row, 'failed', 'Failed');
      };
      if (reduceMotion.matches) apply();
      else window.setTimeout(apply, i * 60);
    });
    const ok = (data.agent_trace || []).filter(a => a.status === 'ok').length;
    const total = (data.agent_trace || []).length;
    const risk = data.risk || {};
    text('agentBoardNote', total
      ? `${ok} of ${total} agents answered${seconds ? ` in ${seconds} s` : ''}. Confidence: ${risk.confidence || 'unknown'}.`
      : 'Answered without the agent pipeline.');
  }

  // ------------------------------------------------------------ boot
  document.addEventListener('orca:telemetry', event => renderStatus(event.detail));
  document.addEventListener('orca:asking', onAsking);
  document.addEventListener('orca:answer', event => onAnswer(event.detail));
  document.addEventListener('DOMContentLoaded', () => {
    initShortcuts();
    initHashSync();
    initGotoLinks();
    initStatusCard();
    if (window.lastBridgeTelemetry) renderStatus({ data: window.lastBridgeTelemetry });
  });
})();
