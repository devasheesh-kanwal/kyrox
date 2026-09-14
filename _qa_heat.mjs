export default async function run(page, ui) {
  // Wait for Leaflet + the heat plugin to actually be on window.
  await page.waitForFunction(
    () => typeof window.L === 'object' && typeof window.L.heatLayer === 'function',
    { timeout: 15000 }
  ).catch(() => {});

  const result = await page.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
    return {
      leafletLoaded: typeof window.L !== 'undefined' && typeof window.L.map === 'function',
      heatLayerLoaded: typeof window.L !== 'undefined' && typeof window.L.heatLayer === 'function',
      heatScriptTag: scripts.some(s => s.includes('leaflet-heat')),
      heatScriptUrls: scripts.filter(s => s.includes('heat')),
      leafletScriptUrls: scripts.filter(s => s.includes('leaflet')),
      mapElementExists: !!document.getElementById('marineMapLeaflet'),
      tileLoaded: !!document.querySelector('.leaflet-tile'),
      canvasCount: document.querySelectorAll('.leaflet-container canvas').length
    };
  });
  return result;
}
