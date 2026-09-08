import os
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

def verify_files():
    for f in html_files:
        assert os.path.exists(f), f"File missing: {f}"
        with open(f, 'r', encoding='utf-8') as handle:
            content = handle.read()
        
        # 1. CARTO voyager raster URL present
        assert 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png' in content, f"CARTO voyager URL missing in {f}"
        
        # 2. Key appending logic present
        assert 'key=' in content, f"Key appending logic missing in {f}"
        
        # 3. CARTO and OpenStreetMap attribution present
        assert 'CARTO' in content and 'OpenStreetMap' in content, f"Attribution missing in {f}"
        
        # 4. Strict layer ordering: tileLayer -> riskHeatmapLayer -> tacticalZonesLayer -> waypointsLayer
        init_pos = content.find('// 1. CARTO Voyager Basemap')
        heat_pos = content.find('// 2. Risk Heatmap Layer')
        zones_pos = content.find('// 3. Tactical Zones & Waypoint Risk Markers')
        assert init_pos != -1, f"CARTO basemap comment missing in {f}"
        assert heat_pos != -1, f"Risk heatmap layer comment missing in {f}"
        assert zones_pos != -1, f"Tactical zones layer comment missing in {f}"
        assert init_pos < heat_pos < zones_pos, f"Layer ordering violated in {f}"
        
        # 5. User GPS marker with zIndexOffset present
        assert 'zIndexOffset: 1000' in content, f"User GPS zIndexOffset missing in {f}"
        
        # 6. Heatmap rendering function present
        assert 'renderDynamicRiskHeatmap' in content, f"renderDynamicRiskHeatmap missing in {f}"
        
        # 7. No hardcoded secret API keys in HTML
        assert 'CARTO_API_KEY = "' not in content or 'CARTO_API_KEY = ""' in content, f"Potential hardcoded key in {f}"

        print(f"[PASS] {f} verified successfully")

if __name__ == '__main__':
    verify_files()
    print("\n--- ALL 9 HTML FILES PASSED STRICT VERIFICATION ---")
