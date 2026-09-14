export default async function run(page, ui) {
  // Wait for tiles (proof Leaflet booted), then probe the plugin directly.
  await page.waitForSelector('.leaflet-tile', { timeout: 15000 }).catch(() => {});

  const probe = async () => page.evaluate(() => ({
    leaflet: typeof window.L,
    heatLayer: typeof (window.L && window.L.heatLayer),
    canvases: document.querySelectorAll('.leaflet-container canvas').length,
    tileCount: document.querySelectorAll('.leaflet-tile').length
  }));

  const first = await probe();
  // Give the CDN plugin a beat if it hasn't attached yet.
  if (first.heatLayer !== 'function') {
    await page.waitForTimeout(3000);
  }
  const second = await probe();

  // Force the heatmap toggle to exercise the real code path if available.
  const toggled = await page.evaluate(() => {
    const btn = document.getElementById('btnToggleHeatmap');
    return { hasToggle: !!btn, label: document.getElementById('txtHeatmapToggle')?.textContent };
  });

  return { first, second, toggled };
}
