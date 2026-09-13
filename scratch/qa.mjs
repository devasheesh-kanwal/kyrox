export default async function run(page, ui) {
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.goto("http://localhost:5500/index.html", {waitUntil:"domcontentloaded"});
  await page.waitForTimeout(2500);
  return {errors, state: await page.evaluate(() => ({orca:typeof window.ORCA, plotly:typeof window.Plotly, map:typeof window.L, plotSize:document.querySelector("#regressionPlotly")?.getBoundingClientRect().toJSON(), panel:document.querySelector("#modelEvaluationPanel")?.innerText}))};
}
