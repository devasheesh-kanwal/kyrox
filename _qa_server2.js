const http = require('http');
const fs = require('fs');
const p = require('path');
const root = process.argv[2];
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.json': 'application/json' };

function heatBody(lat, lon) {
  const step = 0.05;
  const risks = [12, 22, 18, 30, 96, 42, 20, 35, 25];
  const pts = [];
  let i = 0;
  for (let r = -1; r <= 1; r++) {
    for (let c = -1; c <= 1; c++) {
      const risk = risks[i++];
      pts.push({
        latitude: lat + r * step,
        longitude: lon + c * step,
        risk,
        risk_level: risk >= 75 ? 'CRITICAL' : risk >= 50 ? 'HIGH' : risk >= 30 ? 'MEDIUM' : 'LOW',
        wave_height: 1.2, wind_speed: 9, swell_height: 0.8,
        zone_type: risk >= 75 ? 'danger' : risk >= 30 ? 'caution' : 'pfz',
        zone_label: 'QA Zone', restricted: false
      });
    }
  }
  return JSON.stringify({ has_data: true, user_location: { latitude: lat, longitude: lon }, risk_points: pts });
}

http.createServer((req, res) => {
  let u = decodeURIComponent(req.url.split('?')[0]);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  // Mock backend on the same server so the app's own fetch succeeds.
  if (u === '/heatmap' || u === '/api/v1/risk-analysis') {
    let body = '';
    req.on('data', d => body += d);
    req.on('end', () => {
      let lat = 15.246, lon = 73.803;
      try { const j = JSON.parse(body || '{}'); if (j.latitude) lat = j.latitude; if (j.longitude) lon = j.longitude; } catch {}
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(heatBody(lat, lon));
    });
    return;
  }
  if (u === '/telemetry') { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); return; }
  if (u === '/bulletins') { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('[]'); return; }
  if (u.startsWith('/predictions')) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); return; }

  // Serve an env.js that points the dashboard at this same origin, so the
  // mocked /heatmap endpoint is used.
  if (u === '/env.js' || u === '/../../env.js') {
    res.writeHead(200, { 'Content-Type': 'text/javascript' });
    res.end('window.__ENV__ = { KYROX_API_BASE: "http://localhost:5500" };');
    return;
  }

  if (u === '/') u = '/index.html';
  const f = p.join(root, u);
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); res.end('nf'); return; }
    res.writeHead(200, { 'Content-Type': types[p.extname(f).toLowerCase()] || 'application/octet-stream' });
    res.end(d);
  });
}).listen(5500, () => console.log('serving on 5500 with mock /heatmap'));
