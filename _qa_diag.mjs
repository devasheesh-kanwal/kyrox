export default async function run(page, ui) {
  const net = [];
  page.on('response', r => { if (r.url().includes('.js')) net.push(`${r.status()} ${r.url()}`); });

  await page.waitForTimeout(3000);

  const info = await page.evaluate(() => ({
    orca: typeof window.ORCA,
    L: typeof window.L,
    heat: typeof (window.L && window.L.heatLayer),
    speciesCatalog: typeof window.ORCA_SPECIES_CATALOG,
    scripts: Array.from(document.scripts).map(s => ({ src: s.src, loaded: !!s.src })),
    canvases: document.querySelectorAll('canvas').length,
    tileImgs: document.querySelectorAll('img.leaflet-tile').length
  }));
  return { info, net };
}
