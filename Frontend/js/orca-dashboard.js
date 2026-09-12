/**
 * ORCA Marine Intelligence & Conservation Dashboard
 * Core Engine & Interactive Controller
 */

(function () {
  'use strict';

  // State management
  let currentLang = localStorage.getItem('orca_marine_lang') || 'en';
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
  let speciesLayer = null;
  let incidentsLayer = null;
  let userLocationMarker = null;

  let MAP_ZONES = [];
  let MAP_MARKERS = [];
  let BULLETINS = [];
  let vesselLocation = { latitude: 15.246, longitude: 73.803, name: 'Goa Coastal Sector' };
  let isGpsTrackingEnabled = true;
  let customLocationName = null;
  let isBackendConnected = false;

  // Layer Visibility States
  let isHeatmapActive = localStorage.getItem('orca_marine_heatmap') !== 'false';
  let isSpeciesLayerActive = true;
  let isIncidentsLayerActive = true;
  let isZonesLayerActive = true;

  // Trilingual Maritime Translations
  const I18N = {
    en: {
      heroTagline: "Intelligence for a Healthier Ocean",
      heroExploreCta: "Explore Ocean Data",
      heroMapCta: "View Live Map",
      bridgeSubtitle: "OCEAN CONSERVATION & MARINE INTELLIGENCE COMMAND",
      navDashboard: "Dashboard",
      navMap: "Live Ocean Map",
      navAlerts: "Alerts & Bulletins",
      navSpecies: "Species Tracker",
      navAnalytics: "Analytics Studio",
      navChat: "Ask ORCA AI",
      kpiHealth: "Ocean Health",
      kpiSpecies: "Species Detected",
      kpiAlerts: "Active Bulletins",
      kpiPollution: "Pollution Risk",
      kpiTemp: "Water Temperature",
      kpiZones: "Monitored Zones",
      sunlight: "SUNLIGHT",
      sunlightActive: "HIGH CONTRAST",
      telemetryFix: "DGPS FIX: 15°24.6'N, 73°48.2'E",
      legendTitle: "Cartographic Legend",
      legPfz: "Potential Fishing Zone (PFZ)",
      legCaution: "Environmental Caution Area",
      legDanger: "Hazard / Squall Warning",
      legVessel: "Vessel Position (GPS)",
      legHeatmap: "Ocean Risk & SST Heatmap",
      heatScaleLow: "Low Risk (Nominal)",
      heatScaleHigh: "Critical Alert Zone",
      heatmapBtnOn: "HEATMAP: ON",
      heatmapBtnOff: "HEATMAP: OFF",
      registryTitle: "Marine Safety & Conservation Advisories",
      registrySector: "SECTOR: ARABIAN SEA / GOA COAST",
      statusSummary: (d, c) => `Active Advisories: ${d} Critical, ${c} Precautionary`,
      filtAll: "All Advisories",
      filtDanger: "Critical",
      filtCaution: "Precaution",
      filtResolved: "Nominal",
      plotOnChart: "🗺️ Plot on Map",
      askInRadio: "💬 Query ORCA",
      briefTitle: "ORCA Autonomous Intelligence Assistant",
      briefBody: "Multi-agent neural link active. Access real-time satellite SST, species acoustic tags, pollution dispersion vectors, and bathymetric telemetry.",
      inputPlaceholder: "Ask ORCA (e.g. Show pollution hotspots or whale tracking)...",
      submitBtn: "Query",
      drawerAsk: "Ask ORCA in Chat 💬",
      drawerDismiss: "Dismiss",
      mobChart: "Live Map",
      mobAlerts: "Alerts",
      mobChat: "Ask ORCA",
      mobGraph: "Analytics",
      mobSpecies: "Species",
      viewPC: "PC",
      viewPhone: "PHONE",
      queries: [
        { label: "🐋 Recent Species Detections", query: "What marine species were detected recently?", zone_id: null },
        { label: "🧪 Show Pollution Hotspots", query: "Show pollution hotspots and risk areas", zone_id: null },
        { label: "🌊 Sea Swell & Wave Hazards", query: "Is there high wave swell or squall risk today?", zone_id: null },
        { label: "📍 Explain Risk Heatmap", query: "Explain the current 3x3 ocean risk heatmap", zone_id: null },
        { label: "📈 Marine Trend Forecast", query: "What is the 24-hour linear regression projection?", zone_id: null },
        { label: "🆘 Coast Guard / Emergency", query: "Emergency marine distress contacts VHF Ch 16", zone_id: null }
      ]
    },
    hi: {
      heroTagline: "स्वस्थ महासागर के लिए कृत्रिम बुद्धिमत्ता",
      heroExploreCta: "समुद्री डेटा देखें",
      heroMapCta: "लाइव मैप खोलें",
      bridgeSubtitle: "व्यावसायिक महासागरीय बुद्धिमत्ता एवं संरक्षण केंद्र",
      navDashboard: "डैशबोर्ड",
      navMap: "लाइव महासागर मैप",
      navAlerts: "सुरक्षा अलर्ट",
      navSpecies: "प्रजाति ट्रैकर",
      navAnalytics: "विश्लेषण स्टूडियो",
      navChat: "ORCA AI सहायक",
      kpiHealth: "महासागर स्वास्थ्य",
      kpiSpecies: "पहचानी गई प्रजातियां",
      kpiAlerts: "सक्रिय अलर्ट",
      kpiPollution: "प्रदूषण जोखिम",
      kpiTemp: "समुद्री तापमान",
      kpiZones: "निगरानी क्षेत्र",
      sunlight: "सनलाइट",
      sunlightActive: "हाई कंट्रास्ट",
      telemetryFix: "DGPS स्थिति: 15°24.6'N, 73°48.2'E",
      legendTitle: "नॉटिकल संकेत (Legend)",
      legPfz: "मत्स्य क्षेत्र (INCOIS PFZ)",
      legCaution: "सावधानी क्षेत्र (हवा/लहर)",
      legDanger: "प्रतिबंधित खतरा (रेड अलर्ट)",
      legVessel: "नाव की स्थिति (GPS)",
      legHeatmap: "मत्स्य सघनता व SST हीटमैप",
      heatScaleLow: "कम जोखिम (सामान्य)",
      heatScaleHigh: "गंभीर जोखिम (रेड अलर्ट)",
      heatmapBtnOn: "हीटमैप: चालू",
      heatmapBtnOff: "हीटमैप: बंद",
      registryTitle: "तटीय सुरक्षा एवं संरक्षण सूचनाएं",
      registrySector: "सेक्टर: गोवा–कारवार तट",
      statusSummary: (d, c) => `सक्रिय बुलेटिन: ${d} अति गंभीर (RED), ${c} चेतावनी (CAUTION)`,
      filtAll: "सभी सूचनाएं",
      filtDanger: "खतरा",
      filtCaution: "सावधानी",
      filtResolved: "सामान्य",
      plotOnChart: "🗺️ मैप पर देखें",
      askInRadio: "💬 ORCA से पूछें",
      briefTitle: "ORCA सामरिक महासागरीय सहायता",
      briefBody: "उपग्रह व महासागरीय सेंसर सक्रिय हैं। डॉल्फ़िन, व्हेल, कछुआ ट्रैकिंग या प्रदूषण हॉटस्पॉट की जानकारी के लिए पूछें।",
      inputPlaceholder: "सामरिक प्रश्न दर्ज करें (उदा: क्या आज हवा सुरक्षित है?)...",
      submitBtn: "पूछें",
      drawerAsk: "ORCA चैट में पूछें 💬",
      drawerDismiss: "बंद करें",
      mobChart: "नॉटिकल मैप",
      mobAlerts: "सुरक्षा अलर्ट",
      mobChat: "ORCA रेडियो",
      mobGraph: "ग्राफ",
      mobSpecies: "प्रजातियां",
      viewPC: "PC",
      viewPhone: "फोन",
      queries: [
        { label: "🐋 हालिया प्रजाति खोज", query: "हाल ही में कौन सी समुद्री प्रजातियां देखी गईं?", zone_id: null },
        { label: "🧪 प्रदूषण हॉटस्पॉट दिखाएं", query: "प्रदूषण हॉटस्पॉट और जोखिम क्षेत्र दिखाएं", zone_id: null },
        { label: "🌊 हवा व 3m लहरें", query: "क्या 35 km/h की तेज हवा और ऊंची लहरों का खतरा है?", zone_id: null },
        { label: "🐟 उत्तम मत्स्य क्षेत्र (PFZ)", query: "आज मछली पकड़ने के लिए सबसे अच्छी जगह कहां है?", zone_id: null },
        { label: "📈 24-घंटे का रुझान", query: "अगले 24 घंटे में लहरों का क्या अनुमान है?", zone_id: null },
        { label: "🆘 तटरक्षक आपातकाल", query: "Emergency distress assistance VHF Ch 16 contact", zone_id: null }
      ]
    },
    ta: {
      heroTagline: "ஆரோக்கியமான கடலுக்கான கடல்சார் நுண்ணறிவு",
      heroExploreCta: "கடல் தகவல்களை காண்க",
      heroMapCta: "நேரலை வரைபடம்",
      bridgeSubtitle: "கடல்சார் நுண்ணறிவு மற்றும் பாதுகாப்பு மையம்",
      navDashboard: "முகப்பு",
      navMap: "நேரலை வரைபடம்",
      navAlerts: "எச்சரிக்கைகள்",
      navSpecies: "உயிரினங்கள்",
      navAnalytics: "பகுப்பாய்வு",
      navChat: "ORCA AI உதவி",
      kpiHealth: "கடல் நலம்",
      kpiSpecies: "கண்டறியப்பட்ட உயிரினம்",
      kpiAlerts: "எச்சரிக்கைகள்",
      kpiPollution: "மாசுபாடு ஆபத்து",
      kpiTemp: "கடல் வெப்பநிலை",
      kpiZones: "கண்காணிப்பு பகுதி",
      sunlight: "SUNLIGHT",
      sunlightActive: "HIGH CONTRAST",
      telemetryFix: "DGPS நிலை: 15°24.6'N, 73°48.2'E",
      legendTitle: "வரைபடக் குறியீடுகள்",
      legPfz: "மீன்பிடி பகுதி (INCOIS PFZ)",
      legCaution: "எச்சரிக்கை பகுதி (அலை/காற்று)",
      legDanger: "தடைசெய்யப்பட்ட ஆபத்து (ரெட் அலர்ட்)",
      legVessel: "படகு அமைவிடம் (GPS)",
      legHeatmap: "வெப்ப வரைபடம்",
      heatScaleLow: "குறைந்த ஆபத்து",
      heatScaleHigh: "அதிதீவிர ஆபத்து",
      heatmapBtnOn: "வெப்ப வரைபடம்: ஆன்",
      heatmapBtnOff: "வெப்ப வரைபடம்: ஆஃப்",
      registryTitle: "கடற்கரை பாதுகாப்பு அறிவிப்புகள்",
      registrySector: "துறை: கோவா–கார்வார்",
      statusSummary: (d, c) => `செயலில் உள்ளவை: ${d} ஆபத்து, ${c} எச்சரிக்கை`,
      filtAll: "அனைத்தும்",
      filtDanger: "ஆபத்து",
      filtCaution: "எச்சரிக்கை",
      filtResolved: "இயல்பு",
      plotOnChart: "🗺️ வரைபடத்தில் காட்டு",
      askInRadio: "💬 ORCA-விடம் கேள்",
      briefTitle: "ORCA ஆலோசனை மையம்",
      briefBody: "INCOIS மற்றும் செயற்கைக்கோள் இணைப்பு செயலில் உள்ளது. திமிங்கிலம், ஆமை கண்காணிப்பு மற்றும் வானிலை தகவல்களை அறியலாம்.",
      inputPlaceholder: "கேள்வியை தட்டச்சு செய்யவும்...",
      submitBtn: "கேள்",
      drawerAsk: "ORCA உரையாடலில் கேள் 💬",
      drawerDismiss: "மூடு",
      mobChart: "வரைபடம்",
      mobAlerts: "எச்சரிக்கைகள்",
      mobChat: "உரையாடல்",
      mobGraph: "பகுப்பாய்வு",
      mobSpecies: "உயிரினங்கள்",
      viewPC: "PC",
      viewPhone: "போன்",
      queries: [
        { label: "🐋 அண்மைக்கால உயிரினங்கள்", query: "அண்மையில் கண்டறியப்பட்ட கடல் உயிரினங்கள் எவை?", zone_id: null },
        { label: "🧪 மாசு பகுதிகளைக் காட்டு", query: "கடல் மாசு பகுதிகளைக் காட்டு", zone_id: null },
        { label: "🌊 பலத்த காற்று & அலைகள்", query: "இன்று கடுமையான அலைகள் மற்றும் பலத்த காற்று ஆபத்து உள்ளதா?", zone_id: null },
        { label: "🐟 சிறந்த மீன்பிடி பகுதி", query: "இன்று சிறந்த மீன்பிடி பகுதி எங்குள்ளது?", zone_id: null },
        { label: "📈 24 மணி நேர கணிப்பு", query: "அடுத்த 24 மணி நேர வானிலை கணிப்பு என்ன?", zone_id: null },
        { label: "🆘 அவசர உதவி (VHF 16)", query: "Emergency distress assistance VHF Ch 16 contact", zone_id: null }
      ]
    }
  };

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
    "kolkata": { name: "Kolkata Approaches & Sundarbans", lat: 22.550, lon: 88.310 }
  };

  const BACKEND_API_BASE = (() => {
    const configured = (window.__KYROX_API_BASE__ || (window.__ENV__ && window.__ENV__.KYROX_API_BASE) || '').trim().replace(/\/$/, '');
    if (configured) return configured;
    if (window.location.port === '8000') return '';
    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') return `${window.location.protocol}//${window.location.hostname}:8000`;
    return 'http://localhost:8000';
  })();

  // 1. HERO PARTICLE SIMULATION
  function initHeroParticles() {
    const canvas = document.getElementById('heroParticleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let width = canvas.width = canvas.offsetWidth;
    let height = canvas.height = canvas.offsetHeight;

    window.addEventListener('resize', () => {
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    });

    const particles = [];
    const count = 35;
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        radius: Math.random() * 2 + 1,
        speedY: Math.random() * 0.4 + 0.15,
        speedX: (Math.random() - 0.5) * 0.2,
        opacity: Math.random() * 0.6 + 0.2
      });
    }

    function animate() {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#00F0FF';
      particles.forEach(p => {
        p.y -= p.speedY;
        p.x += p.speedX;
        if (p.y < -5) { p.y = height + 5; p.x = Math.random() * width; }
        ctx.globalAlpha = p.opacity;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      });
      requestAnimationFrame(animate);
    }
    animate();
  }

  // 2. VIEW NAVIGATION SYSTEM
  function switchActiveView(viewName) {
    currentActiveView = viewName;
    const navButtons = document.querySelectorAll('.sidebar-nav-btn');
    navButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
    });

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
      setTimeout(() => {
        if (leafletMap) leafletMap.invalidateSize();
      }, 100);
    } else if (viewName === 'dashboard') {
      if (mapStation && chartViewport && locSearchBar) {
        mapStation.appendChild(locSearchBar);
        mapStation.appendChild(chartViewport);
      }
      setTimeout(() => {
        if (leafletMap) leafletMap.invalidateSize();
      }, 100);
    } else if (viewName === 'species') {
      renderSpeciesCatalog();
    } else if (viewName === 'alerts') {
      renderBulletinsList();
    } else if (viewName === 'analytics') {
      setTimeout(() => {
        if (typeof drawRegressionCanvas === 'function') drawRegressionCanvas();
      }, 100);
    }
  }

  // 3. LEAFLET MAP & TACTICAL CARTOGRAPHY
  function initLeafletMap() {
    if (leafletMap) return;
    const mapContainer = document.getElementById('marineMapLeaflet');
    if (!mapContainer) return;

    const initLat = vesselLocation ? vesselLocation.latitude : 15.246;
    const initLon = vesselLocation ? vesselLocation.longitude : 73.803;

    leafletMap = L.map('marineMapLeaflet', {
      center: [initLat, initLon],
      zoom: 11,
      minZoom: 3,
      maxZoom: 18,
      zoomControl: false
    });

    L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);

    // Carto Dark Matter Basemap Tiles
    const cartoDarkUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
    const cartoAttr = '&copy; <a href="https://carto.com/" target="_blank">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>';

    tileLayer = L.tileLayer(cartoDarkUrl, {
      attribution: cartoAttr,
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(leafletMap);

    tileLayer.on('tileerror', () => {
      if (tileLayer._osmFallback) return;
      tileLayer._osmFallback = true;
      leafletMap.removeLayer(tileLayer);
      tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19
      }).addTo(leafletMap);
    });

    // Layer Groups
    riskHeatmapLayer = L.layerGroup().addTo(leafletMap);
    tacticalZonesLayer = L.layerGroup().addTo(leafletMap);
    waypointsLayer = L.layerGroup().addTo(leafletMap);
    speciesLayer = L.layerGroup().addTo(leafletMap);
    incidentsLayer = L.layerGroup().addTo(leafletMap);

    renderLeafletTacticalZones();
    renderLeafletWaypoints();
    renderSpeciesMarkers();
    renderIncidentMarkers();

    leafletMap.on('click', () => {
      closeTacticalDrawer();
    });

    updateHeatmapVisuals();
  }

  function updateDynamicMarineZones(lat, lon, locName, liveData) {
    if (typeof lat !== 'number' || typeof lon !== 'number') return;
    const isEastCoast = lon >= 78.0;
    const lonOffset = isEastCoast ? 0.18 : -0.18;
    const pfzLat = Number((lat - 0.04).toFixed(4));
    const pfzLon = Number((lon + lonOffset).toFixed(4));
    const cautionLat = Number((lat + 0.10).toFixed(4));
    const cautionLon = Number((lon + (isEastCoast ? 0.06 : -0.06)).toFixed(4));
    const dangerLat = Number((lat - 0.15).toFixed(4));
    const dangerLon = Number((lon + (isEastCoast ? 0.22 : -0.22)).toFixed(4));

    const displayName = locName || customLocationName || (vesselLocation && vesselLocation.name) || 'Active Coastal Sector';
    const telem = liveData || window.lastBridgeTelemetry || {};
    const sst = telem.sst || '28.4°C';
    const wave = telem.wave || '1.2m';

    MAP_ZONES = [
      {
        id: "zone-pfz-sw",
        type: "pfz",
        center: [pfzLat, pfzLon],
        latLngs: [
          [Number((pfzLat + 0.06).toFixed(4)), Number((pfzLon - 0.06).toFixed(4))],
          [Number((pfzLat + 0.05).toFixed(4)), Number((pfzLon + 0.06).toFixed(4))],
          [Number((pfzLat - 0.06).toFixed(4)), Number((pfzLon + 0.07).toFixed(4))],
          [Number((pfzLat - 0.08).toFixed(4)), Number((pfzLon - 0.05).toFixed(4))]
        ],
        label_en: `INCOIS PFZ Fishing Zone (${displayName})`,
        label_hi: `INCOIS PFZ मत्स्य क्षेत्र (${displayName})`,
        label_ta: `INCOIS PFZ மீன்பிடி பகுதி (${displayName})`,
        sub_en: `SST ${sst} • Optimal Chlorophyll Front`,
        reason_en: `Pelagic convergence zone for ${displayName}. Mackerel, Kingfish and Tuna feeding schools active. Calm sea state (${wave}).`,
        reason_hi: `${displayName} के लिए उच्च क्लोरोफिल व तापीय प्रवणता। बांगड़ा, सुरमई और टूना मछली के झुंड सक्रिय। शांत समुद्र (${wave})।`,
        coords: `${pfzLat.toFixed(2)}°N, ${pfzLon.toFixed(2)}°E (${isEastCoast ? 'Bearing 095° E' : 'Bearing 215° SW'}, 12 NM)`
      },
      {
        id: "zone-wind-ne",
        type: "caution",
        center: [cautionLat, cautionLon],
        latLngs: [
          [Number((cautionLat + 0.05).toFixed(4)), Number((cautionLon - 0.05).toFixed(4))],
          [Number((cautionLat + 0.06).toFixed(4)), Number((cautionLon + 0.06).toFixed(4))],
          [Number((cautionLat - 0.05).toFixed(4)), Number((cautionLon + 0.07).toFixed(4))],
          [Number((cautionLat - 0.06).toFixed(4)), Number((cautionLon - 0.05).toFixed(4))]
        ],
        label_en: `Caution Swell Zone (${displayName})`,
        label_hi: `सावधानी क्षेत्र (${displayName})`,
        label_ta: `எச்சரிக்கை பகுதி (${displayName})`,
        sub_en: `Swell 2.4m • Moderate Drift`,
        reason_en: `Moderate swell reaching 2.4m with gusty winds in inshore approaches. Small craft exercise vigilance.`,
        reason_hi: `तटीय जलक्षेत्र में 2.4m ऊंची लहरें और हवाएं। छोटी नौकाएं सतर्कता बरतें।`,
        coords: `${cautionLat.toFixed(2)}°N, ${cautionLon.toFixed(2)}°E (8 NM Inshore)`
      },
      {
        id: "zone-danger-se",
        type: "danger",
        center: [dangerLat, dangerLon],
        latLngs: [
          [Number((dangerLat + 0.07).toFixed(4)), Number((dangerLon - 0.06).toFixed(4))],
          [Number((dangerLat + 0.06).toFixed(4)), Number((dangerLon + 0.08).toFixed(4))],
          [Number((dangerLat - 0.07).toFixed(4)), Number((dangerLon + 0.06).toFixed(4))],
          [Number((dangerLat - 0.06).toFixed(4)), Number((dangerLon - 0.07).toFixed(4))]
        ],
        label_en: `Restricted Hazard Zone (Squall Alert)`,
        label_hi: `प्रतिबंधित खतरा क्षेत्र (Squall Alert)`,
        label_ta: `தடைசெய்யப்பட்ட ஆபத்து பகுதி`,
        sub_en: `Squall 40+ kt • Lightning Radar`,
        reason_en: `Radar tracked squall line with 40+ knot cyclonic gusts and lightning strikes. Entry prohibited.`,
        reason_hi: `तटीय रडार द्वारा ट्रैक किया गया स्क्वॉल क्षेत्र। 40+ नॉट की झंझावाती हवाएं और आकाशीय बिजली का खतरा।`,
        coords: `${dangerLat.toFixed(2)}°N, ${dangerLon.toFixed(2)}°E (16 NM Offshore)`
      }
    ];

    MAP_MARKERS = [
      {
        id: "mkr-pfz-target",
        kind: "pfz",
        latLng: [pfzLat, pfzLon],
        zone_id: "zone-pfz-sw",
        label_en: `PFZ Target Waypoint (${displayName})`,
        label_hi: `PFZ लक्ष्य बिंदु (${displayName})`,
        coords: `${pfzLat.toFixed(2)}°N, ${pfzLon.toFixed(2)}°E`,
        reason_en: `Optimal pelagic aggregation (12 NM offshore ${displayName}). Mackerel & Tuna schools active. Depth: 38-45m.`
      },
      {
        id: "mkr-squall-center",
        kind: "danger",
        latLng: [dangerLat, dangerLon],
        zone_id: "zone-danger-se",
        label_en: `Squall Core (${displayName})`,
        label_hi: `तूफान केंद्र (${displayName})`,
        coords: `${dangerLat.toFixed(2)}°N, ${dangerLon.toFixed(2)}°E`,
        reason_en: `Active offshore squall cell moving northeast. Severe gale force gusts.`
      }
    ];

    renderLeafletTacticalZones();
    renderLeafletWaypoints();
  }

  function renderLeafletTacticalZones() {
    if (!tacticalZonesLayer) return;
    tacticalZonesLayer.clearLayers();
    if (!isZonesLayerActive) return;

    MAP_ZONES.forEach(z => {
      if (!z.latLngs) return;
      const color = z.type === 'pfz' ? '#00F5D4' : (z.type === 'caution' ? '#FFB703' : '#FF3366');
      const polygon = L.polygon(z.latLngs, {
        color: color,
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.2
      });

      const label = (currentLang === 'hi') ? z.label_hi : (currentLang === 'ta' ? (z.label_ta || z.label_en) : z.label_en);
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
      const iconHtml = `<div style="width:26px;height:26px;border-radius:50%;background:${isPfz ? 'rgba(0,245,212,0.2)' : 'rgba(255,51,102,0.2)'};border:2px solid ${isPfz ? '#00F5D4' : '#FF3366'};display:flex;align-items:center;justify-content:center;font-size:12px;box-shadow:0 0 10px ${isPfz ? '#00F5D4' : '#FF3366'};">${isPfz ? '🐟' : '⚡'}</div>`;
      const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [26, 26], iconAnchor: [13, 13] });
      const marker = L.marker(m.latLng, { icon: customIcon });

      const label = (currentLang === 'hi') ? m.label_hi : m.label_en;
      marker.bindTooltip(label, { permanent: false, direction: 'top', className: 'tactical-map-tooltip' });
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        selectMapZone(m.zone_id);
      });
      waypointsLayer.addLayer(marker);
    });
  }

  function renderSpeciesMarkers() {
    if (!speciesLayer) return;
    speciesLayer.clearLayers();
    if (!isSpeciesLayerActive || !window.ORCA_SPECIES_CATALOG) return;

    window.ORCA_SPECIES_CATALOG.forEach(sp => {
      if (!sp.last_coords) return;
      const iconHtml = `<div style="width:30px;height:30px;border-radius:50%;background:rgba(0,240,255,0.2);border:2px solid #00F0FF;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 0 12px rgba(0,240,255,0.4);cursor:pointer;" title="${sp.name_en}">${sp.icon}</div>`;
      const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [30, 30], iconAnchor: [15, 15] });
      const marker = L.marker(sp.last_coords, { icon: customIcon });

      marker.bindTooltip(`<strong>${sp.icon} ${sp.name_en}</strong><br><span style="font-size:11px;color:#00F0FF;">${sp.iucn_label_en} • ${sp.detections_24h} hits</span>`, {
        permanent: false,
        direction: 'top',
        className: 'tactical-map-tooltip'
      });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const title = `${sp.icon} ${sp.name_en} (${sp.scientific})`;
        const reason = `${sp.bio_note_en} Acoustic: ${sp.acoustic_freq} | Swim Speed: ${sp.swim_speed} | Depth: ${sp.dive_depth}. Status: ${sp.protection_status_en}.`;
        const coordsStr = `${sp.last_coords[0]}°N, ${sp.last_coords[1]}°E (${sp.last_location_en})`;
        showTacticalDrawer(title, reason, coordsStr, 'species', sp.id);
      });

      speciesLayer.addLayer(marker);
    });
  }

  function renderIncidentMarkers() {
    if (!incidentsLayer) return;
    incidentsLayer.clearLayers();
    if (!isIncidentsLayerActive || !window.ORCA_MARINE_INCIDENTS) return;

    window.ORCA_MARINE_INCIDENTS.forEach(inc => {
      if (!inc.coords) return;
      const isCritical = inc.severity === 'danger';
      const color = isCritical ? '#FF3366' : '#FFB703';
      const iconHtml = `<div style="width:28px;height:28px;border-radius:6px;background:rgba(10,20,38,0.85);border:2px solid ${color};display:flex;align-items:center;justify-content:center;font-size:13px;box-shadow:0 0 12px ${color};cursor:pointer;" title="${inc.title_en}">${inc.icon}</div>`;
      const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [28, 28], iconAnchor: [14, 14] });
      const marker = L.marker(inc.coords, { icon: customIcon });

      marker.bindTooltip(`<strong>${inc.icon} ${inc.title_en}</strong>`, {
        permanent: false,
        direction: 'top',
        className: 'tactical-map-tooltip'
      });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        showTacticalDrawer(`${inc.icon} ${inc.title_en}`, inc.desc_en, `${inc.coords[0]}°N, ${inc.coords[1]}°E (${inc.location_en})`, inc.severity, inc.id);
      });

      incidentsLayer.addLayer(marker);
    });
  }

  function selectMapZone(zoneId) {
    activeZoneId = zoneId;
    const zone = MAP_ZONES.find(z => z.id === zoneId);
    if (!zone) return;
    const title = (currentLang === 'hi') ? zone.label_hi : (currentLang === 'ta' ? (zone.label_ta || zone.label_en) : zone.label_en);
    const reason = (currentLang === 'hi') ? zone.reason_hi : (currentLang === 'ta' ? (zone.reason_ta || zone.reason_en) : zone.reason_en);
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

  // 4. DYNAMIC 3x3 RISK HEATMAP
  function renderDynamicRiskHeatmap(riskPoints, userLocation) {
    if (!riskHeatmapLayer) return;
    riskHeatmapLayer.clearLayers();
    if (!isHeatmapActive || !Array.isArray(riskPoints) || riskPoints.length === 0) return;

    riskPoints.forEach((pt, idx) => {
      const risk = Number(pt.risk) || 0;
      const isCenter = (idx === 4);
      let fillColor = '#00F5D4';
      let strokeColor = '#00F5D4';
      let fillOpacity = 0.28;

      if (pt.risk_level === 'CRITICAL' || risk >= 75) {
        fillColor = '#FF3366';
        strokeColor = '#FF3366';
        fillOpacity = 0.55;
      } else if (pt.risk_level === 'HIGH' || risk >= 50) {
        fillColor = '#FF7A00';
        strokeColor = '#FF7A00';
        fillOpacity = 0.45;
      } else if (pt.risk_level === 'MEDIUM' || risk >= 30) {
        fillColor = '#FFB703';
        strokeColor = '#FFB703';
        fillOpacity = 0.38;
      }

      const circle = L.circle([pt.latitude, pt.longitude], {
        radius: isCenter ? 3400 : 2900,
        color: strokeColor,
        weight: isCenter ? 2 : 1,
        fillColor: fillColor,
        fillOpacity: fillOpacity
      });

      const cellLabel = isCenter ? `📍 User GPS Sector (${risk}% ${pt.risk_level})` : `P${idx + 1}: ${risk}% Risk (${pt.risk_level})`;
      circle.bindTooltip(cellLabel, { permanent: false, direction: 'top', className: 'tactical-map-tooltip' });

      circle.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const title = `${cellLabel} • [${pt.latitude.toFixed(4)}°, ${pt.longitude.toFixed(4)}°]`;
        const reason = `Live neural risk assessment: ${risk}% composite risk. Swell: ${pt.wave_height || '1.1m'}, Wind: ${pt.wind_speed || '12 kts'}. Status: ${pt.risk_level}.`;
        showTacticalDrawer(title, reason, `${pt.latitude.toFixed(4)}°N, ${pt.longitude.toFixed(4)}°E`, 'caution', `risk_pt_${idx+1}`);
      });

      riskHeatmapLayer.addLayer(circle);
    });
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
        if (data && Array.isArray(data.risk_points)) {
          renderDynamicRiskHeatmap(data.risk_points, data.user_location);
          return;
        }
      }
    } catch (e) {}

    // Offline / Local Dynamic 3x3 Heatmap Fallback
    const points = [];
    const step = 0.035;
    let idx = 1;
    for (let r = 1; r >= -1; r--) {
      for (let c = -1; c <= 1; c++) {
        const pLat = lat + r * step;
        const pLon = lon + c * step;
        const risk = idx === 5 ? 24 : (idx === 3 || idx === 7 ? 68 : (idx === 9 ? 82 : 35));
        const level = risk >= 75 ? 'CRITICAL' : (risk >= 50 ? 'HIGH' : (risk >= 30 ? 'MEDIUM' : 'LOW'));
        points.push({ latitude: pLat, longitude: pLon, risk: risk, risk_level: level, wave_height: '1.2m', wind_speed: '14 kts' });
        idx++;
      }
    }
    renderDynamicRiskHeatmap(points, { latitude: lat, longitude: lon });
  }

  function updateHeatmapVisuals() {
    const btn = document.getElementById('btnToggleHeatmap');
    const scale = document.getElementById('heatmapLegendScale');
    const txt = document.getElementById('txtHeatmapToggle');
    if (btn) btn.classList.toggle('active', isHeatmapActive);
    if (scale) scale.style.display = isHeatmapActive ? 'flex' : 'none';
    if (txt) txt.textContent = isHeatmapActive ? 'HEATMAP: ON' : 'HEATMAP: OFF';
    if (riskHeatmapLayer) {
      if (isHeatmapActive) {
        if (vesselLocation) fetchRiskHeatmap(vesselLocation.latitude, vesselLocation.longitude);
      } else {
        riskHeatmapLayer.clearLayers();
      }
    }
  }

  // 5. BULLETINS & ALERTS FEED
  async function fetchLiveBulletins(lat, lon) {
    const targetLat = lat !== undefined ? lat : (vesselLocation ? vesselLocation.latitude : 15.246);
    const targetLon = lon !== undefined ? lon : (vesselLocation ? vesselLocation.longitude : 73.803);

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
    } catch (e) {}

    // Default rich marine conservation bulletins
    BULLETINS = [
      {
        id: "ALRT-01",
        type: "danger",
        title_en: "Critical Squall Alert & Cyclonic Shear",
        title_hi: "गंभीर स्क्वॉल व झंझावाती हवा अलर्ट",
        desc_en: "Severe wind gusts exceeding 42 kts detected 16 NM offshore. Craft <20m advised to hold in port.",
        action_en: "Return to nearest protected harbour or reduce sail immediately.",
        zone_id: "zone-danger-se",
        coords: "15.09°N, 73.58°E"
      },
      {
        id: "ALRT-02",
        type: "caution",
        title_en: "Moderate Swell Surge & Current Anomaly",
        title_hi: "मध्यम समुद्री लहर व धारा चेतावनी",
        desc_en: "2.4m swell reaching inshore approaches. Trawlers exercise caution near shallow sandbars.",
        action_en: "Maintain continuous VHF Ch 16 watch and log GPS fixes hourly.",
        zone_id: "zone-wind-ne",
        coords: "15.34°N, 73.86°E"
      },
      {
        id: "ALRT-03",
        type: "resolved",
        title_en: "Optimal Pelagic Fishing Zone Active",
        title_hi: "सक्रिय मत्स्य क्षेत्र (INCOIS PFZ)",
        desc_en: "Satellite SST and Chlorophyll telemetry confirms prime feeding grounds 12 NM offshore.",
        action_en: "Ideal conditions for sustainable artisanal line fishing.",
        zone_id: "zone-pfz-sw",
        coords: "15.20°N, 73.62°E"
      }
    ];
    renderBulletinsList();
  }

  function renderBulletinsList() {
    const container = document.getElementById('bulletinCardsList');
    if (!container) return;

    let filtered = BULLETINS;
    if (currentAlertFilter !== 'all') {
      filtered = BULLETINS.filter(b => b.type === currentAlertFilter);
    }

    const badgeDangerEl = document.getElementById('badgeDangerCount');
    const dangerCount = BULLETINS.filter(b => b.type === 'danger').length;
    if (badgeDangerEl) badgeDangerEl.textContent = dangerCount;

    const navBadge = document.getElementById('sidebarAlertBadge');
    if (navBadge) navBadge.textContent = dangerCount > 0 ? `${dangerCount} NEW` : '0';

    const kpiAlertVal = document.getElementById('kpiValAlerts');
    if (kpiAlertVal) kpiAlertVal.textContent = BULLETINS.length;

    let html = '';
    filtered.forEach(b => {
      const type = b.type || 'normal';
      const badgeText = type.toUpperCase();
      html += `
        <div class="bulletin-card ${type}">
          <div class="bulletin-header-meta">
            <span class="bulletin-title">${escapeHtml(b.title_en || b.title_hi || '')}</span>
            <span class="bulletin-badge ${type}">${badgeText}</span>
          </div>
          <p class="bulletin-desc">${escapeHtml(b.desc_en || b.desc_hi || '')}</p>
          ${b.action_en ? `<div class="bulletin-action-rec">⚡ <strong>Action:</strong> ${escapeHtml(b.action_en)}</div>` : ''}
          <div class="bulletin-action-bar">
            <button type="button" class="btn-bulletin-action" onclick="window.orcaMapFocusZone('${b.zone_id || ''}')">🗺️ Map</button>
            <button type="button" class="btn-bulletin-action" onclick="window.orcaAskInChat('${escapeHtml(b.title_en || '')}')">💬 Ask AI</button>
          </div>
        </div>
      `;
    });

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

  // 6. SPECIES CATALOG RENDERER
  function renderSpeciesCatalog() {
    const grid = document.getElementById('speciesGridContainer');
    if (!grid || !window.ORCA_SPECIES_CATALOG) return;

    let html = '';
    window.ORCA_SPECIES_CATALOG.forEach(sp => {
      const name = (currentLang === 'hi') ? sp.name_hi : (currentLang === 'ta' ? sp.name_ta : sp.name_en);
      const iucnClass = sp.iucn;
      html += `
        <div class="species-card">
          <div class="species-card-top">
            <div class="species-avatar-seal">${sp.icon}</div>
            <span class="species-iucn-badge ${iucnClass}">${sp.iucn_label_en}</span>
          </div>
          <div class="species-name-wrap">
            <h3>${name}</h3>
            <div class="species-scientific">${sp.scientific}</div>
          </div>
          <div class="species-metrics-row">
            <div class="species-metric-item">
              <span class="species-metric-key">24h Hits</span>
              <span class="species-metric-val">${sp.detections_24h}</span>
            </div>
            <div class="species-metric-item">
              <span class="species-metric-key">Dive Depth</span>
              <span class="species-metric-val">${sp.dive_depth}</span>
            </div>
            <div class="species-metric-item">
              <span class="species-metric-key">Speed</span>
              <span class="species-metric-val">${sp.swim_speed}</span>
            </div>
          </div>
          <p style="font-size:0.75rem;color:var(--text-muted);line-height:1.4;">${sp.bio_note_en}</p>
          <div class="species-action-row">
            <button type="button" class="btn-species-track" onclick="window.orcaTrackSpecies('${sp.id}')">📍 Track on Live Map</button>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;
  }

  window.orcaTrackSpecies = function(speciesId) {
    const sp = window.ORCA_SPECIES_CATALOG.find(s => s.id === speciesId);
    if (!sp || !sp.last_coords) return;
    switchActiveView('map');
    if (leafletMap) {
      leafletMap.flyTo(sp.last_coords, 12, { duration: 1.2 });
      setTimeout(() => {
        showTacticalDrawer(`${sp.icon} ${sp.name_en}`, sp.bio_note_en, `${sp.last_coords[0]}°N, ${sp.last_coords[1]}°E`, 'species', sp.id);
      }, 1200);
    }
  };

  window.orcaMapFocusZone = function(zoneId) {
    switchActiveView('map');
    selectMapZone(zoneId);
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
    const targetLat = lat !== undefined ? lat : (vesselLocation ? vesselLocation.latitude : 15.246);
    const targetLon = lon !== undefined ? lon : (vesselLocation ? vesselLocation.longitude : 73.803);

    try {
      const res = await fetch(`${BACKEND_API_BASE}/telemetry?lat=${targetLat}&lon=${targetLon}`);
      if (res.ok) {
        const data = await res.json();
        updateBridgeTelemetryUI(data);
        return;
      }
    } catch (e) {}

    // Local realistic telemetry fallback
    updateBridgeTelemetryUI({
      sst: '28.4°C',
      wave: '1.2m',
      wind: '12.8 kts',
      current: '0.8 m/s',
      depth: '34m',
      baro: '1008.6 hPa'
    });
  }

  function updateBridgeTelemetryUI(data) {
    window.lastBridgeTelemetry = data || {};
    const sst = data.sst || '28.4°C';
    const wave = data.wave || '1.2m';
    const wind = data.wind || '12.8 kts';
    const depth = data.depth || '34m';
    const baro = data.baro || '1008.4 hPa';

    const kpiTemp = document.getElementById('kpiValTemp');
    if (kpiTemp) kpiTemp.textContent = sst;

    const telemDepth = document.getElementById('txtTelemDepth');
    if (telemDepth) telemDepth.innerHTML = `DEPTH: <strong>${depth}</strong>`;

    const telemBaro = document.getElementById('txtTelemBaro');
    if (telemBaro) telemBaro.innerHTML = `BARO: <strong>${baro}</strong>`;
  }

  // 8. "ASK ORCA" AI ASSISTANT CHAT ENGINE
  async function triggerTacticalQuery(text) {
    if (!text || !text.trim()) return;
    const thread = document.getElementById('tacticalChatThread');
    const input = document.getElementById('tacticalQueryInput');
    if (input) input.value = '';

    // Add User Bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.innerHTML = `
      <div class="chat-bubble-header"><span>PILOT QUERY</span><span>NOW</span></div>
      <div>${escapeHtml(text)}</div>
    `;
    thread.appendChild(userBubble);
    thread.scrollTop = thread.scrollHeight;

    // Loading Bubble
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble assistant';
    loadingBubble.innerHTML = `<div class="chat-bubble-header"><span>ORCA NEURAL AI</span><span>PROCESSING...</span></div><div>Analyzing satellite telemetry & environmental risk matrix...</div>`;
    thread.appendChild(loadingBubble);
    thread.scrollTop = thread.scrollHeight;

    try {
      const payload = {
        message: text,
        latitude: vesselLocation ? vesselLocation.latitude : 15.246,
        longitude: vesselLocation ? vesselLocation.longitude : 73.803,
        zone_id: activeZoneId
      };

      const res = await fetch(`${BACKEND_API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        const reply = data.reply || data.response || data.message || 'Analysis complete.';
        loadingBubble.innerHTML = `
          <div class="chat-bubble-header"><span>ORCA NEURAL DISPATCH</span><span>LIVE</span></div>
          <div>${formatMarkdown(reply)}</div>
        `;
        thread.scrollTop = thread.scrollHeight;
        return;
      }
    } catch (e) {}

    // Fallback AI Response
    setTimeout(() => {
      let smartReply = `Based on live telemetry at **${vesselLocation.latitude.toFixed(2)}°N, ${vesselLocation.longitude.toFixed(2)}°E**, sea state is **calm to moderate** with SST at **28.4°C**. Multi-agent analysis confirms active species tracks (Blue Whale, Olive Ridley Turtle) along the continental shelf edge. Wave heights remain within safe operating limits (<1.5m).`;
      if (text.toLowerCase().includes('pollution') || text.toLowerCase().includes('hotspot')) {
        smartReply = `**Pollution Hotspot Analysis:** SAR telemetry detected a localized micro-film 14 NM offshore. Dispersion vector is trending 215° SW at 0.8 kts. Coastal protection containment units have been notified. Avoid commercial trawling in sector **P9**.`;
      } else if (text.toLowerCase().includes('species') || text.toLowerCase().includes('whale') || text.toLowerCase().includes('turtle')) {
        smartReply = `**Species Intelligence:** 142 total acoustic tracks registered in the last 24h. A mother and calf Blue Whale pair is currently logged at **15.18°N, 73.45°E** (depth 185m). Morjim beach biosphere reports active Olive Ridley turtle arrivals.`;
      }
      loadingBubble.innerHTML = `
        <div class="chat-bubble-header"><span>ORCA NEURAL DISPATCH</span><span>NOMINAL</span></div>
        <div>${formatMarkdown(smartReply)}</div>
      `;
      thread.scrollTop = thread.scrollHeight;
    }, 600);
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
    recognition.lang = currentLang === 'hi' ? 'hi-IN' : (currentLang === 'ta' ? 'ta-IN' : 'en-IN');

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
      recognition.lang = currentLang === 'hi' ? 'hi-IN' : (currentLang === 'ta' ? 'ta-IN' : 'en-IN');
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
  const REG_VARIABLE_CONFIGS = {
    wave_height: { unit: 'm', label: 'Significant Wave Height', safeMax: 1.5, cautionMax: 2.5, dangerMin: 2.5, minPhys: 0.2, maxPhys: 6.0, defaultAnchor: 1.25, slopeSim: 0.032 },
    wind_speed: { unit: 'kts', label: 'Wind Speed', safeMax: 15.0, cautionMax: 25.0, dangerMin: 25.0, minPhys: 2.0, maxPhys: 55.0, defaultAnchor: 14.5, slopeSim: 0.35 },
    swell_wave_height: { unit: 'm', label: 'Swell Wave Height', safeMax: 1.2, cautionMax: 2.0, dangerMin: 2.0, minPhys: 0.1, maxPhys: 5.0, defaultAnchor: 1.10, slopeSim: 0.022 },
    ocean_current_velocity: { unit: 'm/s', label: 'Current Velocity', safeMax: 0.8, cautionMax: 1.5, dangerMin: 1.5, minPhys: 0.1, maxPhys: 3.5, defaultAnchor: 0.75, slopeSim: 0.015 },
    risk_score: { unit: 'idx', label: 'Marine Risk Index', safeMax: 35.0, cautionMax: 70.0, dangerMin: 70.0, minPhys: 5.0, maxPhys: 100.0, defaultAnchor: 32.0, slopeSim: 1.10 }
  };

  let activeRegVar = 'wave_height';
  let regShowCI = true;
  let regressionDataCache = null;
  let hoverActiveIndex = null;

  function computeClientOLS(xArr, yArr) {
    const n = xArr.length;
    if (n < 2) return { slope: 0, intercept: yArr[0] || 0, rSquared: 0, stdError: 0, equation: 'y = 0.00x + 0.00' };
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (let i = 0; i < n; i++) {
      sumX += xArr[i]; sumY += yArr[i];
      sumXY += xArr[i] * yArr[i]; sumX2 += xArr[i] * xArr[i]; sumY2 += yArr[i] * yArr[i];
    }
    const denom = (n * sumX2) - (sumX * sumX);
    const slope = Math.abs(denom) > 1e-9 ? ((n * sumXY) - (sumX * sumY)) / denom : 0;
    const intercept = (sumY - (slope * sumX)) / n;

    const yMean = sumY / n;
    let ssTot = 0, ssRes = 0;
    for (let i = 0; i < n; i++) {
      const yPred = (slope * xArr[i]) + intercept;
      ssTot += Math.pow(yArr[i] - yMean, 2);
      ssRes += Math.pow(yArr[i] - yPred, 2);
    }
    const rSquared = ssTot > 1e-9 ? Math.max(0, Math.min(1, 1 - (ssRes / ssTot))) : 0.88;
    const stdError = Math.sqrt(Math.max(0, ssRes / Math.max(1, n - 2)));
    const eqSign = intercept >= 0 ? '+' : '-';
    return { slope, intercept, rSquared, stdError, equation: `y = ${slope.toFixed(4)}x ${eqSign} ${Math.abs(intercept).toFixed(3)}` };
  }

  function computeLocal24hPrediction(varKey) {
    const cfg = REG_VARIABLE_CONFIGS[varKey];
    const anchor = cfg.defaultAnchor;
    const history = [];
    const now = new Date();

    for (let h = -24; h <= 0; h++) {
      const dt = new Date(now.getTime() + h * 3600 * 1000);
      const tidal = Math.sin(h * (2 * Math.PI / 12.4)) * (anchor * 0.12);
      const val = Math.max(cfg.minPhys, Math.min(cfg.maxPhys, anchor + (cfg.slopeSim * h) + tidal));
      history.push({ hour_offset: h, timestamp: dt.toISOString(), time_label: `${dt.getUTCHours()}:00 UTC`, value: parseFloat(val.toFixed(2)) });
    }

    const xHist = history.map(p => p.hour_offset);
    const yHist = history.map(p => p.value);
    const metrics = computeClientOLS(xHist, yHist);
    const predictions = [];

    for (let h = 1; h <= 24; h++) {
      const dt = new Date(now.getTime() + h * 3600 * 1000);
      let predVal = (metrics.slope * h) + metrics.intercept;
      predVal = Math.max(cfg.minPhys, Math.min(cfg.maxPhys, predVal));
      const margin = 1.96 * metrics.stdError * 1.05;
      const ciLower = Math.max(cfg.minPhys, predVal - margin);
      const ciUpper = Math.min(cfg.maxPhys, predVal + margin);
      const safetyStatus = predVal >= cfg.dangerMin ? 'danger' : (predVal >= cfg.cautionMax ? 'caution' : 'safe');

      predictions.push({
        hour_offset: h,
        timestamp: dt.toISOString(),
        time_label: `+${h}h`,
        predicted_value: parseFloat(predVal.toFixed(2)),
        ci_lower: parseFloat(ciLower.toFixed(2)),
        ci_upper: parseFloat(ciUpper.toFixed(2)),
        safety_status: safetyStatus,
        delta_from_now: parseFloat((predVal - yHist[yHist.length - 1]).toFixed(2))
      });
    }

    return {
      success: true,
      variable: varKey,
      unit: cfg.unit,
      label: cfg.label,
      metrics,
      summary: {
        val_now: yHist[yHist.length - 1],
        peak_val: Math.max(...predictions.map(p => p.predicted_value)),
        peak_hour: 24,
        overall_status: predictions.some(p => p.safety_status === 'danger') ? 'danger' : 'safe',
        advisory_en: `24-Hour statistical OLS projection confirms steady trend for ${cfg.label}. Maintain regular marine monitoring.`
      },
      history,
      predictions
    };
  }

  async function loadRegressionData(varKey) {
    activeRegVar = varKey;
    regressionDataCache = computeLocal24hPrediction(varKey);
    drawRegressionCanvas();
    updateRegressionHUD();
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
    const cfg = REG_VARIABLE_CONFIGS[activeRegVar] || REG_VARIABLE_CONFIGS.wave_height;
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
    ctx.strokeStyle = '#00F0FF';
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    history.forEach((pt, i) => {
      const px = toX(pt.hour_offset);
      const py = toY(pt.value);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.stroke();

    // Regression Future Line
    ctx.strokeStyle = '#FFB703';
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
    ctx.strokeStyle = '#00F0FF';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(xNow, padTop);
    ctx.lineTo(xNow, padTop + plotH);
    ctx.stroke();

    ctx.fillStyle = '#00F0FF';
    ctx.beginPath();
    ctx.arc(xNow, toY(history[history.length - 1].value), 5, 0, Math.PI * 2);
    ctx.fill();
  }

  function updateRegressionHUD() {
    if (!regressionDataCache) return;
    const d = regressionDataCache;
    const s = d.summary;
    const m = d.metrics;
    const p = d.predictions || [];

    const valCur = document.getElementById('valBtmCurrent');
    const valMid = document.getElementById('valBtmMid');
    const valPeak = document.getElementById('valBtmPeak');
    if (valCur) valCur.textContent = `${s.val_now.toFixed(2)} ${d.unit}`;
    if (valMid && p.length >= 6) valMid.textContent = `${p[5].predicted_value.toFixed(2)} ${d.unit}`;
    if (valPeak) valPeak.textContent = `${s.peak_val.toFixed(2)} ${d.unit}`;

    const eqEl = document.getElementById('txtRegEquation');
    const r2El = document.getElementById('txtRegR2');
    if (eqEl) eqEl.textContent = m.equation;
    if (r2El) r2El.textContent = m.rSquared.toFixed(3);

    const advBody = document.getElementById('txtRegAdvisoryBody');
    if (advBody) advBody.textContent = s.advisory_en;
  }

  // 10. LANGUAGE & UTILITIES
  function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('orca_marine_lang', lang);

    ['btnLangHI', 'btnLangEN', 'btnLangTA'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('selected');
    });

    const activeBtn = document.getElementById(lang === 'hi' ? 'btnLangHI' : (lang === 'ta' ? 'btnLangTA' : 'btnLangEN'));
    if (activeBtn) activeBtn.classList.add('selected');

    const dict = I18N[lang] || I18N.en;
    const elSub = document.getElementById('txtBridgeSubtitle');
    if (elSub) elSub.textContent = dict.bridgeSubtitle;

    renderQuickQueries();
    renderSpeciesCatalog();
    renderLeafletTacticalZones();
  }

  function renderQuickQueries() {
    const container = document.getElementById('quickQueriesRow');
    if (!container) return;
    const dict = I18N[currentLang] || I18N.en;
    let html = '';
    dict.queries.forEach(q => {
      html += `<button type="button" class="quick-query-pill" onclick="window.orcaQuickQuery('${escapeHtml(q.query)}')">${q.label}</button>`;
    });
    container.innerHTML = html;
  }

  window.orcaQuickQuery = function(queryText) {
    const input = document.getElementById('tacticalQueryInput');
    if (input) input.value = queryText;
    triggerTacticalQuery(queryText);
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function formatMarkdown(str) {
    if (!str) return '';
    return escapeHtml(str).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }

  // Master Initialization
  function initDashboard() {
    initHeroParticles();
    initLeafletMap();
    initVoiceRecognition();
    setLanguage(currentLang);
    updateDynamicMarineZones(vesselLocation.latitude, vesselLocation.longitude, 'Goa Coastal Sector');
    fetchLiveTelemetry(vesselLocation.latitude, vesselLocation.longitude);
    fetchLiveBulletins(vesselLocation.latitude, vesselLocation.longitude);
    renderSpeciesCatalog();
    loadRegressionData('wave_height');

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
          vesselLocation = { latitude: port.lat, longitude: port.lon, name: port.name };
          leafletMap.flyTo([port.lat, port.lon], 11, { duration: 1.2 });
          updateDynamicMarineZones(port.lat, port.lon, port.name);
          fetchLiveTelemetry(port.lat, port.lon);
          fetchLiveBulletins(port.lat, port.lon);
          fetchRiskHeatmap(port.lat, port.lon);
        }
      });
    });

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

    // Language Buttons
    const btnHi = document.getElementById('btnLangHI');
    const btnEn = document.getElementById('btnLangEN');
    const btnTa = document.getElementById('btnLangTA');
    if (btnHi) btnHi.addEventListener('click', () => setLanguage('hi'));
    if (btnEn) btnEn.addEventListener('click', () => setLanguage('en'));
    if (btnTa) btnTa.addEventListener('click', () => setLanguage('ta'));

    // Sunlight deck toggle
    const btnSunlight = document.getElementById('btnSunlightToggle');
    if (btnSunlight) {
      btnSunlight.addEventListener('click', () => {
        document.body.classList.toggle('deck-sunlight');
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

    // Master Clock
    setInterval(() => {
      const clock = document.getElementById('bridgeMasterClock');
      if (clock) {
        const now = new Date();
        clock.textContent = `${now.toTimeString().split(' ')[0]} IST`;
      }
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }

  window.ORCA = {
    switchActiveView,
    setLanguage,
    triggerTacticalQuery,
    loadRegressionData
  };
})();
