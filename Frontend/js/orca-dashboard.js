/**
 * ORCA Marine Intelligence & Conservation Dashboard
 * Core Engine & Interactive Controller
 */

(function () {
  'use strict';

  // State management
  // Restore the last selected language.
  let currentLang = localStorage.getItem('orca_marine_lang') || 'en';
  // Incremented on every language change so in-flight replies for the previous
  // language can be discarded instead of overwriting a newer answer.
  let languageEpoch = 0;
  let currentAlertFilter = 'all';
  let activeZoneId = null;
  let currentDeviceMode = localStorage.getItem('orca_marine_device_mode') || 'pc';
  let currentActiveView = 'dashboard';

  // Leaflet Map & Layer Groups
  let leafletMap = null;
  let tileLayer = null;
  let tacticalZonesLayer = null;
  let waypointsLayer = null;
  let riskHeatmapLayer = null;
  let heatLayer = null;
  let routeLayer = null;
  let userLocationMarker = null;

  let MAP_ZONES = [];
  let MAP_MARKERS = [];
  let BULLETINS = [];
  // Demo default until the user enables GPS or picks a location.
  let vesselLocation = { latitude: 15.246, longitude: 73.803, name: 'Goa (default - set your location)' };
  let locationSource = 'manual';
  let isGpsTrackingEnabled = false;
  let gpsWatchId = null;
  let telemetryTimer = null;
  let customLocationName = vesselLocation.name;
  let lastEcosystem = null;
  let isBackendConnected = false;

  // Layer Visibility States
  let isHeatmapActive = localStorage.getItem('orca_marine_heatmap') !== 'false';
  let isZonesLayerActive = true;

  // Trilingual Maritime Translations
  const I18N = {
    en: {
      heroTagline: "Collaborative AI agents for safer seas",
      heroExploreCta: "Explore Ocean Data",
      heroMapCta: "View Live Map",
      bridgeSubtitle: "Marine safety & ecosystem intelligence",
      navDashboard: "Overview",
      navMap: "Live map",
      navAlerts: "Warnings",
      navSpecies: "Protected species",
      navAnalytics: "Forecast",
      navChat: "Ask ORCA",
      kpiHealth: "Safety Risk",
      kpiSpecies: "Threatened Species",
      kpiAlerts: "Official Warnings",
      kpiPollution: "Wind",
      kpiTemp: "Water Temperature",
      kpiZones: "Waves",
      sunlight: "Sunlight",
      sunlightActive: "Sunlight",
      legendTitle: "Legend",
      legPfz: "Calm sea (safety only, not a PFZ forecast)",
      legCaution: "Caution",
      legDanger: "Hazard",
      legVessel: "Your position",
      legHeatmap: "Ocean Risk & SST Heatmap",
      heatScaleLow: "Low risk",
      heatScaleHigh: "Critical",
      heatmapBtnOn: "Risk layer: on",
      heatmapBtnOff: "Risk layer: off",
      registryTitle: "Warnings & live assessment",
      registrySector: "",
      statusSummary: (d, c) => `Active Advisories: ${d} Critical, ${c} Precautionary`,
      filtAll: "All",
      filtDanger: "Danger",
      filtCaution: "Caution",
      filtResolved: "Normal",
      plotOnChart: "Show on map",
      askInRadio: "Ask ORCA",
      briefTitle: "ORCA Multi-Agent Assistant",
      briefBody: "Weather, sea state, official warnings, protected areas and species agents answer together. A consensus agent cross-checks them, and every answer shows its reasoning.",
      inputPlaceholder: "Ask ORCA (e.g. Is it safe to fish near Kochi today?)",
      submitBtn: "Send",
      drawerAsk: "Ask ORCA",
      drawerDismiss: "Close",
      mobChart: "Overview",
      mobMap: "Map",
      mobAlerts: "Warnings",
      mobChat: "Ask",
      mobGraph: "Forecast",
      mobSpecies: "Species",
      viewPC: "PC",
      viewPhone: "PHONE",
      chatPilotQuery: "You",
      chatProcessing: "Working",
      chatAnalyzing: "Agents are gathering forecasts, official warnings and protected-area data...",
      chatLive: "Live",
      chatNominal: "Normal",
      chatDispatch: "ORCA",
      chatSpeak: "Speak this response",
      bulletinBadgeDanger: "Danger",
      bulletinBadgeCaution: "Caution",
      bulletinBadgeResolved: "Normal",
      bulletinActionLabel: "Action:",
      queries: [
        { label: "Safe to fish here today?", hint: "Verdict with reasons", icon: "boat", query: "Is it safe to go fishing here today?", zone_id: null },
        { label: "Next 12 hours", hint: "Will wind or waves get worse", icon: "clock-countdown", query: "Will the wind or waves get worse in the next 12 hours?", zone_id: null },
        { label: "Official warnings", hint: "INCOIS and cyclone alerts", icon: "siren", query: "Are there any official INCOIS or cyclone warnings near me?", zone_id: null },
        { label: "Protected species here", hint: "Avoid bycatch", icon: "fish", query: "Which threatened species are recorded here and how do I avoid bycatch?", zone_id: null },
        { label: "Explain the risk map", hint: "What the colours mean", icon: "map-trifold", query: "Explain the risk heatmap around my location", zone_id: null },
        { label: "Emergency / VHF 16", hint: "Who to call in distress", icon: "lifebuoy", query: "Emergency distress contacts VHF Ch 16", zone_id: null }
      ]
    },
    hi: {
      heroTagline: "स्वस्थ महासागर के लिए कृत्रिम बुद्धिमत्ता",
      heroExploreCta: "समुद्री डेटा देखें",
      heroMapCta: "लाइव मैप खोलें",
      bridgeSubtitle: "व्यावसायिक महासागरीय बुद्धिमत्ता एवं संरक्षण केंद्र",
      navDashboard: "अवलोकन",
      navMap: "लाइव मानचित्र",
      navAlerts: "चेतावनियाँ",
      navSpecies: "संरक्षित प्रजातियाँ",
      navAnalytics: "पूर्वानुमान",
      navChat: "ORCA से पूछें",
      kpiHealth: "महासागर स्वास्थ्य",
      kpiSpecies: "पहचानी गई प्रजातियां",
      kpiAlerts: "सक्रिय अलर्ट",
      kpiPollution: "प्रदूषण जोखिम",
      kpiTemp: "समुद्री तापमान",
      kpiZones: "निगरानी क्षेत्र",
      sunlight: "सनलाइट",
      sunlightActive: "हाई कंट्रास्ट",
      legendTitle: "नॉटिकल संकेत (Legend)",
      legCaution: "सावधानी क्षेत्र (हवा/लहर)",
      legDanger: "प्रतिबंधित खतरा (रेड अलर्ट)",
      legVessel: "नाव की स्थिति (GPS)",
      legHeatmap: "मत्स्य सघनता व SST हीटमैप",
      heatScaleLow: "कम जोखिम (सामान्य)",
      heatScaleHigh: "गंभीर जोखिम (रेड अलर्ट)",
      heatmapBtnOn: "हीटमैप: चालू",
      heatmapBtnOff: "हीटमैप: बंद",
      registryTitle: "तटीय सुरक्षा एवं संरक्षण सूचनाएं",
      statusSummary: (d, c) => `सक्रिय बुलेटिन: ${d} अति गंभीर (RED), ${c} चेतावनी (CAUTION)`,
      filtAll: "सभी सूचनाएं",
      filtDanger: "खतरा",
      filtCaution: "सावधानी",
      filtResolved: "सामान्य",
      plotOnChart: "मैप पर देखें",
      askInRadio: "ORCA से पूछें",
      briefTitle: "ORCA सामरिक महासागरीय सहायता",
      submitBtn: "पूछें",
      drawerAsk: "ORCA चैट में पूछें",
      drawerDismiss: "बंद करें",
      mobChart: "अवलोकन",
      mobMap: "मानचित्र",
      mobAlerts: "चेतावनियाँ",
      mobChat: "पूछें",
      mobGraph: "पूर्वानुमान",
      mobSpecies: "प्रजातियाँ",
      viewPC: "PC",
      viewPhone: "फोन",
      chatPilotQuery: "पायलट प्रश्न",
      chatProcessing: "प्रक्रिया जारी...",
      
      chatLive: "लाइव",
      chatNominal: "सामान्य",
      chatDispatch: "ORCA एजेंट",
      chatSpeak: "यह उत्तर सुनें",
      bulletinBadgeDanger: "खतरा",
      bulletinBadgeCaution: "सावधानी",
      bulletinBadgeResolved: "सामान्य",
      bulletinActionLabel: "कार्रवाई:",
    },
    ta: {
      heroTagline: "ஆரோக்கியமான கடலுக்கான கடல்சார் நுண்ணறிவு",
      heroExploreCta: "கடல் தகவல்களை காண்க",
      heroMapCta: "நேரலை வரைபடம்",
      bridgeSubtitle: "கடல்சார் நுண்ணறிவு மற்றும் பாதுகாப்பு மையம்",
      navDashboard: "மேலோட்டம்",
      navMap: "நேரலை வரைபடம்",
      navAlerts: "எச்சரிக்கைகள்",
      navSpecies: "பாதுகாக்கப்பட்ட உயிரினங்கள்",
      navAnalytics: "முன்னறிவிப்பு",
      navChat: "ORCA-விடம் கேளுங்கள்",
      kpiHealth: "கடல் நலம்",
      kpiSpecies: "கண்டறியப்பட்ட உயிரினம்",
      kpiAlerts: "எச்சரிக்கைகள்",
      kpiPollution: "மாசுபாடு ஆபத்து",
      kpiTemp: "கடல் வெப்பநிலை",
      kpiZones: "கண்காணிப்பு பகுதி",
      sunlight: "SUNLIGHT",
      sunlightActive: "HIGH CONTRAST",
      legendTitle: "வரைபடக் குறியீடுகள்",
      legCaution: "எச்சரிக்கை பகுதி (அலை/காற்று)",
      legDanger: "தடைசெய்யப்பட்ட ஆபத்து (ரெட் அலர்ட்)",
      legVessel: "படகு அமைவிடம் (GPS)",
      legHeatmap: "வெப்ப வரைபடம்",
      heatScaleLow: "குறைந்த ஆபத்து",
      heatScaleHigh: "அதிதீவிர ஆபத்து",
      heatmapBtnOn: "வெப்ப வரைபடம்: ஆன்",
      heatmapBtnOff: "வெப்ப வரைபடம்: ஆஃப்",
      registryTitle: "கடற்கரை பாதுகாப்பு அறிவிப்புகள்",
      statusSummary: (d, c) => `செயலில் உள்ளவை: ${d} ஆபத்து, ${c} எச்சரிக்கை`,
      filtAll: "அனைத்தும்",
      filtDanger: "ஆபத்து",
      filtCaution: "எச்சரிக்கை",
      filtResolved: "இயல்பு",
      plotOnChart: "வரைபடத்தில் காட்டு",
      askInRadio: "ORCA-விடம் கேள்",
      briefTitle: "ORCA ஆலோசனை மையம்",
      submitBtn: "கேள்",
      drawerAsk: "ORCA உரையாடலில் கேள்",
      drawerDismiss: "மூடு",
      mobChart: "மேலோட்டம்",
      mobMap: "வரைபடம்",
      mobAlerts: "எச்சரிக்கைகள்",
      mobChat: "கேளுங்கள்",
      mobGraph: "முன்னறிவிப்பு",
      mobSpecies: "உயிரினங்கள்",
      viewPC: "PC",
      viewPhone: "போன்",
      chatPilotQuery: "விமானி கேள்வி",
      chatProcessing: "செயலாக்கம்...",
      
      chatLive: "நேரலை",
      chatNominal: "இயல்பு",
      chatDispatch: "ORCA அனுப்புதல்",
      chatSpeak: "இந்த பதிலை கேள்",
      bulletinBadgeDanger: "ஆபத்து",
      bulletinBadgeCaution: "எச்சரிக்கை",
      bulletinBadgeResolved: "இயல்பு",
      bulletinActionLabel: "நடவடிக்கை:",
    }
  };

  // All 22 official Indian languages offered in the selector. Hindi and Tamil
  // also ship hand-written UI strings above; every other language uses the
  // backend translator for its interface labels.
  const LANGUAGE_OPTIONS = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
    { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
    { code: 'as', label: 'Assamese', native: 'অসমীয়া' },
    { code: 'bn', label: 'Bengali', native: 'বাংলা' },
    { code: 'brx', label: 'Bodo', native: 'बड़ो' },
    { code: 'doi', label: 'Dogri', native: 'डोगरी' },
    { code: 'gu', label: 'Gujarati', native: 'ગુજરાતી' },
    { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
    { code: 'ks', label: 'Kashmiri', native: 'کٲشُر' },
    { code: 'kok', label: 'Konkani', native: 'कोंकणी' },
    { code: 'mai', label: 'Maithili', native: 'मैथिली' },
    { code: 'ml', label: 'Malayalam', native: 'മലയാളം' },
    { code: 'mni', label: 'Manipuri', native: 'ꯃꯤꯇꯩ ꯂꯣꯟ' },
    { code: 'mr', label: 'Marathi', native: 'मराठी' },
    { code: 'ne', label: 'Nepali', native: 'नेपाली' },
    { code: 'or', label: 'Odia', native: 'ଓଡ଼ିଆ' },
    { code: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
    { code: 'sa', label: 'Sanskrit', native: 'संस्कृतम्' },
    { code: 'sat', label: 'Santali', native: 'ᱥᱟᱱᱛᱟᱲᱤ' },
    { code: 'sd', label: 'Sindhi', native: 'سنڌي' },
    { code: 'te', label: 'Telugu', native: 'తెలుగు' },
    { code: 'ur', label: 'Urdu', native: 'اردو' }
  ];
  const LANGUAGE_CODES = new Set(LANGUAGE_OPTIONS.map(option => option.code));

  // Static UI strings that only exist in English in the markup. They are
  // refreshed through the backend translator whenever a non-English language
  // is selected.
  const TRANSLATABLE_STATIC_TEXT = [
    'Dashboard', 'Live Ocean Map', 'Alerts & Bulletins', 'Protected Species',
    'Analytics Studio', 'Ask ORCA AI', 'Safety Risk', 'Waves', 'Wind',
    'Official Warnings', 'Sea Surface Temp', 'Threatened Species', 'Safe Route',
    'Consensus agent', 'OBIS records', 'Open-Meteo Marine', 'nearby', 'recorded',
    'Heatmap', 'Legend', 'Advisories', 'All Advisories', 'Critical',
    'Precaution', 'Nominal', 'Map', 'Ask AI', 'SUNLIGHT', 'HIGH CONTRAST',
    'GPS: ON', 'GPS: OFF', 'Vessel Position (GPS)', 'Calm sea',
    'Environmental Caution Area', 'Hazard / Squall Warning',
    'Ocean Risk & SST Heatmap', 'Low Risk (Nominal)', 'Critical Alert Zone',
    'Live Map', 'Alerts', 'Ask ORCA', 'Analytics', 'Species',
    'Search coastal port or coordinates', 'Locate', 'My GPS', 'Quick Ports',
    'ORCA Ocean Neural Assistant', 'Multi-Agent Link Online',
    'Weather', 'Marine', 'Official alerts', 'Protected areas', 'Ecosystem', 'Consensus',
    'Voice Command',
    'Atmospheric Pressure', 'Relative Humidity', 'Wind Speed', 'Wind Direction',
    'Visibility', 'Cloud Cover', 'Rainfall', 'Air Temperature',
    'Significant Wave Height', 'Swell Height', 'Swell Period', 'Tide State',
    'Chlorophyll-a', 'Sea Surface Salinity', 'Current Speed', 'Fishing Suitability',
  ];
  const STATIC_TEXT_TARGETS = '.kpi-title, .kpi-footer-meta span, .panel-title-text, .sidebar-nav-btn > span:not(.nav-icon):not(.nav-badge), .mobile-dock-btn > span, .map-control-btn, .loc-search-submit span, .loc-search-gps span, .loc-quick-lbl, .bulletin-badge, .brief-title span, .brief-swarm-badge span:not(.pulse-dot), .agent-tag, .bulletin-action-bar .btn-bulletin-action';

  // Coastal Ports Directory
  const MARITIME_PORTS_CATALOG = {
    "goa": { name: "Goa Coastal & Marine Sector", lat: 15.246, lon: 73.803 },
    "mumbai": { name: "Mumbai Port & Offshore Basin", lat: 18.922, lon: 72.834 },
    "kochi": { name: "Kochi Marine Terminal & Offshore", lat: 9.967, lon: 76.242 },
    "chennai": { name: "Chennai Port & Coromandel Waters", lat: 13.085, lon: 80.298 },
    "visakhapatnam": { name: "Visakhapatnam Deepwater Harbour", lat: 17.686, lon: 83.218 },
    "mangalore": { name: "New Mangalore Port Waters", lat: 12.870, lon: 74.840 },
    "porbandar": { name: "Porbandar Marine Sanctuary Coast", lat: 21.642, lon: 69.609 },
    "kanyakumari": { name: "Kanyakumari Convergence Waters", lat: 8.078, lon: 77.555 },
    "kolkata": { name: "Kolkata Approaches & Sundarbans", lat: 22.550, lon: 88.310 },
    "nellore": { name: "Nellore Coastal Waters", lat: 14.442, lon: 79.986 },
    "puducherry": { name: "Puducherry Coast", lat: 11.941, lon: 79.808 },
    "vizag": { name: "Visakhapatnam Deepwater Harbour", lat: 17.686, lon: 83.218 },
    "andaman": { name: "Port Blair and Andaman Sea", lat: 11.623, lon: 92.726 },
    "nicobar": { name: "Great Nicobar Maritime Sector", lat: 7.030, lon: 93.790 }
  };

  // Theme colours come from CSS custom properties so charts and map layers
  // follow the active theme (night / sunlight).
  function themeColor(name, fallback) {
    const value = getComputedStyle(document.body).getPropertyValue(name).trim();
    return value || fallback;
  }

  const BACKEND_API_BASE = (() => {
    const configured = (window.__KYROX_API_BASE__ || (window.__ENV__ && window.__ENV__.KYROX_API_BASE) || '').trim().replace(/\/$/, '');
    if (configured) return configured;
    if (window.location.port === '8000') return '';
    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') return `${window.location.protocol}//${window.location.hostname}:8000`;
    return 'http://localhost:8000';
  })();


  // 2. VIEW NAVIGATION SYSTEM
  // Animated where the View Transitions API exists (the new view slides in the
  // direction you move through the sidebar); instant elsewhere, under reduced
  // motion, while the page is still loading, or when a caller needs the switch
  // to happen synchronously ({ instant: true }). Returns a promise that resolves
  // once the new view is in the DOM.
  const VIEW_ORDER = ['dashboard', 'map', 'alerts', 'species', 'analytics', 'chat'];
  const prefersReducedMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  function switchActiveView(viewName, options = {}) {
    const root = document.documentElement;
    const animate = currentActiveView !== viewName
      && !options.instant
      && typeof document.startViewTransition === 'function'
      && !prefersReducedMotion.matches
      && document.readyState === 'complete'
      && !document.hidden
      && document.body.classList.contains('mode-app')
      && !root.dataset.vt; // a page-level transition is already running
    if (!animate) {
      applyActiveView(viewName);
      return Promise.resolve();
    }
    root.dataset.navDir = VIEW_ORDER.indexOf(viewName) < VIEW_ORDER.indexOf(currentActiveView) ? 'back' : 'forward';
    root.dataset.vt = 'view';
    const transition = document.startViewTransition(() => applyActiveView(viewName));
    transition.finished.finally(() => {
      if (root.dataset.vt === 'view') delete root.dataset.vt;
      delete root.dataset.navDir;
    });
    return transition.updateCallbackDone.catch(() => {});
  }

  function applyActiveView(viewName) {
    const viewChanged = currentActiveView !== viewName;
    currentActiveView = viewName;
    const navButtons = document.querySelectorAll('.sidebar-nav-btn');
    navButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
    });

    // Views that were hidden while a language was selected still hold English
    // text, so localize them once they become visible.
    if (viewChanged && currentLang !== 'en') {
      localizeDynamicContent(currentLang);
      applyTranslatedStaticText(currentLang);
    }

    const mobButtons = document.querySelectorAll('.mobile-dock-btn');
    mobButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
    });

    const panels = document.querySelectorAll('.workspace-view-panel');
    panels.forEach(panel => {
      panel.classList.toggle('active-view', panel.id === `view-${viewName}`);
    });

    const mapStation = document.querySelector('.dashboard-map-station');
    const fullMapContainer = document.getElementById('fullscreenMapContainer');
    const chartViewport = document.getElementById('chartViewport');
    const locSearchBar = document.getElementById('locSearchBar');

    if (viewName === 'map') {
      if (fullMapContainer && chartViewport && locSearchBar) {
        fullMapContainer.appendChild(locSearchBar);
        fullMapContainer.appendChild(chartViewport);
      }
      // The map is initialized only after it has a visible container. This
      // prevents Leaflet's zero-size calculation when the dashboard is loaded.
      if (!leafletMap) initLeafletMap();
      setTimeout(() => {
        if (leafletMap) leafletMap.invalidateSize();
      }, 150);
    } else if (viewName === 'dashboard') {
      if (mapStation && chartViewport && locSearchBar) {
        mapStation.appendChild(locSearchBar);
        mapStation.appendChild(chartViewport);
      }
      if (!leafletMap) initLeafletMap();
      setTimeout(() => {
        if (leafletMap) leafletMap.invalidateSize();
      }, 100);
    } else if (viewName === 'species') {
      renderSpeciesCatalog();
    } else if (viewName === 'alerts') {
      renderBulletinsList();
    } else if (viewName === 'analytics') {
      // Plotly measured the panel while it was hidden (default 700 px wide),
      // so redraw now that it has its real size, then fit it to the container.
      requestAnimationFrame(() => {
        drawRegressionPlotly();
        const plot = document.getElementById('regressionPlotly');
        if (plot && plot._fullLayout && window.Plotly) window.Plotly.Plots.resize(plot);
      });
    }
  }

  // 3. LEAFLET MAP & TACTICAL CARTOGRAPHY
  function initLeafletMap() {
    if (leafletMap) return;
    const mapContainer = document.getElementById('marineMapLeaflet');
    if (!mapContainer) return;

    const initLat = vesselLocation.latitude;
    const initLon = vesselLocation.longitude;

    leafletMap = L.map('marineMapLeaflet', {
      center: [initLat, initLon],
      zoom: 11,
      minZoom: 3,
      maxZoom: 18,
      zoomControl: false
    });

    L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);
    updateUserLocationMarker();

    // Use the shared configuration. OpenStreetMap is the free default, so a
    // CARTO key is never required for the map to load.
    const mapConfig = window.CartoMapConfig || {};
    const tileUrl = mapConfig.BASEMAP_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    tileLayer = L.tileLayer(tileUrl, {
      attribution: mapConfig.attribution || '&copy; OpenStreetMap contributors',
      subdomains: mapConfig.subdomains || 'abc',
      maxZoom: mapConfig.maxZoom || 19,
      crossOrigin: true
    }).addTo(leafletMap);

    // Layer Groups
    riskHeatmapLayer = L.layerGroup().addTo(leafletMap);
    tacticalZonesLayer = L.layerGroup().addTo(leafletMap);
    waypointsLayer = L.layerGroup().addTo(leafletMap);
    routeLayer = L.layerGroup().addTo(leafletMap);

    // The map is populated only from live backend layers (heatmap, route).
    if (tacticalZonesLayer) tacticalZonesLayer.clearLayers();
    if (waypointsLayer) waypointsLayer.clearLayers();

    leafletMap.on('dblclick', (event) => {
      closeTacticalDrawer();
      // Double-clicking the map becomes the new analysis location. Marker and
      // polygon handlers stop propagation, so selecting an existing feature
      // keeps its current behavior.
      const lat = Number(event.latlng.lat.toFixed(6));
      const lon = Number(event.latlng.lng.toFixed(6));
      stopGpsTracking();
      updateLocation(lat, lon, `Map selection: ${formatCoord(lat, lon, 2)}`, 'map');
    });

    updateHeatmapVisuals();
  }

  function renderLeafletTacticalZones() {
    if (!tacticalZonesLayer) return;
    tacticalZonesLayer.clearLayers();
    if (!isZonesLayerActive) return;

    MAP_ZONES.forEach(z => {
      if (!z.latLngs) return;
      const color = (z.type === 'calm' || z.type === 'pfz') ? themeColor('--ok', '#6DB894') : (z.type === 'caution' ? themeColor('--warn', '#E2944F') : themeColor('--bad', '#E0625A'));
      const polygon = L.polygon(z.latLngs, {
        color: color,
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.2
      });

      const label = languageValue(z, 'label', currentLang);
      polygon.bindTooltip(label, { permanent: false, direction: 'center', className: 'tactical-map-tooltip' });

      polygon.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        selectMapZone(z.id);
      });

      tacticalZonesLayer.addLayer(polygon);
    });
  }

  function renderLeafletWaypoints() {
    if (!waypointsLayer) return;
    waypointsLayer.clearLayers();

    MAP_MARKERS.forEach(m => {
      if (!m.latLng) return;
      const isPfz = m.kind === 'pfz';
      const markColor = isPfz ? themeColor('--ok', '#6DB894') : themeColor('--bad', '#E0625A');
      const iconHtml = `<div style="width:14px;height:14px;border-radius:50%;background:${markColor};border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.4);"></div>`;
      const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [14, 14], iconAnchor: [7, 7] });
      const marker = L.marker(m.latLng, { icon: customIcon });

      const label = languageValue(m, 'label', currentLang);
      marker.bindTooltip(label, { permanent: false, direction: 'top', className: 'tactical-map-tooltip' });
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        selectMapZone(m.zone_id);
      });
      waypointsLayer.addLayer(marker);
    });
  }

  function selectMapZone(zoneId) {
    activeZoneId = zoneId;
    const zone = MAP_ZONES.find(z => z.id === zoneId);
    if (!zone) return;
    const title = languageValue(zone, 'label', currentLang);
    const reason = languageValue(zone, 'reason', currentLang);
    showTacticalDrawer(title, reason, zone.coords, zone.type, zoneId);
  }

  function showTacticalDrawer(title, reason, coords, theme, zoneId) {
    const drawer = document.getElementById('tacticalDrawer');
    if (!drawer) return;
    document.getElementById('drawerTitle').textContent = title || 'Briefing';
    document.getElementById('drawerReason').textContent = reason || '';
    document.getElementById('drawerCoordinates').textContent = coords || '';
    drawer.style.display = 'flex';
  }

  function closeTacticalDrawer() {
    const drawer = document.getElementById('tacticalDrawer');
    if (drawer) drawer.style.display = 'none';
  }

  // 4. DYNAMIC RISK HEATMAP (smooth continuous gradient)
  function renderDynamicRiskHeatmap(riskPoints, userLocation) {
    if (!riskHeatmapLayer) return;
    riskHeatmapLayer.clearLayers();
    if (heatLayer) {
      leafletMap.removeLayer(heatLayer);
      heatLayer = null;
    }
    if (!isHeatmapActive || !Array.isArray(riskPoints) || riskPoints.length === 0) return;

    // Each forecast cell is drawn as its own tile, coloured by its own risk
    // level. (A blurred heat layer summed overlapping cells and made low-risk
    // water look dangerous.)
    const lats = [...new Set(riskPoints.map(p => Number(p.latitude)))].sort((a, b) => a - b);
    const step = lats.length > 1 ? Math.abs(lats[1] - lats[0]) : 0.035;
    const half = step / 2;
    const colorFor = level => ({
      LOW: themeColor('--ok', '#6DB894'),
      MEDIUM: themeColor('--warn', '#E2944F'),
      HIGH: themeColor('--bad', '#E0625A'),
      CRITICAL: themeColor('--bad', '#E0625A')
    }[level] || themeColor('--text-3', '#6C7C8C'));

    riskPoints.forEach((pt, idx) => {
      if (pt.risk === undefined || pt.risk === null || pt.latitude === undefined || pt.longitude === undefined) return;
      const lat = Number(pt.latitude);
      const lon = Number(pt.longitude);
      const risk = Number(pt.risk) || 0;
      const isCenter = userLocation &&
        Math.abs(lat - Number(userLocation.latitude)) < 0.0001 &&
        Math.abs(lon - Number(userLocation.longitude)) < 0.0001;
      const color = colorFor(pt.risk_level);
      const cell = L.rectangle([[lat - half, lon - half], [lat + half, lon + half]], {
        color,
        weight: isCenter ? 1.5 : 0.5,
        opacity: isCenter ? 0.9 : 0.35,
        dashArray: isCenter ? null : '2 4',
        fillColor: color,
        fillOpacity: 0.12 + Math.min(0.3, risk / 220),
        interactive: true
      });

      const cellLabel = isCenter ? `Your position · risk ${risk}/100 (${pt.risk_level})` : `Cell ${idx + 1} · risk ${risk}/100 (${pt.risk_level})`;
      cell.bindTooltip(cellLabel, { permanent: false, direction: 'top', className: 'tactical-map-tooltip' });
      cell.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const num = (v, u, d = 1) => (v !== null && v !== undefined) ? `${Number(v).toFixed(d)} ${u}` : 'unavailable';
        const why = (pt.reasons && pt.reasons.length) ? ` Reasons: ${pt.reasons.join('; ')}.` : '';
        const reason = `Agent risk ${risk}/100 (${pt.risk_level}). Now: waves ${num(pt.wave_height, 'm')}, wind ${num(pt.wind_speed, 'kt', 0)}. Next 12 h max: waves ${num(pt.wave_height_max_12h, 'm')}, wind ${num(pt.wind_speed_max_12h, 'kt', 0)}.${why}`;
        showTacticalDrawer(cellLabel, reason, formatCoord(lat, lon, 4), 'caution', `risk_pt_${idx + 1}`);
      });
      riskHeatmapLayer.addLayer(cell);
    });

    const heatmapText = document.getElementById('txtHeatmapToggle');
    if (heatmapText) heatmapText.textContent = 'Risk layer: on';
  }

  function renderLiveAnalysisZones(riskPoints) {
    MAP_ZONES = [];
    MAP_MARKERS = [];
    if (!Array.isArray(riskPoints)) {
      renderLeafletTacticalZones();
      renderLeafletWaypoints();
      return;
    }

    riskPoints.forEach((point, index) => {
      if (!point.zone_type || !Number.isFinite(Number(point.latitude)) || !Number.isFinite(Number(point.longitude))) return;
      const zoneType = point.zone_type;
      const color = (zoneType === 'calm' || zoneType === 'pfz') ? themeColor('--ok', '#6DB894') : (zoneType === 'caution' ? themeColor('--warn', '#E2944F') : themeColor('--bad', '#E0625A'));
      const lat = Number(point.latitude);
      const lon = Number(point.longitude);
      const radius = 0.018;
      const latLngs = Array.from({ length: 6 }, (_, vertexIndex) => {
        const angle = (Math.PI / 3) * vertexIndex + Math.PI / 6;
        return [lat + Math.sin(angle) * radius, lon + Math.cos(angle) * radius];
      });
      const swell = point.swell_height !== null && point.swell_height !== undefined
        ? `${Number(point.swell_height).toFixed(1)}m` : 'unavailable';
      const wave = point.wave_height !== null && point.wave_height !== undefined
        ? `${Number(point.wave_height).toFixed(1)}m` : 'unavailable';
      const wind = point.wind_speed !== null && point.wind_speed !== undefined
        ? `${Number(point.wind_speed).toFixed(1)} kt` : 'unavailable';

      MAP_ZONES.push({
        id: `zone-live-${index}`,
        type: zoneType,
        center: [lat, lon],
        latLngs,
        label_en: `${point.zone_label || zoneType} • Live analysis`,
        label_hi: `${point.zone_label || zoneType} • लाइव विश्लेषण`,
        label_ta: `${point.zone_label || zoneType} • நேரலை பகுப்பாய்வு`,
        sub_en: `Risk ${point.risk}/100 • Wave ${wave} • Swell ${swell}`,
        reason_en: `Agent analysis: risk ${point.risk}/100 (${point.risk_level}), wave ${wave}, swell ${swell}, wind ${wind}.${point.restricted ? ' Protected or restricted area.' : ''}`,
        coords: formatCoord(lat, lon, 4)
      });
    });

    renderLeafletTacticalZones();
    renderLeafletWaypoints();
  }

  async function fetchRiskHeatmap(lat, lon) {
    try {
      const res = await fetch(`${BACKEND_API_BASE}/heatmap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lon })
      });
      if (res.ok) {
        const data = await res.json();
        // Check if backend has real data using the has_data flag
        if (data && data.has_data === true && Array.isArray(data.risk_points) && data.risk_points.length > 0) {
          renderDynamicRiskHeatmap(data.risk_points, data.user_location);
          // When the smooth heat gradient is active it already conveys the risk
          // field; the solid hexagon zones are only the non-heatmap fallback,
          // so suppress them to keep the overlay clean.
          renderLiveAnalysisZones(isHeatmapActive ? [] : data.risk_points);
          isBackendConnected = true;
          return;
        }
      }
    } catch (e) {
      isBackendConnected = false;
      console.warn('Heatmap fetch failed:', e);
    }

    // If no real data is available, clear the heatmap layer
    if (riskHeatmapLayer) {
      riskHeatmapLayer.clearLayers();
    }
    if (heatLayer) {
      leafletMap.removeLayer(heatLayer);
      heatLayer = null;
    }
    renderLiveAnalysisZones([]);

    // Show a message that heatmap data is unavailable
    const heatmapBtn = document.getElementById('btnToggleHeatmap');
    const heatmapText = document.getElementById('txtHeatmapToggle');
    if (heatmapBtn && heatmapText) {
      heatmapBtn.classList.remove('active');
      heatmapText.textContent = 'Risk layer: no sea data';
    }

    console.log('No real heatmap data available - heatmap disabled');
  }

  function updateHeatmapVisuals() {
    const btn = document.getElementById('btnToggleHeatmap');
    const scale = document.getElementById('heatmapLegendScale');
    const txt = document.getElementById('txtHeatmapToggle');

    if (btn) btn.classList.toggle('active', isHeatmapActive);
    if (scale) scale.style.display = isHeatmapActive ? 'flex' : 'none';

    if (txt) {
      if (!isHeatmapActive) {
        txt.textContent = 'Risk layer: off';
      } else {
        txt.textContent = 'Risk layer: on';
      }
    }

    if (riskHeatmapLayer) {
      if (isHeatmapActive) {
        if (vesselLocation) fetchRiskHeatmap(vesselLocation.latitude, vesselLocation.longitude);
      } else {
        riskHeatmapLayer.clearLayers();
        if (heatLayer) {
          leafletMap.removeLayer(heatLayer);
          heatLayer = null;
        }
      }
    }
  }

  // 5. BULLETINS & ALERTS FEED
  async function fetchLiveBulletins(lat, lon) {
    const targetLat = lat !== undefined ? lat : vesselLocation.latitude;
    const targetLon = lon !== undefined ? lon : vesselLocation.longitude;

    try {
      const res = await fetch(`${BACKEND_API_BASE}/bulletins?lat=${targetLat}&lon=${targetLon}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          BULLETINS = data;
          renderBulletinsList();
          return;
        }
      }
    } catch (e) {
      isBackendConnected = false;
    }

    // Never display invented advisories when the live bulletin feed is down.
    BULLETINS = [];
    renderBulletinsList();
  }

  // Feeds such as INCOIS publish titles in capitals; show them in title case
  // but keep agency acronyms as they are.
  const KEEP_UPPER = new Set(['INCOIS', 'GDACS', 'IMD', 'NOAA', 'ECMWF', 'OBIS', 'OSM', 'MPA', 'VHF', 'UTC', 'GFS', 'WAM', 'IFS', 'SST']);
  function readableTitle(value) {
    const text = String(value || '');
    if (!/[A-Z]/.test(text) || text !== text.toUpperCase()) return text;
    return text.toLowerCase().replace(/[\p{L}\p{N}]+/gu, word => {
      const upper = word.toUpperCase();
      return KEEP_UPPER.has(upper) ? upper : word.charAt(0).toUpperCase() + word.slice(1);
    });
  }

  // "Normal" and "resolved" are the same filter (the feed sends "normal").
  function bulletinGroup(type) {
    return type === 'danger' || type === 'caution' ? type : 'resolved';
  }

  function renderBulletinsList() {
    const container = document.getElementById('bulletinCardsList');
    if (!container) return;

    const filtered = currentAlertFilter === 'all'
      ? BULLETINS
      : BULLETINS.filter(b => bulletinGroup(b.type) === currentAlertFilter);

    const counts = { all: BULLETINS.length, danger: 0, caution: 0, resolved: 0 };
    BULLETINS.forEach(b => { counts[bulletinGroup(b.type)] += 1; });
    [['cntFiltAll', 'all'], ['cntFiltDanger', 'danger'], ['cntFiltCaution', 'caution'], ['cntFiltResolved', 'resolved']]
      .forEach(([id, key]) => { const el = document.getElementById(id); if (el) el.textContent = String(counts[key]); });

    const badgeDangerEl = document.getElementById('badgeDangerCount');
    const dangerCount = counts.danger;
    if (badgeDangerEl) badgeDangerEl.textContent = dangerCount;

    const navBadge = document.getElementById('sidebarAlertBadge');
    if (navBadge) {
      navBadge.textContent = dangerCount > 0 ? `${dangerCount} NEW` : '0';
      navBadge.dataset.hot = dangerCount > 0 ? 'true' : 'false';
    }

    const icons = { danger: 'siren', caution: 'warning', resolved: 'check-circle' };
    let html = '';
    filtered.forEach(b => {
      const type = b.type || 'normal';
      const group = bulletinGroup(type);
      const badgeText = t(`bulletinBadge${type.charAt(0).toUpperCase()}${type.slice(1)}`, type.charAt(0).toUpperCase() + type.slice(1));
      const source = [
        escapeHtml(b.source_en || ''),
        b.issued ? `issued ${escapeHtml(b.issued)}` : '',
        b.url ? `<a href="${escapeHtml(b.url)}" target="_blank" rel="noopener">details</a>` : ''
      ].filter(Boolean).join(' · ');
      // Icons sit outside the text nodes: translation replaces those nodes' text.
      html += `
        <article class="bulletin-card ${type}" data-group="${group}">
          <span class="bc-icon" aria-hidden="true"><i class="ph ph-${icons[group]} icon"></i></span>
          <div class="bc-body">
            <div class="bulletin-header-meta">
              <h3 class="bulletin-title">${escapeHtml(readableTitle(b.title_en || b.title_hi || ''))}</h3>
              <span class="bulletin-badge ${type}">${escapeHtml(badgeText)}</span>
            </div>
            <p class="bulletin-desc">${escapeHtml(b.desc_en || b.desc_hi || '')}</p>
            <div class="bulletin-source-line">${b.official ? '<span class="official-pill">Official</span>' : ''}<span>${source}</span></div>
            ${b.action_en ? `<div class="bc-action"><i class="ph ph-lightning icon" aria-hidden="true"></i><div class="bulletin-action-rec"><strong>${escapeHtml(t('bulletinActionLabel', 'Action:'))}</strong> ${escapeHtml(b.action_en)}</div></div>` : ''}
            <div class="bulletin-action-bar">
              <button type="button" class="bc-btn" onclick="window.orcaMapFocusZone('${escapeHtml(String(b.zone_id || '').replace(/'/g, ''))}')"><i class="ph ph-map-trifold icon" aria-hidden="true"></i><span class="btn-bulletin-action">Show on map</span></button>
              <button type="button" class="bc-btn" onclick="window.orcaAskInChat('${escapeHtml((b.title_en || '').replace(/'/g, ''))}')"><i class="ph ph-chat-circle-text icon" aria-hidden="true"></i><span class="btn-bulletin-action">Ask ORCA</span></button>
            </div>
          </div>
        </article>
      `;
    });

    if (!html) {
      const message = BULLETINS.length
        ? 'Nothing in this category right now.'
        : 'No warnings or assessments loaded yet. They appear here as soon as the official feeds answer.';
      html = `<div class="bulletin-empty"><i class="ph ph-shield-check icon" aria-hidden="true"></i><p>${escapeHtml(message)}</p></div>`;
    }

    container.innerHTML = html;
    const fullContainer = document.getElementById('alertsFullCardsList');
    if (fullContainer) fullContainer.innerHTML = html;
  }

  window.setAlertFilter = function(filter) {
    currentAlertFilter = filter;
    ['btnFiltAll', 'btnFiltDanger', 'btnFiltCaution', 'btnFiltResolved'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });
    const activeMap = { 'all': 'btnFiltAll', 'danger': 'btnFiltDanger', 'caution': 'btnFiltCaution', 'resolved': 'btnFiltResolved' };
    const activeBtn = document.getElementById(activeMap[filter] || 'btnFiltAll');
    if (activeBtn) activeBtn.classList.add('active');
    renderBulletinsList();
  };

  // 6. SPECIES FIELD GUIDE (list + detail)
  // Records come from OBIS via the backend. Photos, common names and the short
  // description come from Wikipedia's public page-summary API, looked up by
  // scientific name in the browser; if Wikipedia has nothing, the card says so.
  let speciesFilter = 'all';
  let speciesQuery = '';
  let speciesSelected = null;
  const IUCN_SCALE = ['LC', 'NT', 'VU', 'EN', 'CR'];
  const IUCN_CLASS = { CR: 'critically-endangered', EN: 'endangered', VU: 'vulnerable', NT: 'near-threatened' };
  const IUCN_LABEL = { CR: 'Critically endangered', EN: 'Endangered', VU: 'Vulnerable', NT: 'Near threatened' };
  const wikiCache = new Map();   // name -> Promise of the summary (dedupes requests)
  const wikiInfo = new Map();    // name -> resolved summary (used by search)

  function loadWiki(name) {
    if (!name) return Promise.resolve(null);
    if (!wikiCache.has(name)) {
      const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(name.trim().replace(/\s+/g, '_'))}`;
      wikiCache.set(name, fetch(url, { headers: { Accept: 'application/json' } })
        .then(res => (res.ok ? res.json() : null))
        .then(page => {
          if (!page || page.type === 'disambiguation') return null;
          const original = page.originalimage || {};
          const thumb = page.thumbnail && page.thumbnail.source;
          // Wikimedia only serves standard thumbnail widths; try 960px, then the
          // original (if it is not huge), then the small thumbnail.
          const images = [];
          if (thumb && original.width >= 960) images.push(thumb.replace(/\/\d+px-/, '/960px-'));
          if (original.source && original.width <= 2400) images.push(original.source);
          if (thumb) images.push(thumb);
          const common = page.title && page.title.toLowerCase() !== name.toLowerCase() ? page.title : '';
          return {
            common,
            description: page.description || '',
            extract: page.extract || '',
            thumb: thumb || '',
            images,
            url: (page.content_urls && page.content_urls.desktop && page.content_urls.desktop.page) || ''
          };
        })
        .then(info => { if (info) wikiInfo.set(name, info); return info; })
        .catch(() => null));
    }
    return wikiCache.get(name);
  }

  function groupIcon(group) {
    const g = String(group || '').toLowerCase();
    if (g.includes('bird')) return 'bird';
        return 'fish-simple';
  }

  function relevantTip(sp, tips) {
    const g = String(sp.group || '').toLowerCase();
    const keys = g.includes('shark') || g.includes('ray') ? /shark|ray|guitarfish/i
      : g.includes('turtle') ? /turtle/i
      : g.includes('mammal') ? /dolphin|porpoise|whale|dugong/i
      : g.includes('bird') ? /bird/i
      : null;
    return keys ? (tips || []).find(tip => keys.test(tip)) || '' : '';
  }

  function sortedSpecies(list) {
    return list.slice().sort((a, b) =>
      (IUCN_SCALE.indexOf(b.category) - IUCN_SCALE.indexOf(a.category)) || ((Number(b.records) || 0) - (Number(a.records) || 0)));
  }

  function iucnScaleMarkup(sp) {
    const rank = IUCN_SCALE.indexOf(sp.category);
    const steps = IUCN_SCALE.map((code, i) => `<span class="iucn-step${i <= rank ? ' on' : ''}${i === rank ? ' current' : ''}" title="${code}"></span>`).join('');
    return `
      <div class="iucn-scale" role="img" aria-label="IUCN Red List: ${escapeHtml(sp.category_label || sp.category || 'unknown')}">
        <div class="iucn-ends"><span class="iucn-label">${escapeHtml(sp.category_label || sp.category || 'Unknown')}</span><span>IUCN Red List</span></div>
        <div class="iucn-steps">${steps}</div>
        <div class="iucn-ticks"><span>Least concern</span><span>Critical</span></div>
      </div>`;
  }

  function speciesRow(sp) {
    const cls = IUCN_CLASS[sp.category] || '';
    const selected = sp.scientific_name === speciesSelected;
    const records = Number(sp.records);
    return `
      <button type="button" class="sp-row ${cls}${selected ? ' is-selected' : ''}" role="option" aria-selected="${selected}" data-name="${escapeHtml(sp.scientific_name)}">
        <span class="sp-thumb"><i class="ph ph-${groupIcon(sp.group)} icon" aria-hidden="true"></i></span>
        <span class="sp-row-text">
          <span class="sp-row-common">${escapeHtml(sp.group || 'marine species')}</span>
          <em class="sp-row-sci">${escapeHtml(sp.scientific_name)}</em>
        </span>
        <span class="sp-row-meta">
          <span class="species-iucn-badge ${cls}" title="${escapeHtml(sp.category_label || '')}">${escapeHtml(sp.category || '?')}</span>
          <span class="sp-row-rec">${Number.isFinite(records) ? records : '-'} rec.</span>
        </span>
      </button>`;
  }

  function renderSpeciesDetail(sp, tips) {
    const panel = document.getElementById('speciesDetail');
    if (!panel) return;
    if (!sp) { panel.innerHTML = ''; panel.hidden = true; return; }
    panel.hidden = false;
    const cls = IUCN_CLASS[sp.category] || '';
    const records = Number(sp.records);
    const tip = relevantTip(sp, tips);
    panel.className = `sp-detail ${cls}`;
    panel.innerHTML = `
      <div class="sp-photo is-loading"><i class="ph ph-${groupIcon(sp.group)} icon" aria-hidden="true"></i></div>
      <div class="sp-detail-body">
        <div class="sp-detail-top">
          <span class="species-group">${escapeHtml(sp.group || 'marine species')}</span>
          <span class="species-iucn-badge ${cls}">${escapeHtml(sp.category || '?')}</span>
        </div>
        <h2 class="sp-common" id="spDetailCommon">${escapeHtml(sp.scientific_name)}</h2>
        <p class="sp-sci"><em>${escapeHtml(sp.scientific_name)}</em>${sp.family ? ` · ${escapeHtml(sp.family)}` : ''}</p>
        ${iucnScaleMarkup(sp)}
        <p class="sp-extract" id="spDetailExtract"><span class="skeleton-line"></span><span class="skeleton-line short"></span></p>
        <dl class="sp-facts">
          <div><dt>OBIS records nearby</dt><dd>${Number.isFinite(records) ? records : '-'}</dd></div>
          <div><dt>Family</dt><dd>${escapeHtml(sp.family || 'Not recorded')}</dd></div>
          <div><dt>Class</dt><dd>${escapeHtml(sp.class || 'Not recorded')}</dd></div>
        </dl>
        ${tip ? `<div class="sp-tip"><i class="ph ph-hand-heart icon" aria-hidden="true"></i><p><strong>If you catch one:</strong> ${escapeHtml(tip)}</p></div>` : ''}
        <div class="sp-links">
          ${sp.obis_url ? `<a class="bc-btn" href="${escapeHtml(sp.obis_url)}" target="_blank" rel="noopener"><i class="ph ph-database icon" aria-hidden="true"></i>OBIS records</a>` : ''}
          <a class="bc-btn" id="spDetailWiki" href="https://en.wikipedia.org/wiki/${encodeURIComponent(sp.scientific_name.replace(/\s+/g, '_'))}" target="_blank" rel="noopener"><i class="ph ph-book-open icon" aria-hidden="true"></i>Wikipedia</a>
        </div>
        <p class="sp-credit" id="spDetailCredit"></p>
      </div>`;

    const name = sp.scientific_name;
    loadWiki(name).then(info => {
      if (speciesSelected !== name) return;
      const photo = panel.querySelector('.sp-photo');
      const common = document.getElementById('spDetailCommon');
      const extract = document.getElementById('spDetailExtract');
      const credit = document.getElementById('spDetailCredit');
      const wiki = document.getElementById('spDetailWiki');
      if (photo) photo.classList.remove('is-loading');
      if (!info) {
        if (extract) extract.textContent = 'No Wikipedia summary is available for this species.';
        if (photo) photo.classList.add('is-empty');
        return;
      }
      if (common && info.common) common.textContent = info.common;
      if (extract) extract.textContent = info.extract || info.description || 'No summary available.';
      if (wiki && info.url) wiki.href = info.url;
      if (credit) credit.textContent = info.images.length ? 'Photo and summary: Wikipedia / Wikimedia Commons' : 'Summary: Wikipedia';
      if (!photo) return;
      if (!info.images.length) { photo.classList.add('is-empty'); return; }
      const candidates = info.images.slice();
      const tryNext = () => {
        const src = candidates.shift();
        if (!src) { photo.classList.add('is-empty'); return; }
        const img = new Image();
        img.alt = `${info.common || name} (${name})`;
        img.decoding = 'async';
        img.onload = () => {
          if (speciesSelected !== name) return;
          photo.innerHTML = '';
          photo.appendChild(img);
          photo.classList.add('has-photo');
        };
        img.onerror = tryNext;
        img.src = src;
      };
      tryNext();
    });
  }

  function hydrateRows(grid) {
    grid.querySelectorAll('.sp-row').forEach(row => {
      const name = row.dataset.name;
      loadWiki(name).then(info => {
        if (!info || !row.isConnected) return;
        if (info.common) {
          const label = row.querySelector('.sp-row-common');
          if (label) label.textContent = info.common;
        }
        if (info.thumb) {
          const thumb = row.querySelector('.sp-thumb');
          // Not lazy: an image that is not in the document yet would never load.
          const img = new Image();
          img.alt = '';
          img.onload = () => { if (thumb) { thumb.innerHTML = ''; thumb.appendChild(img); thumb.classList.add('has-photo'); } };
          img.src = info.thumb;
        }
      });
    });
  }

  function renderSpeciesStats(eco, counts) {
    const box = document.getElementById('speciesStats');
    if (!box) return;
    if (!eco || !eco.available || !eco.species || !eco.species.length) { box.innerHTML = ''; return; }
    const total = eco.species.length;
    const segments = ['CR', 'EN', 'VU', 'NT'].filter(code => counts[code]).map(code => `
        <button type="button" class="sp-seg ${IUCN_CLASS[code]}${speciesFilter === code ? ' active' : ''}" style="flex-grow:${counts[code]}" data-iucn="${code}" aria-label="${IUCN_LABEL[code]}: ${counts[code]}"></button>`).join('');
    const legend = ['CR', 'EN', 'VU', 'NT'].filter(code => counts[code]).map(code => `
        <button type="button" class="sp-legend-item ${IUCN_CLASS[code]}${speciesFilter === code ? ' active' : ''}" data-iucn="${code}"><span class="sp-legend-dot" aria-hidden="true"></span>${IUCN_LABEL[code]}<strong>${counts[code]}</strong></button>`).join('');
    box.innerHTML = `
      <div class="sp-total"><strong>${total}</strong><span>threatened species recorded within about 25 km</span></div>
      <div class="sp-bar" role="group" aria-label="Species by IUCN category">${segments}</div>
      <div class="sp-legend">${legend}</div>`;
  }

  function renderSpeciesCatalog() {
    const grid = document.getElementById('speciesGridContainer');
    if (!grid) return;
    const eco = lastEcosystem;
    const box = document.getElementById('speciesBycatchBox');
    const toolbar = document.getElementById('speciesToolbar');
    const guide = grid.closest('.sp-guide');
    const showEmpty = message => {
      grid.innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
      if (box) box.hidden = true;
      if (toolbar) toolbar.hidden = true;
      if (guide) guide.classList.add('is-empty');
      renderSpeciesStats(null);
      renderSpeciesDetail(null);
    };
    if (!eco) {
      if (guide) guide.classList.remove('is-empty');
      grid.innerHTML = Array.from({ length: 6 }, () => '<div class="sp-row is-skeleton" aria-hidden="true"><span class="sp-thumb"></span><span class="sp-row-text"><span class="skeleton-line short"></span><span class="skeleton-line"></span></span></div>').join('');
      return;
    }
    if (!eco.available) return showEmpty('The OBIS biodiversity service is unreachable right now. No species information is shown rather than guessing.');
    if (!eco.species || !eco.species.length) return showEmpty('No IUCN-threatened marine species have OBIS records within about 25 km of this location. Absence of records is not proof of absence.');
    if (guide) guide.classList.remove('is-empty');

    const tips = eco.bycatch_tips || [];
    if (box) {
      box.hidden = !tips.length;
      box.innerHTML = tips.length
        ? `<div class="bycatch-head"><i class="ph ph-hand-heart icon" aria-hidden="true"></i><strong>Bycatch advice for this area</strong></div><ul>${tips.map(tip => `<li>${escapeHtml(tip)}</li>`).join('')}</ul>`
        : '';
    }

    const counts = { all: eco.species.length, CR: 0, EN: 0, VU: 0, NT: 0 };
    eco.species.forEach(sp => { if (counts[sp.category] !== undefined) counts[sp.category] += 1; });
    renderSpeciesStats(eco, counts);
    if (toolbar) {
      toolbar.hidden = false;
      ['all', 'CR', 'EN', 'VU', 'NT'].forEach(key => {
        const el = document.getElementById(`spCnt${key === 'all' ? 'All' : key}`);
        if (el) el.textContent = String(counts[key]);
        const btn = toolbar.querySelector(`[data-iucn="${key}"]`);
        if (btn) {
          btn.hidden = key !== 'all' && counts[key] === 0;
          btn.classList.toggle('active', key === speciesFilter);
        }
      });
    }

    const query = speciesQuery.trim().toLowerCase();
    const visible = sortedSpecies(eco.species).filter(sp => {
      if (speciesFilter !== 'all' && sp.category !== speciesFilter) return false;
      if (!query) return true;
      const wiki = wikiInfo.get(sp.scientific_name);
      return [sp.scientific_name, sp.group, sp.family, sp.category_label, wiki && wiki.common].some(v => String(v || '').toLowerCase().includes(query));
    });
    if (!visible.some(sp => sp.scientific_name === speciesSelected)) speciesSelected = visible.length ? visible[0].scientific_name : null;

    grid.innerHTML = visible.length
      ? visible.map(speciesRow).join('')
      : `<p class="empty-state">No species match${query ? ` "${escapeHtml(speciesQuery.trim())}"` : ''} in this category.</p>`;
    hydrateRows(grid);
    renderSpeciesDetail(visible.find(sp => sp.scientific_name === speciesSelected) || null, tips);
  }

  function selectSpecies(name, focus) {
    if (!name || name === speciesSelected) return;
    speciesSelected = name;
    const grid = document.getElementById('speciesGridContainer');
    if (grid) {
      grid.querySelectorAll('.sp-row').forEach(row => {
        const on = row.dataset.name === name;
        row.classList.toggle('is-selected', on);
        row.setAttribute('aria-selected', String(on));
        if (on && focus) row.focus();
      });
    }
    const sp = lastEcosystem && (lastEcosystem.species || []).find(item => item.scientific_name === name);
    renderSpeciesDetail(sp || null, (lastEcosystem && lastEcosystem.bycatch_tips) || []);
    const detail = document.getElementById('speciesDetail');
    if (detail && window.matchMedia('(max-width: 1000px)').matches) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function initSpeciesToolbar() {
    const setFilter = value => { speciesFilter = value || 'all'; renderSpeciesCatalog(); };
    const toolbar = document.getElementById('speciesToolbar');
    if (toolbar) toolbar.querySelectorAll('[data-iucn]').forEach(btn => btn.addEventListener('click', () => setFilter(btn.dataset.iucn)));
    const stats = document.getElementById('speciesStats');
    if (stats) stats.addEventListener('click', event => {
      const btn = event.target.closest('[data-iucn]');
      if (btn) setFilter(speciesFilter === btn.dataset.iucn ? 'all' : btn.dataset.iucn);
    });
    const search = document.getElementById('speciesSearch');
    if (search) search.addEventListener('input', () => { speciesQuery = search.value; renderSpeciesCatalog(); });
    const grid = document.getElementById('speciesGridContainer');
    if (grid) {
      grid.addEventListener('click', event => {
        const row = event.target.closest('.sp-row[data-name]');
        if (row) selectSpecies(row.dataset.name);
      });
      grid.addEventListener('keydown', event => {
        if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
        const rows = Array.from(grid.querySelectorAll('.sp-row[data-name]'));
        const index = rows.findIndex(row => row.dataset.name === speciesSelected);
        const next = rows[Math.max(0, Math.min(rows.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)))];
        if (next) { event.preventDefault(); selectSpecies(next.dataset.name, true); }
      });
    }
  }

  async function fetchEcosystem(lat, lon) {
    try {
      const res = await fetch(`${BACKEND_API_BASE}/ecosystem?lat=${lat}&lon=${lon}`);
      lastEcosystem = res.ok ? await res.json() : { available: false };
    } catch (e) {
      lastEcosystem = { available: false };
    }
    const kpi = document.getElementById('kpiValSpecies');
    const trend = document.getElementById('kpiTrendSpecies');
    if (kpi) kpi.textContent = lastEcosystem.available ? String(lastEcosystem.total) : 'N/A';
    if (trend) {
      const c = lastEcosystem.counts || {};
      const serious = (c.CR || 0) + (c.EN || 0);
      trend.textContent = lastEcosystem.available ? `${serious} CR/EN` : 'source offline';
      trend.className = `kpi-trend ${serious ? 'warning' : 'positive'}`;
    }
    if (currentActiveView === 'species') renderSpeciesCatalog();
  }

  window.orcaMapFocusZone = function(zoneId) {
    // The map exists only once its view has been applied.
    switchActiveView('map').then(() => selectMapZone(zoneId));
  };

  window.orcaAskInChat = function(queryText) {
    switchActiveView('chat');
    const input = document.getElementById('tacticalQueryInput');
    if (input) {
      input.value = `Tell me more about: ${queryText}`;
      triggerTacticalQuery(input.value);
    }
  };

  // 7. TELEMETRY & GPS FIX
  async function fetchLiveTelemetry(lat, lon) {
    const targetLat = lat !== undefined ? lat : vesselLocation.latitude;
    const targetLon = lon !== undefined ? lon : vesselLocation.longitude;

    try {
      const res = await fetch(`${BACKEND_API_BASE}/telemetry?lat=${targetLat}&lon=${targetLon}`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Telemetry request failed (${res.status})`);
      const data = await res.json();
      isBackendConnected = true;
      updateBridgeTelemetryUI(data);
      return data;
    } catch (e) {
      isBackendConnected = false;
      updateBridgeTelemetryUI({ status: 'offline' });
      MAP_ZONES = [];
      MAP_MARKERS = [];
      renderLiveAnalysisZones([]);
      renderLeafletTacticalZones();
      renderLeafletWaypoints();
      return null;
    }
  }

  function formatCoord(lat, lon, digits = 4) {
    if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) return '--';
    lat = Number(lat); lon = Number(lon);
    return `${Math.abs(lat).toFixed(digits)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(digits)}°${lon >= 0 ? 'E' : 'W'}`;
  }

  function formatGpsFix(location) {
    if (!location || typeof location.latitude !== 'number') return 'Location unavailable';
    const src = locationSource === 'gps' ? 'GPS' : 'SELECTED';
    return `${src === 'GPS' ? 'GPS' : 'Selected'} · ${formatCoord(location.latitude, location.longitude, 3)}`;
  }

  function updateBridgeTelemetryUI(data) {
    data = data || {};
    window.lastBridgeTelemetry = data;
    document.dispatchEvent(new CustomEvent('orca:telemetry', { detail: { data, place: vesselLocation.name } }));
    const offline = data.status === 'offline';
    const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
    const setHtml = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
    const num = (v, d = 1) => (typeof v === 'number' && Number.isFinite(v)) ? v.toFixed(d) : null;

    const status = document.getElementById('txtBackendStatus');
    if (status) status.textContent = offline ? 'OFFLINE' : (data.stale ? 'STALE DATA' : 'LIVE');
    const statusPill = document.getElementById('backendStatusPill');
    if (statusPill) statusPill.dataset.state = offline ? 'offline' : (data.stale ? 'stale' : 'live');

    if (offline) {
      renderVerdict(data);
      setText('txtTelemetryFix', 'Live feed offline');
      ['kpiValRisk', 'kpiValWave', 'kpiValWind', 'kpiValTemp', 'kpiValAlerts', 'heroValRisk', 'heroValWave', 'heroValWind', 'heroValAlerts']
        .forEach(id => setText(id, '--'));
      setText('kpiTrendRisk', 'backend offline');
      return;
    }

    setText('txtTelemetryFix', formatGpsFix(data.location || vesselLocation));
    const tend = data.pressure_tendency_3h;
    const arrow = typeof tend === 'number' ? (tend <= -1 ? ' ↓' : tend >= 1 ? ' ↑' : ' →') : '';
    const val = v => (!v || v === 'UNAVAILABLE') ? 'n/a' : v;
    setHtml('txtTelemWind', `Wind <strong>${escapeHtml(val(data.wind))}</strong>`);
    setHtml('txtTelemWave', `Waves <strong>${escapeHtml(val(data.wave))}</strong>`);
    setHtml('txtTelemBaro', `Pressure <strong>${escapeHtml(val(data.baro))}${arrow}</strong>`);
    setHtml('txtTelemSsh', `High tide <strong>${escapeHtml(val(String(data.highTide || '').replace(', model', '')))}</strong>`);
    setHtml('txtTelemSwell', `Swell <strong>${escapeHtml(val(data.swell))}${data.swell_period ? ` · ${Number(data.swell_period).toFixed(0)} s` : ''}</strong>`);
    renderVerdict(data);

    const level = data.risk_level || '--';
    const levelClass = { LOW: 'positive', MEDIUM: 'warning', HIGH: 'danger', CRITICAL: 'danger' }[level] || '';
    const noSea = data.marine_available === false;
    setText('kpiValRisk', noSea ? 'N/A' : (data.risk_score ?? '--'));
    const riskTrend = document.getElementById('kpiTrendRisk');
    if (riskTrend) {
      riskTrend.textContent = noSea ? 'not at sea' : `${level} • ${data.confidence || '?'} confidence`;
      riskTrend.className = `kpi-trend ${levelClass}`;
    }
    const outlook = data.outlook || {};
    setText('kpiValWave', num(data.wave_height) ?? '--');
    setText('kpiTrendWave', `12 h max ${num(outlook.wave_height_max_12h) ?? '--'} m`);
    setText('kpiValWind', num(data.wind_speed, 0) ?? '--');
    setText('kpiTrendWind', `gusts ${num(data.wind_gusts, 0) ?? '--'} kt • 12 h max ${num(outlook.wind_speed_max_12h, 0) ?? '--'}`);
    setText('kpiValTemp', (data.sst || "--").replace("°C", "").trim());
    setText('kpiTrendTemp', data.observed_at ? `as of ${data.observed_at.slice(11, 16)} UTC` : '--');

    const official = Array.isArray(data.official_alerts) ? data.official_alerts : [];
    const feeds = data.official_feeds || {};
    const feedDown = Object.values(feeds).some(f => f && f.available === false);
    setText('kpiValAlerts', String(official.length));
    const alertTrend = document.getElementById('kpiTrendAlerts');
    if (alertTrend) {
      const worst = official[0];
      alertTrend.textContent = feedDown ? 'a feed is offline' : (worst ? `${worst.level} • ${worst.source}` : 'none in range');
      alertTrend.className = `kpi-trend ${feedDown || worst ? 'warning' : 'positive'}`;
    }

    setText('heroValRisk', noSea ? 'N/A' : `${level}`);
    setText('heroValWave', num(data.wave_height) ? `${num(data.wave_height)} m` : '--');
    setText('heroValWind', num(data.wind_speed, 0) ? `${num(data.wind_speed, 0)} kt` : '--');
    setText('heroValAlerts', feedDown ? `${official.length}*` : String(official.length));
  }

  // Overview headline: a plain-language verdict with the top reasons.
  function renderVerdict(data) {
    const card = document.getElementById('verdictCard');
    if (!card) return;
    const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
    setText('verdictPlace', vesselLocation.name || formatCoord(vesselLocation.latitude, vesselLocation.longitude, 2));
    const list = document.getElementById('verdictReasons');
    const fill = document.getElementById('riskMeterFill');
    const offline = data.status === 'offline';
    const noSea = data.marine_available === false;
    const level = offline || noSea ? '' : (data.risk_level || '');
    card.dataset.level = level;
    const headline = offline ? 'Live data unavailable'
      : noSea ? 'No sea data at this point'
      : ({ LOW: 'Suitable to go out', MEDIUM: 'Go out with caution', HIGH: 'Return to shore', CRITICAL: 'Do not go to sea' }[level] || 'Checking conditions');
    setText('verdictHeadline', headline);
    setText('verdictStatus', offline || noSea || !level ? '' : `${level.charAt(0)}${level.slice(1).toLowerCase()} risk`);
    let reasons = Array.isArray(data.reasons) ? data.reasons.slice(0, 3) : [];
    if (offline) reasons = ['ORCA could not reach its data sources. Check your official marine forecast before going out.'];
    else if (noSea) reasons = ['This position looks like land. Search a harbour or tap the sea on the map.'];
    else if (!reasons.length) reasons = ['No hazards now or in the next 12 hours from the forecast models and official feeds.'];
    if (list) list.innerHTML = reasons.map(r => `<li class="${r.startsWith('OFFICIAL') ? 'official' : ''}">${escapeHtml(r.replace(/^OFFICIAL /, 'Official · '))}</li>`).join('');
    if (fill) fill.style.left = `${Math.max(0, Math.min(100, Number(data.risk_score) || 0))}%`;
    const meta = [];
    if (data.observed_at) meta.push(`Updated ${data.observed_at.slice(11, 16)} UTC`);
    if (data.stale) meta.push('using last good data');
    if (Array.isArray(data.sources) && data.sources.length) meta.push(data.sources.join(' · '));
    setText('verdictMeta', offline ? '' : meta.join(' · '));
  }

  function updateUserLocationMarker() {
    if (!leafletMap || !vesselLocation) return;
    const point = [vesselLocation.latitude, vesselLocation.longitude];
    if (!userLocationMarker) {
      userLocationMarker = L.circleMarker(point, {
        radius: 7, color: '#ffffff', weight: 2.5, fillColor: themeColor('--accent', '#E0559A'), fillOpacity: 1
      }).bindTooltip('Device location', { direction: 'top' }).addTo(leafletMap);
    } else {
      userLocationMarker.setLatLng(point);
    }
  }

  function updateLocation(lat, lon, name, source) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    vesselLocation = { latitude: lat, longitude: lon, name: name || formatCoord(lat, lon, 2) };
    const placeEl = document.getElementById('verdictPlace');
    if (placeEl) placeEl.textContent = vesselLocation.name;
    const chatPlace = document.getElementById('chatPlace');
    if (chatPlace) chatPlace.textContent = vesselLocation.name;
    customLocationName = vesselLocation.name;
    locationSource = source || 'manual';
    updateUserLocationMarker();
    if (leafletMap) leafletMap.flyTo([lat, lon], 11, { duration: 0.8 });
    // Refresh live feeds for the newly selected point. Synthetic zones are not
    // regenerated here, so a map click cannot recreate the old fixed scheme.
    fetchLiveTelemetry(lat, lon);
    fetchLiveBulletins(lat, lon);
    fetchEcosystem(lat, lon);
    if (isHeatmapActive) fetchRiskHeatmap(lat, lon);
    if (currentActiveView === 'analytics') loadRegressionData(activeRegVar);
    updateGpsButton();
  }

  function updateGpsButton() {
    const btn = document.getElementById('btnGpsToggle');
    const text = document.getElementById('txtGpsToggle');
    if (btn) {
      btn.classList.toggle('gps-active', isGpsTrackingEnabled);
      btn.setAttribute('aria-pressed', String(isGpsTrackingEnabled));
    }
    if (text) text.textContent = isGpsTrackingEnabled ? 'GPS: ON' : 'GPS: OFF';
  }

  function stopGpsTracking() {
    if (gpsWatchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(gpsWatchId);
    gpsWatchId = null;
    isGpsTrackingEnabled = false;
    updateGpsButton();
  }

  function startGpsTracking() {
    if (!navigator.geolocation) {
      window.alert('GPS is not available in this browser. Use a coastal port or coordinates instead.');
      return;
    }
    isGpsTrackingEnabled = true;
    updateGpsButton();
    const onPosition = position => updateLocation(position.coords.latitude, position.coords.longitude, 'Device GPS', 'gps');
    const onError = error => {
      stopGpsTracking();
      const message = error.code === 1 ? 'Location permission was denied.' : 'Unable to read the device location.';
      window.alert(`${message} Select a port or enter coordinates to continue.`);
    };
    navigator.geolocation.getCurrentPosition(onPosition, onError, { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
    gpsWatchId = navigator.geolocation.watchPosition(onPosition, onError, { enableHighAccuracy: true, maximumAge: 30000, timeout: 20000 });
  }

  function resolveLocationInput(raw) {
    const input = String(raw || '').trim();
    if (!input) return null;

    // Coordinates: "15.24, 73.80", "15.24N 73.80E", "-33.9 18.4"
    const m = input.match(/^\s*(-?\d+(?:\.\d+)?)\s*°?\s*([NSns])?[\s,]+(-?\d+(?:\.\d+)?)\s*°?\s*([EWew])?\s*$/);
    if (m) {
      let lat = Number(m[1]);
      let lon = Number(m[3]);
      if (m[2] && m[2].toUpperCase() === 'S') lat = -Math.abs(lat);
      if (m[4] && m[4].toUpperCase() === 'W') lon = -Math.abs(lon);
      if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) return { lat, lon, name: formatCoord(lat, lon, 2) };
    }

    const key = input.toLowerCase();
    if (MARITIME_PORTS_CATALOG[key]) {
      const port = MARITIME_PORTS_CATALOG[key];
      return { lat: port.lat, lon: port.lon, name: port.name };
    }
    const match = Object.keys(MARITIME_PORTS_CATALOG).find(k => key === k || MARITIME_PORTS_CATALOG[k].name.toLowerCase() === key);
    if (match) {
      const port = MARITIME_PORTS_CATALOG[match];
      return { lat: port.lat, lon: port.lon, name: port.name };
    }
    return null;
  }

  // Coordinates / known ports first, then worldwide geocoding via the backend.
  async function resolveLocationAnywhere(raw) {
    const local = resolveLocationInput(raw);
    if (local) return local;
    const q = String(raw || '').trim();
    if (q.length < 2) return null;
    try {
      const res = await fetch(`${BACKEND_API_BASE}/geocode?q=${encodeURIComponent(q)}`);
      if (!res.ok) return null;
      const place = await res.json();
      return { lat: place.latitude, lon: place.longitude, name: place.name };
    } catch (e) {
      return null;
    }
  }

  // 8. "ASK ORCA" AI ASSISTANT CHAT ENGINE
  async function triggerTacticalQuery(text) {
    if (!text || !text.trim()) return;
    const thread = document.getElementById('tacticalChatThread');
    const input = document.getElementById('tacticalQueryInput');
    if (input) input.value = '';
    const view = document.getElementById('view-chat');
    if (view) view.classList.add('has-messages');

    const userMsg = document.createElement('div');
    userMsg.className = 'msg msg-user';
    userMsg.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    thread.appendChild(userMsg);

    // Working state: name each agent as it is consulted (they run together).
    const reply = document.createElement('div');
    reply.className = 'msg msg-orca is-working';
    const steps = [
      ['wind', 'Weather agent: ECMWF and NOAA wind'],
      ['waves', 'Marine agent: waves, swell and tide'],
      ['siren', 'Official alerts: INCOIS and GDACS'],
      ['shield-check', 'Geospatial agent: protected areas'],
      ['fish', 'Ecosystem agent: OBIS species records'],
      ['scales', 'Consensus agent: cross-checking sources']
    ];
    reply.innerHTML = `
      ${orcaAvatar()}
      <div class="msg-body">
        <div class="msg-meta"><span class="msg-name">ORCA</span><span class="msg-working-label">${escapeHtml(t('chatProcessing', 'Working'))}</span></div>
        <ol class="agent-steps">${steps.map(([icon, label], i) => `<li style="--i:${i}"><i class="ph ph-${icon} icon" aria-hidden="true"></i><span>${escapeHtml(label)}</span></li>`).join('')}</ol>
      </div>`;
    thread.appendChild(reply);
    scrollThread(thread);
    document.dispatchEvent(new CustomEvent('orca:asking', { detail: { text } }));
    const stepEls = reply.querySelectorAll('.agent-steps li');
    let stepIndex = 0;
    const ticker = window.setInterval(() => {
      if (stepIndex < stepEls.length) {
        if (stepIndex > 0) stepEls[stepIndex - 1].classList.replace('is-active', 'is-done');
        stepEls[stepIndex].classList.add('is-active');
        stepIndex += 1;
      }
    }, 450);

    const finish = html => {
      window.clearInterval(ticker);
      reply.classList.remove('is-working');
      reply.querySelector('.msg-body').innerHTML = html;
      scrollThread(thread);
    };

    try {
      const res = await fetch(`${BACKEND_API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          language: currentLang,
          latitude: vesselLocation.latitude,
          longitude: vesselLocation.longitude,
          zone_id: activeZoneId
        })
      });

      if (res.ok) {
        const requestEpoch = languageEpoch;
        const requestLanguage = currentLang;
        const data = await res.json();
        document.dispatchEvent(new CustomEvent('orca:answer', { detail: { data } }));
        let answer = (data.chat && data.chat.response) || (data.recommendation && (data.recommendation.response_text || data.recommendation.message)) || data.message || 'Analysis complete.';
        if (data.status === 'location_required') answer = data.message || answer;
        // The backend localizes responses, so only translate when that failed.
        if (requestLanguage !== 'en' && (!data.chat || !data.chat.translation_success)) {
          answer = await translateForLanguage(answer, requestLanguage);
        }
        if (requestEpoch !== languageEpoch) { window.clearInterval(ticker); return; }

        const level = (data.risk && data.risk.risk_level) || '';
        reply.dataset.level = level;
        const place = data.place_name || vesselLocation.name;
        const levelLabel = level ? `${level.charAt(0)}${level.slice(1).toLowerCase()} risk` : '';
        finish(`
          <div class="msg-meta">
            <span class="msg-name">ORCA</span>
            ${levelLabel ? `<span class="verdict-status">${escapeHtml(levelLabel)}</span>` : ''}
            <span class="msg-place"><i class="ph ph-crosshair-simple icon" aria-hidden="true"></i>${escapeHtml(place)}</span>
          </div>
          ${structuredAnswer(data, answer, requestLanguage)}
          <div class="msg-actions">${speakerButtonMarkup(answer)}</div>
          ${agentReasoningMarkup(data)}`);
        return;
      }
    } catch (e) {}

    // Never invent an answer: say the system could not reach its agents.
    document.dispatchEvent(new CustomEvent('orca:answer', { detail: { data: null } }));
    const failText = 'ORCA could not reach its agents right now, so no advice is given. Check your official marine forecast (INCOIS or your national met service) before going out, and keep VHF Channel 16 on.';
    const localized = await translateForLanguage(failText, currentLang);
    reply.dataset.level = 'OFFLINE';
    finish(`
      <div class="msg-meta"><span class="msg-name">ORCA</span><span class="verdict-status">Offline</span></div>
      <p class="answer-lead">${escapeHtml(localized)}</p>`);
  }

  function scrollThread(thread) {
    requestAnimationFrame(() => thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' }));
  }

  function orcaAvatar() {
    return `<div class="msg-avatar" aria-hidden="true"><svg viewBox="0 0 32 32"><path class="brand-wave" d="M6 20c3 0 4.5-2.4 7.5-2.4S17 20 20 20s4.2-1.2 6-1.8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/><path d="M12 17.4c1-4.6 3.6-8.2 7.5-9.4-1.1 3.4-1.1 6.3 0 9.6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/></svg></div>`;
  }

  // English answers are laid out as lead / actions / why; translated answers
  // stay as one localized paragraph.
  function structuredAnswer(data, reply, lang) {
    const rec = data && data.recommendation;
    if (lang !== 'en' || !rec || !rec.message) return `<p class="answer-lead">${formatMarkdown(reply)}</p>`;
    const tips = (rec.recommendations || []).slice(0, 4);
    const tidy = value => String(value).replace(/OFFICIAL /g, 'Official ');
    return `
      <p class="answer-lead">${escapeHtml(tidy(rec.message))}</p>
      ${tips.length ? `<div class="answer-block"><span class="answer-label">What to do</span><ul class="answer-list">${tips.map(tip => `<li><i class="ph ph-check-circle icon" aria-hidden="true"></i><span>${escapeHtml(tidy(tip))}</span></li>`).join('')}</ul></div>` : ''}
      ${rec.explanation ? `<p class="answer-why">${escapeHtml(tidy(rec.explanation))}</p>` : ''}`;
  }

  // Explainability: which agents ran, what they found, how confident ORCA is.
  function agentReasoningMarkup(data) {
    if (!data || data.status !== 'success') return '';
    const risk = data.risk || {};
    const findings = (data.consensus || {}).findings || [];
    const trace = data.agent_trace || [];
    const typeLabel = { agreement: 'Agrees', conflict: 'Conflict', trend: 'Trend', official: 'Official', gap: 'Data gap', insight: 'Insight', ecosystem: 'Ecosystem' };
    const rows = findings.map(f => `
        <li data-type="${escapeHtml(f.type)}">
          <span class="tl-dot" aria-hidden="true"></span>
          <div><span class="tl-head"><strong>${escapeHtml(typeLabel[f.type] || f.type)}</strong><span class="finding-agents">${escapeHtml((f.agents || []).join(' + ').replace(/_agent/g, '').replace(/_/g, ' '))}</span></span>
          <span class="tl-text">${escapeHtml(String(f.message).replace(/^(INCOIS|GDACS) /, 'Official $1 '))}</span></div>
        </li>`).join('');
    const okCount = trace.filter(a => a.status === 'ok').length;
    const chips = trace.map(a => `<span class="trace-chip ${a.status === 'ok' ? 'ok' : 'failed'}" title="${escapeHtml(a.error || '')}">${escapeHtml(a.agent.replace('_agent', '').replace(/_/g, ' '))} ${a.status === 'ok' ? `${a.ms} ms` : 'failed'}</span>`).join('');
    return `
      <details class="agent-reasoning">
        <summary><i class="ph ph-tree-structure icon" aria-hidden="true"></i>How ORCA decided<span class="summary-meta">risk ${risk.risk_score ?? '-'}/100 · ${escapeHtml(risk.confidence || '?')} confidence · ${okCount}/${trace.length} agents</span></summary>
        ${rows ? `<ol class="reason-timeline">${rows}</ol>` : '<p class="answer-why">No cross-check findings.</p>'}
        <div class="trace-row">${chips}</div>
      </details>`;
  }

  // Voice Command (Web Speech API)
  let recognition = null;
  let isListening = false;

  function initVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = speechLanguage(currentLang);

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      const input = document.getElementById('tacticalQueryInput');
      if (input) input.value = transcript;
      triggerTacticalQuery(transcript);
      stopVoiceListening();
    };

    recognition.onerror = () => { stopVoiceListening(); };
    recognition.onend = () => { stopVoiceListening(); };
  }

  function startVoiceListening() {
    if (!recognition) initVoiceRecognition();
    if (!recognition) return;
    try {
      recognition.lang = speechLanguage(currentLang);
      recognition.start();
      isListening = true;
      const btn = document.getElementById('btnVoiceCommand');
      if (btn) btn.classList.add('listening');
    } catch (e) {}
  }

  function stopVoiceListening() {
    if (recognition && isListening) {
      try { recognition.stop(); } catch (e) {}
    }
    isListening = false;
    const btn = document.getElementById('btnVoiceCommand');
    if (btn) btn.classList.remove('listening');
  }

  // 9. 24-HOUR LINEAR REGRESSION PREDICTION MODELLING ENGINE

  let activeRegVar = 'wave_height';
  let regShowCI = true;
  let regressionDataCache = null;
  let hoverActiveIndex = null;

  async function loadRegressionData(varKey) {
    varKey = varKey || activeRegVar;
    activeRegVar = varKey;
    document.querySelectorAll('.graph-var-pill').forEach(btn => btn.classList.toggle('active', btn.dataset.var === varKey));
    const params = new URLSearchParams({ variable: varKey, lat: vesselLocation.latitude, lon: vesselLocation.longitude, horizon_hours: 24, past_hours: 24 });
    try {
      const response = await fetch(`${BACKEND_API_BASE}/predictions/forecast?${params}`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok || body.success === false) throw new Error(body.error || `Forecast request failed (${response.status})`);
      regressionDataCache = body;
    } catch (error) {
      // No synthetic fallback: show that the forecast is unavailable.
      regressionDataCache = null;
      const plot = document.getElementById('regressionPlotly');
      if (plot && window.Plotly) window.Plotly.purge(plot);
      const adv = document.getElementById('txtRegAdvisoryBody');
      if (adv) adv.textContent = `Forecast unavailable for this location: ${error.message}`;
      ['valBtmCurrent', 'valBtmMid', 'valBtmPeak', 'txtRegEquation', 'txtRegR2'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '--'; });
      const panel = document.getElementById('modelEvaluationPanel');
      if (panel) panel.textContent = '';
      return;
    }
    drawRegressionPlotly();
    updateRegressionHUD();
  }

  // Plotly (about 3.5 MB) is only needed for the Forecast chart, so it is not
  // in <head> where it would block the first paint on slow mobile networks.
  // It is fetched in the background after load, or on demand here.
  const PLOTLY_SRC = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
  let plotlyLoading = null;
  function ensurePlotly() {
    if (window.Plotly) return Promise.resolve(window.Plotly);
    if (!plotlyLoading) {
      plotlyLoading = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = PLOTLY_SRC;
        script.async = true;
        script.onload = () => (window.Plotly ? resolve(window.Plotly) : reject(new Error('Chart library did not initialise')));
        script.onerror = () => { plotlyLoading = null; reject(new Error('Chart library could not be downloaded')); };
        document.head.appendChild(script);
      });
    }
    return plotlyLoading;
  }

  function drawRegressionPlotly() {
    const plot = document.getElementById('regressionPlotly');
    const data = regressionDataCache;
    if (plot && data && typeof window.Plotly === 'undefined') {
      ensurePlotly()
        .then(() => drawRegressionPlotly())
        .catch(() => { plot.innerHTML = '<p class="empty-state">The chart library could not be loaded. The figures below are still live.</p>'; });
      return;
    }
    if (!plot || !data) {
      drawRegressionCanvas();
      return;
    }
    const history = data.history || [];
    const predictions = data.predictions || [];
    const evaluation = data.model_evaluation || {};
    const traces = [
      { x: history.map(point => point.hour_offset), y: history.map(point => point.value), text: history.map(point => point.time_label), mode: 'lines+markers', name: 'Past 24 h (model hindcast)', line: { color: themeColor('--text-2', '#A5B3C1'), width: 2 }, marker: { size: 4 } },
      { x: predictions.map(point => point.hour_offset), y: predictions.map(point => point.predicted_value), text: predictions.map(point => point.time_label), mode: 'lines', name: 'Forecast (best model blend)', line: { color: themeColor('--accent', '#E0559A'), width: 2.5 } },
      { x: predictions.map(point => point.hour_offset), y: predictions.map(point => point.ci_upper), mode: 'lines', name: 'Highest model', line: { color: themeColor('--accent-line', 'rgba(224,85,154,0.42)'), width: 1 }, hoverinfo: 'skip', showlegend: !!data.uncertainty_available },
      { x: predictions.map(point => point.hour_offset), y: predictions.map(point => point.ci_lower), mode: 'lines', name: 'Lowest model', line: { color: themeColor('--accent-line', 'rgba(224,85,154,0.42)'), width: 1 }, fill: 'tonexty', fillcolor: themeColor('--accent-soft', 'rgba(224,85,154,0.14)'), hoverinfo: 'skip', showlegend: !!data.uncertainty_available }
    ];
    const thresholds = data.thresholds || {};
    const shapes = [];
    if (Number.isFinite(thresholds.safe_max)) shapes.push({ type: 'line', x0: -24, x1: 24, y0: thresholds.safe_max, y1: thresholds.safe_max, line: { color: themeColor('--ok', '#6DB894'), dash: 'dot', width: 1 } });
    if (Number.isFinite(thresholds.danger_min)) shapes.push({ type: 'line', x0: -24, x1: 24, y0: thresholds.danger_min, y1: thresholds.danger_min, line: { color: themeColor('--bad', '#E0625A'), dash: 'dot', width: 1 } });
    const variableLabel = data.label || data.variable || activeRegVar;
    const grid = themeColor('--line', 'rgba(150,178,204,0.1)');
    const strong = themeColor('--line-strong', 'rgba(150,178,204,0.18)');
    const mono = themeColor('--font-mono', 'monospace');
    const narrow = plot.clientWidth > 0 && plot.clientWidth < 560;
    const coarse = window.matchMedia ? window.matchMedia('(pointer: coarse)').matches : false;
    // "Now" divides the hindcast from the forecast.
    shapes.push({ type: 'line', x0: 0, x1: 0, yref: 'paper', y0: 0, y1: 1, line: { color: strong, width: 1, dash: 'dash' } });
    window.Plotly.react(plot, traces, {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: themeColor('--text-2', '#A5B3C1'), family: themeColor('--font-ui', 'sans-serif'), size: 12 },
      autosize: true,
      margin: narrow ? { l: 44, r: 10, t: 28, b: 96 } : { l: 56, r: 20, t: 40, b: 46 },
      hovermode: 'x unified',
      hoverlabel: { bgcolor: themeColor('--surface-2', '#17232F'), bordercolor: strong, font: { color: themeColor('--text', '#E7ECF1'), family: themeColor('--font-ui', 'sans-serif') } },
      xaxis: { title: { text: 'Hours from now', font: { size: 11 } }, gridcolor: grid, zerolinecolor: strong, tickfont: { family: mono }, showspikes: true, spikemode: 'across', spikethickness: 1, spikecolor: strong, spikedash: 'solid' },
      yaxis: { title: { text: `${variableLabel} (${data.unit || ''})`, font: { size: 11 } }, gridcolor: grid, zerolinecolor: strong, tickfont: { family: mono }, rangemode: 'tozero' },
      shapes,
      annotations: [{ x: 0, y: 1, xref: 'x', yref: 'paper', text: 'Now', showarrow: false, yanchor: 'bottom', font: { size: 11, color: themeColor('--text-3', '#74808B'), family: mono } }],
      // On narrow screens the legend sits under the chart instead of over the lines.
      legend: narrow ? { orientation: 'h', y: -0.32, x: 0, font: { size: 10 } } : { orientation: 'h', y: 1.14, x: 0, font: { size: 11 } }
    }, { responsive: true, displaylogo: false, displayModeBar: !narrow && !coarse, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'] });
    const panel = document.getElementById('modelEvaluationPanel');
    if (panel) {
      const names = { nwp_24h_ahead: 'Model forecast (made 24 h earlier)', persistence: 'Persistence ("same as yesterday")', linear_trend: 'Straight-line trend' };
      const models = Object.entries(evaluation.models || {});
      const matrix = evaluation.confusion_matrix && evaluation.confusion_matrix.matrix;
      if (!models.length) {
        panel.innerHTML = `<p class="model-eval-note">${escapeHtml(evaluation.note || 'Verification unavailable.')}</p>`;
      } else {
        const best = models.reduce((a, b) => (Number(b[1].mae) < Number(a[1].mae) ? b : a))[0];
        const rows = models.map(([name, m]) => `
            <tr class="${name === best ? 'is-best' : ''}">
              <th scope="row">${escapeHtml(names[name] || name)}${name === best ? '<span class="eval-best">Lowest error</span>' : ''}</th>
              <td>${escapeHtml(String(m.mae))}</td><td>${escapeHtml(String(m.rmse))}</td><td>${escapeHtml(String(m.validation_size))} h</td>
            </tr>`).join('');
        const matrixRows = matrix ? Object.entries(matrix).map(([actual, v]) => `<tr><th scope="row">${escapeHtml(actual)}</th><td>${escapeHtml(String(v.safe ?? '-'))}</td><td>${escapeHtml(String(v.caution ?? '-'))}</td><td>${escapeHtml(String(v.danger ?? '-'))}</td></tr>`).join('') : '';
        panel.innerHTML = `
          <div class="eval-block">
            <h3>How the last 24 hours compared with ${escapeHtml(evaluation.truth_source || 'the hindcast')}</h3>
            <table class="eval-table"><thead><tr><th scope="col">Method</th><th scope="col">MAE</th><th scope="col">RMSE</th><th scope="col">Hours</th></tr></thead><tbody>${rows}</tbody></table>
          </div>
          ${matrixRows ? `<div class="eval-block">
            <h3>Safety bands: what happened vs what the model said</h3>
            <table class="eval-table"><thead><tr><th scope="col">Actual</th><th scope="col">Safe</th><th scope="col">Caution</th><th scope="col">Danger</th></tr></thead><tbody>${matrixRows}</tbody></table>
          </div>` : ''}`;
      }
    }
  }

  function drawRegressionCanvas() {
    const canvas = document.getElementById('regressionCanvas');
    const container = document.getElementById('graphCanvasContainer');
    if (!canvas || !container || !regressionDataCache) return;

    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w <= 0 || h <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;

    const ctx = canvas.getContext('2d');
    ctx.resetTransform();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const data = regressionDataCache;
    const th = data.thresholds || {};
    const cfg = { unit: data.unit || '', safeMax: Number(th.safe_max) || 1, dangerMin: Number(th.danger_min) || 2 };
    const history = data.history || [];
    const predictions = data.predictions || [];

    const padLeft = 55, padRight = 25, padTop = 30, padBottom = 40;
    const plotW = Math.max(10, w - padLeft - padRight);
    const plotH = Math.max(10, h - padTop - padBottom);

    const tMin = -24, tMax = 24;
    let yMinVal = 0, yMaxVal = Math.max(cfg.dangerMin * 1.25, 4.0);
    history.forEach(p => { if (p.value > yMaxVal) yMaxVal = p.value * 1.15; });
    predictions.forEach(p => { if (p.predicted_value > yMaxVal) yMaxVal = p.predicted_value * 1.15; });

    const toX = t => padLeft + ((t - tMin) / (tMax - tMin)) * plotW;
    const toY = val => padTop + plotH - ((val - yMinVal) / (yMaxVal - yMinVal)) * plotH;

    // Threshold bands
    const ySafe = toY(cfg.safeMax);
    const yDanger = toY(cfg.dangerMin);
    const yZero = toY(0);

    ctx.fillStyle = 'rgba(0, 245, 212, 0.05)';
    ctx.fillRect(padLeft, ySafe, plotW, yZero - ySafe);
    ctx.fillStyle = 'rgba(255, 51, 102, 0.08)';
    ctx.fillRect(padLeft, padTop, plotW, yDanger - padTop);

    // Grid lines
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.1)';
    ctx.fillStyle = '#8FA4BF';
    ctx.font = '10px "JetBrains Mono", monospace';

    for (let i = 0; i <= 4; i++) {
      const val = yMinVal + (i / 4) * (yMaxVal - yMinVal);
      const py = toY(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, py);
      ctx.lineTo(padLeft + plotW, py);
      ctx.stroke();
      ctx.fillText(`${val.toFixed(1)} ${cfg.unit}`, 8, py + 3);
    }

    // Historical Line
    ctx.strokeStyle = themeColor('--text-2', '#A5B3C1');
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    history.forEach((pt, i) => {
      const px = toX(pt.hour_offset);
      const py = toY(pt.value);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.stroke();

    // Regression Future Line
    ctx.strokeStyle = themeColor('--accent', '#E0559A');
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    predictions.forEach((pt, i) => {
      const px = toX(pt.hour_offset);
      const py = toY(pt.predicted_value);
      if (i === 0) ctx.moveTo(toX(0), toY(history[history.length - 1].value));
      ctx.lineTo(px, py);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Present marker
    const xNow = toX(0);
    ctx.strokeStyle = themeColor('--text-2', '#A5B3C1');
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(xNow, padTop);
    ctx.lineTo(xNow, padTop + plotH);
    ctx.stroke();

    ctx.fillStyle = themeColor('--text-2', '#A5B3C1');
    ctx.beginPath();
    ctx.arc(xNow, toY(history[history.length - 1].value), 5, 0, Math.PI * 2);
    ctx.fill();
  }

  function updateRegressionHUD() {
    if (!regressionDataCache) return;
    const d = regressionDataCache;
    const s = d.summary || {};
    const m = d.metrics || {};
    const p = d.predictions || [];
    const unit = d.unit || '';
    const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };

    setText('valBtmCurrent', `${Number(s.val_now ?? 0).toFixed(2)} ${unit}`);
    const p6 = p.find(pt => pt.hour_offset === 6);
    setText('valBtmMid', p6 ? `${Number(p6.predicted_value).toFixed(2)} ${unit}` : '--');
    setText('subBtmMid', p6 ? `${p6.delta_from_now >= 0 ? '+' : ''}${p6.delta_from_now} ${unit} vs now` : '--');
    setText('valBtmPeak', `${Number(s.peak_val ?? 0).toFixed(2)} ${unit}`);
    setText('subBtmPeak', s.peak_hour ? `around +${s.peak_hour} h (worst model)` : 'worst model');
    setText('txtRegEquation', m.mae !== null && m.mae !== undefined ? `${m.mae} ${unit}` : 'not verified');
    setText('txtRegR2', m.skill_vs_persistence !== null && m.skill_vs_persistence !== undefined ? Number(m.skill_vs_persistence).toFixed(2) : 'n/a');
    setText('txtRegAdvisoryBody', s.advisory_en || 'Forecast data is not available for this location.');
    const box = document.getElementById('boxRegAdvisory');
    if (box) box.className = `regression-advisory-box ${s.overall_status || 'safe'}`;
  }

  // 10. LANGUAGE & UTILITIES
  function setLanguage(lang) {
    currentLang = LANGUAGE_CODES.has(lang) ? lang : 'en';
    lang = currentLang;
    languageEpoch += 1;
    document.documentElement.lang = lang;
    localStorage.setItem('orca_marine_lang', lang);

    // Update main language buttons
    ['btnLangHI', 'btnLangEN', 'btnLangTA', 'btnLangMore'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('selected');
    });

    // Mark the matching shortcut button, or the "more" button for anything
    // beyond the HI/EN/TA shortcuts.
    const shortcutButton = { hi: 'btnLangHI', en: 'btnLangEN', ta: 'btnLangTA' }[lang];
    const activeButton = document.getElementById(shortcutButton || 'btnLangMore');
    if (activeButton) activeButton.classList.add('selected');

    const moreButton = document.getElementById('btnLangMore');
    if (moreButton) moreButton.textContent = shortcutButton ? '▼' : lang.toUpperCase();

    // Update expanded language dropdown buttons
    const langGridBtns = document.querySelectorAll('.lang-grid-btn');
    langGridBtns.forEach(btn => {
      btn.classList.remove('selected');
      if (btn.getAttribute('data-lang') === lang) {
        btn.classList.add('selected');
      }
    });

    // Use available translations or fallback to English
    const dict = I18N[lang] || I18N.en;
    const translatedElements = {
      txtHeroTagline: 'heroTagline', btnHeroExplore: 'heroExploreCta', btnHeroMap: 'heroMapCta',
      txtBridgeSubtitle: 'bridgeSubtitle', txtSunlightLabel: 'sunlight', txtViewPC: 'viewPC', txtViewPhone: 'viewPhone',
      txtLegendTitle: 'legendTitle', txtRegistryTitle: 'registryTitle',
      txtDrawerAsk: 'drawerAsk', txtDrawerDismiss: 'drawerDismiss', txtBriefBody: 'briefBody',
      txtMobChart: 'mobChart', txtMobMap: 'mobMap', txtMobAlerts: 'mobAlerts', txtMobSpecies: 'mobSpecies',
      txtMobGraph: 'mobGraph', txtMobChat: 'mobChat'
    };
    Object.entries(translatedElements).forEach(([id, key]) => {
      const element = document.getElementById(id);
      if (element && dict[key]) element.textContent = dict[key];
    });
    // Languages without a hand-written dictionary keep the English placeholder
    // until the translated one arrives.
    const input = document.getElementById('tacticalQueryInput');
    if (input && dict.inputPlaceholder) input.placeholder = dict.inputPlaceholder;
    const submit = document.querySelector('#btnSubmitQuery span');
    if (submit && dict.submitBtn) submit.textContent = dict.submitBtn;
    localizeInputPlaceholder(lang);
    [['btnFiltAll', 'filtAll'], ['btnFiltDanger', 'filtDanger'], ['btnFiltCaution', 'filtCaution'], ['btnFiltResolved', 'filtResolved']].forEach(([id, key]) => {
      // Only the label span: the chip also holds a colour dot and a live count.
      const element = document.getElementById(id);
      const label = element && (element.querySelector('.filt-label') || element);
      if (label && dict[key]) label.textContent = dict[key];
    });
    document.querySelectorAll('.sidebar-nav-btn').forEach((button) => {
      const key = `nav${button.dataset.view.charAt(0).toUpperCase()}${button.dataset.view.slice(1)}`;
      // Prefer the span carrying the label text; fall back to the first span so
      // buttons that also render a count badge are still translated.
      const label = button.querySelector(':scope > span:not(.nav-icon):not(.nav-badge):not([id^="sidebar"])')
        || button.querySelector(':scope > span:not(.nav-icon)');
      if (label && dict[key]) label.textContent = dict[key];
    });

    renderQuickQueries();
    renderSpeciesCatalog();
    renderLeafletTacticalZones();
    renderBulletinsList();
    applyTranslatedStaticText(lang);
    localizeDynamicContent(lang);
    localizeBriefBody(lang);
  }

  // Bulletins and advisories arrive in English from the backend. Translate the
  // rendered text once per language and cache it for later switches.
  async function localizeDynamicContent(lang, attempt = 0) {
    if (lang === 'en') return;
    window.clearTimeout(localizeDynamicContent.retry);
    // Bulletins arrive from the backend on a delay. Retry a few times so the
    // cards get localized once they actually exist in the DOM.
    const hasBulletins = document.querySelector('.bulletin-card');
    const nodes = Array.from(document.querySelectorAll(
      '.bulletin-title, .bulletin-desc, .bulletin-action-rec, .bulletin-action-bar .btn-bulletin-action, #txtDrawerReason, #txtRegAdvisoryBody, #drawerTitle'
    )).filter(node => {
      const text = (node.textContent || '').trim();
      return text.length > 1 && !/^\d+$/.test(text);
    });
    if (!nodes.length) return;

    const translated = await translateBatchForLanguage(
      nodes.map(node => node.textContent.trim()),
      lang
    );
      if (lang !== currentLang) return;
      nodes.forEach((node, index) => {
        const value = translated[index];
        if (value) node.textContent = value;
      });

        // First pass had no bulletins yet, so try again shortly to catch them.
        if (!hasBulletins && attempt < 4) {
          localizeDynamicContent.retry = window.setTimeout(() => {
            if (lang === currentLang) localizeDynamicContent(lang, attempt + 1);
          }, 2500);
        }
      }
    function renderLanguageOptions() {
    const container = document.querySelector('#expandedLangDropdown .lang-grid');
    if (!container) return;
    container.innerHTML = LANGUAGE_OPTIONS.map(option => (
      `<button class="lang-grid-btn" type="button" data-lang="${option.code}" title="${option.label}">${option.native}</button>`
    )).join('');
  }

  function renderQuickQueries() {
    const container = document.getElementById('quickQueriesRow');
    const cards = document.getElementById('chatSuggest');
    const dict = I18N[currentLang] || I18N.en;
    const queries = dict.queries || I18N.en.queries;
    const enQueries = I18N.en.queries;
    if (container) {
      container.innerHTML = queries.map(q =>
        `<button type="button" class="quick-query-pill" onclick="window.orcaQuickQuery('${escapeHtml(q.query)}')">${escapeHtml(q.label)}</button>`
      ).join('');
    }
    if (cards) {
      cards.innerHTML = queries.map((q, i) => {
        const base = enQueries[i] || {};
        return `<button type="button" class="chat-suggest-card" style="--i:${i}" onclick="window.orcaQuickQuery('${escapeHtml(q.query)}')">
            <span class="sg-icon"><i class="ph ph-${escapeHtml(q.icon || base.icon || 'chat-circle-text')} icon" aria-hidden="true"></i></span>
            <span class="sg-label">${escapeHtml(q.label)}</span>
            <span class="sg-hint">${escapeHtml(q.hint || base.hint || '')}</span>
          </button>`;
      }).join('');
    }
    // Languages without a hand-written dictionary keep the English prompt that
    // gets sent to the backend, but their visible labels are translated.
    localizeQuickQueryLabels(currentLang);
  }

  async function localizeInputPlaceholder(lang) {
    const input = document.getElementById('tacticalQueryInput');
    if (!input || lang === 'en' || (I18N[lang] && I18N[lang].inputPlaceholder)) return;
    const original = input.getAttribute('data-original-placeholder') || input.placeholder;
    if (!original) return;
    input.setAttribute('data-original-placeholder', original);
    const translated = await translateForLanguage(original, lang);
    if (lang !== currentLang) return;
    input.placeholder = translated || original;
  }

  async function localizeQuickQueryLabels(lang) {
    if (lang === 'en' || (I18N[lang] && I18N[lang].queries)) return;
    const labels = Array.from(document.querySelectorAll('#quickQueriesRow .quick-query-pill, #chatSuggest .sg-label, #chatSuggest .sg-hint'));
    if (!labels.length) return;
    const translated = await translateBatchForLanguage(
      labels.map(button => button.textContent.trim()),
      lang
    );
    if (lang !== currentLang) return;
    labels.forEach((button, index) => {
      if (translated[index]) button.textContent = translated[index];
    });
  }

  // Languages without a hand-written brief get the English text machine-translated.
  async function localizeBriefBody(lang) {
    const el = document.getElementById('txtBriefBody');
    if (!el || (I18N[lang] && I18N[lang].briefBody)) return;
    const english = I18N.en.briefBody;
    el.textContent = english;
    if (lang === 'en') return;
    const translated = await translateForLanguage(english, lang);
    if (lang === currentLang && translated) el.textContent = translated;
  }

  window.orcaQuickQuery = function(queryText) {
    const input = document.getElementById('tacticalQueryInput');
    if (input) input.value = queryText;
    triggerTacticalQuery(queryText);
  };

  // Pick the best available localized field (``name_hi`` / ``label_ta``...).
  // Hand-written hi/ta strings win; every other language falls back to English
  // and is translated later by localizeDynamicContent().
  function languageValue(record, prefix, lang) {
    if (!record) return '';
    if (lang === 'hi') return record[`${prefix}_hi`] || record[`${prefix}_en`] || '';
    if (lang === 'ta') return record[`${prefix}_ta`] || record[`${prefix}_en`] || '';
    return record[`${prefix}_en`] || '';
  }

  // Look up one translated UI string, falling back to English.
  function t(key, fallback) {
    const dict = I18N[currentLang];
    return (dict && dict[key]) || fallback;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function formatMarkdown(str) {
    if (!str) return '';
    return escapeHtml(str).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }

  function speakerButtonMarkup(text) {
    const label = escapeHtml(t('chatSpeak', 'Speak this response'));
    return `<button type="button" class="chat-speak-btn" data-speak-text="${escapeHtml(String(text).replace(/[*_`#]/g, ''))}" data-speak-lang="${speechLanguage(currentLang)}" title="${label}" aria-label="${label}"><i class="ph ph-speaker-high icon" aria-hidden="true"></i>Listen</button>`;
  }

  // Translation cache: repeated strings (quick queries, advisories, static
  // labels) are only ever sent to the backend once per language.
  const translationCache = new Map();

  function translationCacheKey(lang, text) {
    return `${lang}\u0000${text}`;
  }

  // Translate a batch of strings in one request. Rejections are swallowed so a
  // translation outage can never break the dashboard.
  async function translateBatchForLanguage(texts, lang) {
    if (!texts || !texts.length || lang === 'en') return [];
    try {
      const response = await fetch(`${BACKEND_API_BASE}/translate/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texts, target_lang: lang, source_lang: 'en' })
      });
      if (!response.ok) throw new Error(`Translation request failed (${response.status})`);
      const data = await response.json();
      if (Array.isArray(data.translations)) {
        data.translations.forEach((entry, index) => {
          if (entry && entry.success && entry.translated_text) {
            translationCache.set(translationCacheKey(lang, texts[index]), entry.translated_text);
          }
        });
      }
    } catch (error) {
      console.warn('Batch translation failed:', error);
    }
    return texts.map(text => translationCache.get(translationCacheKey(lang, text)) || text);
  }

  async function translateForLanguage(text, lang) {
    if (!text || lang === 'en') return text;
    const cacheKey = translationCacheKey(lang, text);
    if (translationCache.has(cacheKey)) return translationCache.get(cacheKey);

    // Single strings go through the same endpoint so they share the cache and
    // the failure handling with batched translations.
    const [translated] = await translateBatchForLanguage([text], lang);
    return translated || text;
  }

  // Strip leading emoji/pictographs so "🌊 Ocean Health" still matches the
  // English string "Ocean Health".
  function labelWithoutLeadingSymbols(text) {
    return String(text || '').replace(/^[^\p{L}\p{N}]+/u, '').trim();
  }

  function isTranslatableStaticLabel(text) {
    const bare = labelWithoutLeadingSymbols(text);
    return Boolean(bare) && TRANSLATABLE_STATIC_TEXT.some(
      candidate => bare === candidate || bare.startsWith(candidate)
    );
  }

  // Refresh dashboard labels that only exist in English in the markup.
  async function applyTranslatedStaticText(lang) {
    if (lang === 'en') return;
    const wanted = new Map();
    document.querySelectorAll(STATIC_TEXT_TARGETS).forEach(element => {
      const text = (element.textContent || '').trim();
      if (!text || wanted.has(text) || text.length > 70) return;
      if (!isTranslatableStaticLabel(text)) return;
      wanted.set(text, element);
    });
    if (!wanted.size) return;

    const translated = await translateBatchForLanguage(Array.from(wanted.keys()), lang);
    if (lang !== currentLang) return;
    Array.from(wanted.values()).forEach((element, index) => {
      const value = translated[index];
      if (!value) return;
      // Never overwrite a badge that holds a computed count (e.g. "2 NEW").
      if (element.classList.contains('nav-badge') && /^\d/.test(value)) return;
      if (value !== element.textContent.trim()) element.textContent = value;
    });
  }

  // Keep the interface in step with the stored language when the pilot moves
  // between pages (the dashboard and the Alerts view share one preference).
  function initLanguageSync() {
    window.addEventListener('storage', (event) => {
      if (event.key !== 'orca_marine_lang' || !event.newValue) return;
      if (event.newValue !== currentLang) setLanguage(event.newValue);
    });
    window.addEventListener('focus', () => {
      const stored = localStorage.getItem('orca_marine_lang');
      if (stored && stored !== currentLang) setLanguage(stored);
    });
  }

  // Master Initialization
  function initDashboard() {
    initVoiceRecognition();
    initLanguageSync();
    setLanguage(currentLang);
    // Initial live feed load. Risk cells are returned by the backend rather
    // than fabricated around the default location.
    fetchLiveTelemetry(vesselLocation.latitude, vesselLocation.longitude);
    fetchLiveBulletins(vesselLocation.latitude, vesselLocation.longitude);
    fetchEcosystem(vesselLocation.latitude, vesselLocation.longitude);
    if (isHeatmapActive) fetchRiskHeatmap(vesselLocation.latitude, vesselLocation.longitude);
    updateGpsButton();
    // Upstream models update hourly and the backend caches for 10-15 min, so
    // polling every 2 minutes is plenty (5 s polling caused rate limiting).
    telemetryTimer = window.setInterval(() => {
      if (document.hidden || !vesselLocation) return;
      const { latitude, longitude } = vesselLocation;
      fetchLiveTelemetry(latitude, longitude);
      fetchLiveBulletins(latitude, longitude);
      if (isHeatmapActive) fetchRiskHeatmap(latitude, longitude);
    }, 120000);
    initSpeciesToolbar();
    renderSpeciesCatalog();
    loadRegressionData('wave_height');
    initRoutePlanner();
    if (currentActiveView === 'dashboard') initLeafletMap();
    const chatPlace = document.getElementById('chatPlace');
    if (chatPlace) chatPlace.textContent = vesselLocation.name;
    const changePlace = document.getElementById('btnChatChangePlace');
    if (changePlace) changePlace.addEventListener('click', () => {
      window.location.hash = 'map';
      setTimeout(() => { const box = document.getElementById('inputCustomLocation'); if (box) box.focus(); }, 300);
    });
    const verdictAsk = document.getElementById('btnVerdictAsk');
    if (verdictAsk) verdictAsk.addEventListener('click', () => {
      switchActiveView('chat');
      triggerTacticalQuery('Is it safe to go fishing here today, and why?');
    });
    const verdictRoute = document.getElementById('btnVerdictRoute');
    if (verdictRoute) verdictRoute.addEventListener('click', () => {
      switchActiveView('map');
      const body = document.getElementById('routePlannerBody');
      if (body) body.hidden = false;
      const to = document.getElementById('inputRouteTo');
      if (to) setTimeout(() => to.focus(), 200);
    });

    // Deep links: index.html#map, #chat, #alerts, #species, #analytics
    const VIEWS = ['dashboard', 'map', 'alerts', 'species', 'analytics', 'chat'];
    const fromHash = () => { const v = (window.location.hash || '').replace('#', ''); if (VIEWS.includes(v)) switchActiveView(v); };
    window.addEventListener('hashchange', fromHash);
    fromHash();

    // Sidebar navigation clicks
    document.querySelectorAll('.sidebar-nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-view');
        if (view) switchActiveView(view);
      });
    });

    // Mobile dock clicks
    document.querySelectorAll('.mobile-dock-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-view');
        if (view) switchActiveView(view);
      });
    });

    // Quick port chips
    document.querySelectorAll('.loc-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const locKey = chip.getAttribute('data-loc').toLowerCase();
        const port = MARITIME_PORTS_CATALOG[locKey];
        if (port && leafletMap) {
          stopGpsTracking();
          updateLocation(port.lat, port.lon, port.name, 'manual');
        }
      });
    });

    // GPS and location controls
    const gpsToggle = document.getElementById('btnGpsToggle');
    if (gpsToggle) gpsToggle.addEventListener('click', () => isGpsTrackingEnabled ? stopGpsTracking() : startGpsTracking());
    const gpsLocate = document.getElementById('btnCurrentGpsLocation');
    if (gpsLocate) gpsLocate.addEventListener('click', startGpsTracking);
    const locationInput = document.getElementById('inputCustomLocation');
    const submitLocation = async () => {
      const resolved = await resolveLocationAnywhere(locationInput && locationInput.value);
      if (!resolved) {
        window.alert('Location not found. Try a port or town name (e.g. "Chennai", "Durban") or coordinates such as "15.24, 73.80" or "33.9S 18.4E".');
        return;
      }
      stopGpsTracking();
      updateLocation(resolved.lat, resolved.lon, resolved.name, 'manual');
      if (locationInput) locationInput.value = '';
    };
    const submitLocationButton = document.getElementById('btnSubmitLocation');
    if (submitLocationButton) submitLocationButton.addEventListener('click', submitLocation);
    if (locationInput) locationInput.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); submitLocation(); } });
    const clearLocation = document.getElementById('btnClearLocSearch');
    if (clearLocation) clearLocation.addEventListener('click', () => { if (locationInput) locationInput.value = ''; });

    // Query Form
    const queryForm = document.getElementById('tacticalQueryForm');
    if (queryForm) {
      queryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('tacticalQueryInput');
        if (input && input.value.trim()) triggerTacticalQuery(input.value.trim());
      });
    }

    // Voice button
    const voiceBtn = document.getElementById('btnVoiceCommand');
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        if (isListening) stopVoiceListening();
        else startVoiceListening();
      });
    }

    // Heatmap button toggle
    const btnHeatmap = document.getElementById('btnToggleHeatmap');
    if (btnHeatmap) {
      btnHeatmap.addEventListener('click', () => {
        isHeatmapActive = !isHeatmapActive;
        localStorage.setItem('orca_marine_heatmap', isHeatmapActive);
        updateHeatmapVisuals();
      });
    }

    // Legend Toggle
    const btnLegend = document.getElementById('btnToggleLegend');
    const pnlLegend = document.getElementById('chartLegendPanel');
    if (btnLegend && pnlLegend) {
      btnLegend.addEventListener('click', () => {
        pnlLegend.classList.toggle('collapsed');
      });
    }

    // Language Selector
    renderLanguageOptions();
    const btnHi = document.getElementById('btnLangHI');
    const btnEn = document.getElementById('btnLangEN');
    const btnTa = document.getElementById('btnLangTA');
    const btnLangMore = document.getElementById('btnLangMore');
    const expandedLangDropdown = document.getElementById('expandedLangDropdown');

    if (btnHi) btnHi.addEventListener('click', () => setLanguage('hi'));
    if (btnEn) btnEn.addEventListener('click', () => setLanguage('en'));
    if (btnTa) btnTa.addEventListener('click', () => setLanguage('ta'));

    // Toggle expanded language dropdown
    if (btnLangMore && expandedLangDropdown) {
      btnLangMore.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        const isHidden = expandedLangDropdown.style.display === 'none' || expandedLangDropdown.style.display === '';
        expandedLangDropdown.style.display = isHidden ? 'block' : 'none';
      });

      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!expandedLangDropdown.contains(e.target) && e.target !== btnLangMore && !btnLangMore.contains(e.target)) {
          expandedLangDropdown.style.display = 'none';
        }
      });

      // Handle language grid button clicks
      const langGridBtns = expandedLangDropdown.querySelectorAll('.lang-grid-btn');
      langGridBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const langCode = btn.getAttribute('data-lang');
          setLanguage(langCode);
          expandedLangDropdown.style.display = 'none';
        });
      });
    }

    document.addEventListener('click', (event) => {
      const button = event.target.closest('.chat-speak-btn');
      if (!button) return;
      speakText(button.dataset.speakText || '', button.dataset.speakLang || speechLanguage(currentLang));
      document.querySelectorAll('.chat-speak-btn.speaking').forEach((item) => item.classList.remove('speaking'));
      button.classList.add('speaking');
    });

    // Sunlight deck toggle
    const btnSunlight = document.getElementById('btnSunlightToggle');
    if (btnSunlight) {
      btnSunlight.addEventListener('click', () => {
        const light = document.body.classList.toggle('deck-sunlight');
        try { localStorage.setItem('orca_theme', light ? 'light' : 'dark'); } catch (e) {}
        // Charts and map layers read colours from CSS variables; redraw them.
        if (regressionDataCache) drawRegressionPlotly();
        if (isHeatmapActive && vesselLocation) fetchRiskHeatmap(vesselLocation.latitude, vesselLocation.longitude);
      });
    }

    // Dismiss drawer
    const btnDismiss = document.getElementById('btnDismissDrawer');
    if (btnDismiss) btnDismiss.addEventListener('click', closeTacticalDrawer);

    // Hero CTAs
    const btnExplore = document.getElementById('btnHeroExplore');
    if (btnExplore) btnExplore.addEventListener('click', () => switchActiveView('dashboard'));
    const btnHeroMap = document.getElementById('btnHeroMap');
    if (btnHeroMap) btnHeroMap.addEventListener('click', () => switchActiveView('map'));
    const recalc = document.getElementById('btnRecalcRegression');
    if (recalc) recalc.addEventListener('click', () => loadRegressionData(activeRegVar));

    // Fetch the chart library once the page is idle, so Forecast opens ready.
    const prefetchPlotly = () => ensurePlotly().then(() => { if (regressionDataCache) drawRegressionPlotly(); }).catch(() => {});
    const whenIdle = cb => (window.requestIdleCallback ? window.requestIdleCallback(cb, { timeout: 4000 }) : window.setTimeout(cb, 1500));
    if (document.readyState === 'complete') whenIdle(prefetchPlotly);
    else window.addEventListener('load', () => whenIdle(prefetchPlotly), { once: true });

    // Master Clock
    setInterval(() => {
      const clock = document.getElementById('bridgeMasterClock');
      if (clock) {
        const now = new Date();
        const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').split('/').pop().replace('_', ' ');
        clock.textContent = `${now.toTimeString().slice(0, 5)} ${tz} · ${now.toISOString().slice(11, 16)} UTC`;
      }
    }, 1000);
  }

  // Text-to-Speech Functionality
  let speechSynthesis = window.speechSynthesis;
  let currentUtterance = null;

  function speakText(text, lang = 'en-US') {
    if (!text || !speechSynthesis) return;

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Prefer a voice for the selected language. The utterance language is
    // retained even when a platform only exposes a regional/alias voice.
    const voices = speechSynthesis.getVoices();
    const candidates = speechLanguageCandidates(lang).map(value => value.toLowerCase());
    const matchingVoice = voices.find(voice => {
      const voiceLang = String(voice.lang || '').toLowerCase();
      return candidates.some(candidate => voiceLang === candidate || voiceLang.startsWith(`${candidate}-`));
    }) || voices.find(voice => {
      const voiceLang = String(voice.lang || '').toLowerCase();
      const languageCode = String(lang).toLowerCase().split('-')[0];
      return voiceLang.startsWith(`${languageCode}-`) || voiceLang === languageCode;
    });
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    currentUtterance = utterance;
    speechSynthesis.speak(utterance);
  }

  // Use BCP-47 tags that browser speech engines commonly expose. Some of the
  // official language codes do not have a matching regional voice on every
  // platform, so the aliases below let us select the closest script voice
  // without changing the language of the text being spoken.
  const SPEECH_LANGUAGE_ALIASES = {
    en: ['en-US', 'en-GB'],
    as: ['as-IN'],
    bn: ['bn-IN', 'bn-BD'],
    brx: ['brx-IN', 'hi-IN'],
    doi: ['doi-IN', 'hi-IN'],
    gu: ['gu-IN'],
    hi: ['hi-IN'],
    kn: ['kn-IN'],
    ks: ['ks-IN', 'hi-IN'],
    kok: ['kok-IN'],
    mai: ['mai-IN', 'hi-IN'],
    ml: ['ml-IN'],
    mni: ['mni-IN'],
    mr: ['mr-IN'],
    ne: ['ne-IN', 'ne-NP'],
    or: ['or-IN'],
    pa: ['pa-IN'],
    sa: ['sa-IN', 'hi-IN'],
    sat: ['sat-IN'],
    sd: ['sd-IN'],
    ta: ['ta-IN'],
    te: ['te-IN'],
    ur: ['ur-IN', 'ur-PK']
  };

  function speechLanguage(lang) {
    const code = String(lang || 'en').toLowerCase().split('-')[0];
    return (SPEECH_LANGUAGE_ALIASES[code] || [`${code}-IN`])[0];
  }

  function speechLanguageCandidates(lang) {
    const code = String(lang || 'en').toLowerCase().split('-')[0];
    return SPEECH_LANGUAGE_ALIASES[code] || [`${code}-IN`];
  }

  function stopSpeech() {
    if (speechSynthesis) {
      speechSynthesis.cancel();
    }
  }

  // Load voices when they become available
  if (speechSynthesis) {
    speechSynthesis.onvoiceschanged = () => {
      speechSynthesis.getVoices();
    };
  }

  // Initialize only after the speech-language aliases are defined. Voice
  // recognition uses speechLanguage() during startup.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }

  // 11. SAFE ROUTE PLANNER
  function initRoutePlanner() {
    const toggle = document.getElementById('btnRouteToggle');
    const body = document.getElementById('routePlannerBody');
    const btn = document.getElementById('btnPlanRoute');
    if (toggle && body) toggle.addEventListener('click', () => { body.hidden = !body.hidden; });
    if (btn) btn.addEventListener('click', planSafeRoute);
  }

  async function planSafeRoute() {
    const out = document.getElementById('routeResult');
    const fromRaw = (document.getElementById('inputRouteFrom') || {}).value || '';
    const toRaw = (document.getElementById('inputRouteTo') || {}).value || '';
    const vessel = (document.getElementById('selectRouteVessel') || {}).value || 'small';
    const show = html => { if (out) out.innerHTML = html; };
    if (!toRaw.trim()) { show('<p class="route-error">Enter a destination.</p>'); return; }
    show('<p>Resolving places…</p>');
    const from = fromRaw.trim() ? await resolveLocationAnywhere(fromRaw) : { lat: vesselLocation.latitude, lon: vesselLocation.longitude, name: vesselLocation.name };
    const to = await resolveLocationAnywhere(toRaw);
    if (!from || !to) { show('<p class="route-error">Could not find the start or destination.</p>'); return; }
    show('<p>Checking forecast along possible routes…</p>');
    try {
      const res = await fetch(`${BACKEND_API_BASE}/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_latitude: from.lat, start_longitude: from.lon, end_latitude: to.lat, end_longitude: to.lon, vessel })
      });
      const data = await res.json();
      if (!res.ok) { show(`<p class="route-error">${escapeHtml(data.detail || 'Route planning failed.')}</p>`); return; }
      drawRoute(data);
      const cls = { DIRECT_OK: 'ok', DETOUR: 'detour', NO_SAFE_ROUTE: 'blocked' }[data.verdict] || '';
      const rc = data.route_conditions || {};
      show(`
        <div class="route-verdict ${cls}">${escapeHtml(data.verdict.replace(/_/g, ' '))}</div>
        <p>${escapeHtml(data.summary)}</p>
        <p class="route-stats">${data.distance_nm} NM • ~${data.eta_hours} h at ${data.vessel.speed_kt} kt • max waves ${rc.max_wave_m ?? '-'} m • max wind ${rc.max_wind_kt ?? '-'} kt</p>
        <p class="route-limits">${escapeHtml(data.limitations)}</p>`);
    } catch (e) {
      show('<p class="route-error">Route service unreachable.</p>');
    }
  }

  function drawRoute(data) {
    if (!leafletMap) { switchActiveView('map', { instant: true }); }
    if (!leafletMap || !routeLayer) return;
    routeLayer.clearLayers();
    const pts = (data.waypoints || []).map(w => [w.latitude, w.longitude]);
    if (pts.length < 2) return;
    const color = data.verdict === 'NO_SAFE_ROUTE' ? themeColor('--bad', '#E0625A') : (data.verdict === 'DETOUR' ? themeColor('--warn', '#E2944F') : themeColor('--ok', '#6DB894'));
    L.polyline(pts, { color, weight: 4, opacity: 0.9, dashArray: data.verdict === 'NO_SAFE_ROUTE' ? '8 6' : null }).addTo(routeLayer);
    pts.forEach((p, i) => {
      const label = i === 0 ? 'Start' : (i === pts.length - 1 ? 'Destination' : `Waypoint ${i}`);
      L.circleMarker(p, { radius: i === 0 || i === pts.length - 1 ? 7 : 4, color: '#fff', weight: 1.5, fillColor: color, fillOpacity: 1 })
        .bindTooltip(`${label}: ${formatCoord(p[0], p[1], 3)}`, { direction: 'top' }).addTo(routeLayer);
    });
    leafletMap.fitBounds(L.latLngBounds(pts).pad(0.2));
  }

  window.ORCA = {
    apiBase: BACKEND_API_BASE,
    getLocation: () => (vesselLocation ? { latitude: vesselLocation.latitude, longitude: vesselLocation.longitude, name: vesselLocation.name } : null),
    switchActiveView,
    setLanguage,
    triggerTacticalQuery,
    loadRegressionData,
    startGpsTracking,
    stopGpsTracking,
    updateLocation,
    speakText,
    stopSpeech
  };
})();
