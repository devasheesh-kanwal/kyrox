/**
 * KyroX Marine Safety AI - CARTO Basemaps Configuration Utility
 *
 * Configures CARTO Voyager raster basemap for Leaflet.
 * Supports secure client environment variables:
 * - window.__ENV__.CARTO_API_KEY / window.CARTO_API_KEY
 * - window.__ENV__.CARTO_BASEMAP_URL / window.CARTO_BASEMAP_URL
 * - import.meta.env (Vite)
 * - process.env (Webpack / Create React App)
 *
 * Security:
 * - Never hardcodes API keys in source code.
 * - Only appends `?key=CARTO_API_KEY` when a key is provided in the environment.
 */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CartoMapConfig = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Securely resolve client environment variables without leaking secrets
  function resolveEnv() {
    var env = {};
    if (typeof window !== 'undefined') {
      if (window.__ENV__) Object.assign(env, window.__ENV__);
      if (window.CARTO_CONFIG) Object.assign(env, window.CARTO_CONFIG);
      if (window.ENV) Object.assign(env, window.ENV);
      if (window.CARTO_API_KEY) env.CARTO_API_KEY = window.CARTO_API_KEY;
      if (window.CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = window.CARTO_BASEMAP_URL;
    }
    try {
      if (typeof import.meta !== 'undefined' && import.meta.env) {
        if (import.meta.env.VITE_CARTO_API_KEY) env.CARTO_API_KEY = import.meta.env.VITE_CARTO_API_KEY;
        if (import.meta.env.VITE_CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = import.meta.env.VITE_CARTO_BASEMAP_URL;
        if (import.meta.env.CARTO_API_KEY) env.CARTO_API_KEY = import.meta.env.CARTO_API_KEY;
        if (import.meta.env.CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = import.meta.env.CARTO_BASEMAP_URL;
      }
    } catch (e) {}
    try {
      if (typeof process !== 'undefined' && process.env) {
        if (process.env.REACT_APP_CARTO_API_KEY) env.CARTO_API_KEY = process.env.REACT_APP_CARTO_API_KEY;
        if (process.env.REACT_APP_CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = process.env.REACT_APP_CARTO_BASEMAP_URL;
        if (process.env.CARTO_API_KEY) env.CARTO_API_KEY = process.env.CARTO_API_KEY;
        if (process.env.CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = process.env.CARTO_BASEMAP_URL;
      }
    } catch (e) {}
    return env;
  }

  var env = resolveEnv();

  // Standard CARTO Voyager basemap raster endpoint
  var BASEMAP_URL = env.CARTO_BASEMAP_URL || 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png';
  var API_KEY = env.CARTO_API_KEY || '';

  function getTileUrl() {
    var url = BASEMAP_URL;
    if (API_KEY && typeof API_KEY === 'string' && API_KEY.trim().length > 0) {
      var sep = url.indexOf('?') !== -1 ? '&' : '?';
      return url + sep + 'key=' + encodeURIComponent(API_KEY.trim());
    }
    return url;
  }

  return {
    BASEMAP_URL: BASEMAP_URL,
    hasApiKey: function () {
      return Boolean(API_KEY && API_KEY.trim().length > 0);
    },
    getTileUrl: getTileUrl,
    attribution: '&copy; <a href="https://carto.com/" target="_blank" rel="noopener">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    subdomains: 'abcd',
    maxZoom: 19
  };
}));
