export default async function run(page, ui) {
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  await page.waitForSelector('.leaflet-tile', { timeout: 20000 }).catch(() => { });
  // Let the app fetch /heatmap and paint the gradient.
  await page.waitForTimeout(4000);

  const state = await page.evaluate(() => {
    const c = document.querySelector('.leaflet-container canvas');
    return {
      canvasCount: document.querySelectorAll('.leaflet-container canvas').length,
      toggle: document.getElementById('txtHeatmapToggle')?.textContent,
      legendVisible: document.getElementById('heatmapLegendScale')?.style.display !== 'none'
    };
  });

  // Center the map activity: switch to the map view.
  try { await page.evaluate(() => window.ORCA && window.ORCA.switchActiveView && window.ORCA.switchActiveView('map')); } catch { }
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'C:\\Users\\devas\\OneDrive\\Documents\\GitHub\\kyrox\\_qa_heat.png' });

  return { state, errors };
}
