with open('Frontend/Alerts/alerts.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = {
    'Has marineMapLeaflet': 'id="marineMapLeaflet"' in content,
    'No marineSvgChart': 'marineSvgChart' not in content,
    'Has leafletMap init': 'initLeafletMap()' in content,
    'Has pulsing beacon': 'leaflet-user-beacon' in content,
    'Has dynamic risk circles': 'renderDynamicRiskHeatmap' in content,
    'Has pinUserLocationOnMap': 'pinUserLocationOnMap' in content,
    'Has CartoDB tiles': 'cartocdn.com' in content,
    'No svgMarineHeatmapLayer': 'svgMarineHeatmapLayer' not in content,
}

for k, v in checks.items():
    print(k, ':', v)

assert all(checks.values()), 'Some checks failed!'
print('ALL CHECKS PASSED!')
