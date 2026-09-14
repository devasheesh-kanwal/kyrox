export default async function run(page, ui) {
  // Intercept the backend heatmap call and serve a realistic 3x3 grid so we can
  // exercise renderDynamicRiskHeatmap without the Python backend running.
  await page.route('**/heatmap*', async (route) => {
    const lat = 15.246, lon = 73.803, step = 0.05;
    const pts = [];
    const risks = [12, 22, 18, 30, 96, 42, 20, 35, 25];
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
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ has_data: true, user_location: { latitude: lat, longitude: lon }, risk_points: pts })
    });
  });

  await page.waitForSelector('.leaflet-tile', { timeout: 15000 }).catch(() => {});

  const before = await page.evaluate(() => ({
    leaflet: typeof window.L,
    heatLayerFn: typeof (window.L && window.L.heatLayer),
    canvases: document.querySelectorAll('.leaflet-container canvas').length
  }));

  // Trigger a location update through the app's real public API.
  await page.evaluate(() => window.ORCA.updateLocation(15.246, 73.803, 'QA', 'manual'));
  await page.waitForTimeout(3500);

  const after = await page.evaluate(() => ({
    canvases: document.querySelectorAll('.leaflet-container canvas').length,
    heatCanvases: document.querySelectorAll('.leaflet-container .leaflet-heatmap-layer').length,
    toggleLabel: document.getElementById('txtHeatmapToggle')?.textContent,
    anyCanvasWithContent: Array.from(document.querySelectorAll('.leaflet-container canvas'))
      .some(c => c.width > 0 && c.height > 0)
  }));

  return { before, after };
}
