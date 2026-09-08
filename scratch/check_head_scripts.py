import os

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

pattern = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>'
for p in html_files:
    with open(p, 'r', encoding='utf-8') as f:
        c = f.read()
    print(f'{p}: has_leaflet_script={pattern in c}')
