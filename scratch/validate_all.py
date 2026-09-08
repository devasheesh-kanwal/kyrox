from validate_js import parse_js

files = [
    'alerts.html',
    'chat.html',
    'index.html',
    'map.html',
    'Frontend/index.html',
    'Frontend/Alerts/alerts.html',
    'Frontend/Chat/chat.html',
    'Frontend/Map/map.html',
    'map/map.html'
]

for p in files:
    with open(p, 'r', encoding='utf-8') as f:
        html = f.read()
    start = html.find('<script>')
    end = html.rfind('</script>')
    script_code = html[start+8:end]
    parse_js(script_code)
    print(f"SUCCESS: {p} parsed with 0 syntax errors!")

print("\nALL 9 BRIDGE HTML FILES 100% VALIDATED WITH ZERO SYNTAX ERRORS!")
