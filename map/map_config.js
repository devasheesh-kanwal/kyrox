/**
 * KyroX Marine Safety AI - Basemap Configuration
 *
 * CARTO Voyager tiles require a paid/API key and otherwise render
 * "API key required" on the map. Default to OpenStreetMap (no key).
 * Use CARTO only when CARTO_API_KEY is explicitly provided.
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

  var OSM_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  var OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';
  var CARTO_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png';
  var CARTO_ATTR = '&copy; <a href="https://carto.com/" target="_blank" rel="noopener">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';

  function resolveEnv() {
    var env = {};
    if (typeof window !== 'undefined') {
      if (window.__ENV__) Object.assign(env, window.__ENV__);
      if (window.CARTO_CONFIG) Object.assign(env, window.CARTO_CONFIG);
      if (window.ENV) Object.assign(env, window.ENV);
      if (window.CARTO_API_KEY) env.CARTO_API_KEY = window.CARTO_API_KEY;
      if (window.CARTO_BASEMAP_URL) env.CARTO_BASEMAP_URL = window.CARTO_BASEMAP_URL;
    }
    return env;
  }

  var env = resolveEnv();
  var API_KEY = (env.CARTO_API_KEY || '').trim();
  var customUrl = (env.CARTO_BASEMAP_URL || '').trim();
  var useCarto = Boolean(API_KEY);

  function getTileUrl() {
    if (useCarto) {
      var url = customUrl || CARTO_URL;
      var sep = url.indexOf('?') !== -1 ? '&' : '?';
      return url + sep + 'key=' + encodeURIComponent(API_KEY);
    }
    if (customUrl && customUrl.indexOf('cartocdn.com') === -1) {
      return customUrl;
    }
    return OSM_URL;
  }

  return {
    OSM_URL: OSM_URL,
    BASEMAP_URL: getTileUrl(),
    hasApiKey: function () {
      return useCarto;
    },
    getTileUrl: getTileUrl,
    attribution: useCarto ? CARTO_ATTR : OSM_ATTR,
    subdomains: useCarto ? 'abcd' : 'abc',
    maxZoom: 19
  };
}));
