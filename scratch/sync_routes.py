# scratch/sync_routes.py
import os

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    master = f.read()

def adapt_for_subfolder(content, default_view):
    res = content.replace('href="css/orca-theme.css"', 'href="../css/orca-theme.css"')
    res = res.replace('src="js/species-data.js"', 'src="../js/species-data.js"')
    res = res.replace('src="js/orca-dashboard.js"', 'src="../js/orca-dashboard.js"')
    res = res.replace('src="map_config.js"', 'src="../map_config.js"')
    res = res.replace('src="env.js"', 'src="../env.js"')
    
    script = f'''
  <script>
    window.addEventListener("DOMContentLoaded", function() {{
      if (window.ORCA && window.ORCA.switchActiveView) {{
        window.ORCA.switchActiveView("{default_view}");
      }}
    }});
  </script>
'''
    res = res.replace('</body>', script + '</body>')
    return res

# 1. Alerts
with open('Frontend/Alerts/alerts.html', 'w', encoding='utf-8') as f:
    f.write(adapt_for_subfolder(master, 'alerts'))
print('Frontend/Alerts/alerts.html updated')

# 2. Chat
with open('Frontend/Chat/chat.html', 'w', encoding='utf-8') as f:
    f.write(adapt_for_subfolder(master, 'chat'))
print('Frontend/Chat/chat.html updated')

# 3. Map (Frontend/Map/map.html)
with open('Frontend/Map/map.html', 'w', encoding='utf-8') as f:
    f.write(adapt_for_subfolder(master, 'map'))
print('Frontend/Map/map.html updated')

# 4. map/map.html (in root map folder)
if os.path.exists('map'):
    with open('map/map.html', 'w', encoding='utf-8') as f:
        f.write(adapt_for_subfolder(master, 'map'))
    print('map/map.html updated')
