// KyroX Frontend Environment Configuration Template
// Copy this file to env.js and set your CARTO_API_KEY if required.
// env.js is excluded from Git via .gitignore and will never be committed.
window.__ENV__ = {
  // Set this to the deployed FastAPI origin, for example:
  // KYROX_API_BASE: "https://api.example.com"
  KYROX_API_BASE: "",
  CARTO_API_KEY: "",
  CARTO_BASEMAP_URL: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
};
