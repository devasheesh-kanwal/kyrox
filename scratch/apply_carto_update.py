import re

html_files = [
    'alerts.html',
    'chat.html',
    'index.html',
    'map.html',
    'map/map.html',
    'Frontend/Alerts/alerts.html',
    'Frontend/Chat/chat.html',
    'Frontend/Map/map.html',
    'Frontend/index.html'
]

# 1. Target head script replacement
old_head_script = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>'
new_head_script = '''<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <!-- CARTO Basemaps & Environment Configuration Utility -->
  <script src="env.js" onerror=""></script>
  <script src="../env.js" onerror=""></script>
  <script src="../../env.js" onerror=""></script>
  <script src="map_config.js" onerror=""></script>
  <script src="../map_config.js" onerror=""></script>
  <script src="../../map_config.js" onerror=""></script>'''

# 2. Target tileLayer + layer ordering replacement
old_map_init_pattern = re.compile(
    r'''// CartoDB DarkMatter nautical tiles\s*'''
    r'''tileLayer = L\.tileLayer\('https://\{s\}\.basemaps\.cartocdn\.com/dark_all/\{z\}/\{x\}/\{y\}\{r\}\.png',\s*\{[^}]*\}\)\.addTo\(leafletMap\);\s*'''
    r'''tacticalZonesLayer = L\.layerGroup\(\)\.addTo\(leafletMap\);\s*'''
    r'''riskHeatmapLayer = L\.layerGroup\(\)\.addTo\(leafletMap\);\s*'''
    r'''waypointsLayer = L\.layerGroup\(\)\.addTo\(leafletMap\);''',
    re.DOTALL
)

new_map_init = '''      // CARTO Voyager Basemap Integration
      const cartoTileUrl = (typeof CartoMapConfig !== 'undefined' && CartoMapConfig.getTileUrl)
        ? CartoMapConfig.getTileUrl()
        : (() => {
            const env = (typeof window !== 'undefined' && (window.__ENV__ || window.CARTO_CONFIG || window.ENV)) || {};
            const baseUrl = env.CARTO_BASEMAP_URL || 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png';
            const apiKey = env.CARTO_API_KEY || (typeof window !== 'undefined' && window.CARTO_API_KEY) || '';
            if (apiKey && apiKey.trim().length > 0) {
              const sep = baseUrl.includes('?') ? '&' : '?';
              return `${baseUrl}${sep}key=${encodeURIComponent(apiKey.trim())}`;
            }
            return baseUrl;
          })();

      const cartoAttribution = (typeof CartoMapConfig !== 'undefined' && CartoMapConfig.attribution)
        ? CartoMapConfig.attribution
        : '&copy; <a href="https://carto.com/" target="_blank" rel="noopener">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';

      // 1. CARTO Voyager Basemap (bottom layer, tilePane, zIndex 200)
      tileLayer = L.tileLayer(cartoTileUrl, {
        attribution: cartoAttribution,
        subdomains: 'abcd',
        maxZoom: 19
      }).addTo(leafletMap);

      // STRICT LAYER ORDERING:
      // CARTO BASEMAP (tileLayer) -> RISK HEATMAP -> RISK ZONES / MARKERS -> USER GPS MARKER
      // 2. Risk Heatmap Layer (overlayPane, zIndex 400)
      riskHeatmapLayer = L.layerGroup().addTo(leafletMap);

      // 3. Tactical Zones & Waypoint Risk Markers (overlayPane, renders on top of heatmap)
      tacticalZonesLayer = L.layerGroup().addTo(leafletMap);
      waypointsLayer = L.layerGroup().addTo(leafletMap);'''

# 3. Target attribution CSS
old_css_marker = '/* Tactical Map Tooltip */'
attribution_css = '''/* CARTO & OSM Map Attribution (Strictly visible and styled) */
    .leaflet-control-attribution {
      background: rgba(18, 16, 14, 0.88) !important;
      color: #A89B88 !important;
      font-family: var(--font-telemetry) !important;
      font-size: 10px !important;
      padding: 2px 8px !important;
      border-top-left-radius: 4px !important;
      border: 1px solid var(--border-bezel) !important;
      border-right: none !important;
      border-bottom: none !important;
      z-index: 1000 !important;
    }
    .leaflet-control-attribution a {
      color: var(--brass-bright) !important;
      text-decoration: underline !important;
    }

    /* Tactical Map Tooltip */'''

for path in html_files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update head scripts
    if old_head_script in content and 'map_config.js' not in content:
        content = content.replace(old_head_script, new_head_script, 1)
        print(f"[{path}] Updated head scripts")
    else:
        print(f"[{path}] Head scripts already updated or pattern not found")

    # 2. Update map init
    content, count = old_map_init_pattern.subn(new_map_init, content)
    print(f"[{path}] Replaced map init: {count} match(es)")
    assert count == 1, f"Failed map init replacement for {path}"

    # 3. Add attribution CSS if not present
    if '.leaflet-control-attribution' not in content:
        content = content.replace(old_css_marker, attribution_css, 1)
        print(f"[{path}] Added attribution CSS")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("All HTML files updated successfully!")
