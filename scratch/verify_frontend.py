# scratch/verify_frontend.py
import re
import os

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('Frontend/js/orca-dashboard.js', 'r', encoding='utf-8') as f:
    js_dashboard = f.read()

with open('Frontend/js/species-data.js', 'r', encoding='utf-8') as f:
    js_species = f.read()

with open('Frontend/css/orca-theme.css', 'r', encoding='utf-8') as f:
    css = f.read()

print("HTML size:", len(html), "bytes")
print("Dashboard JS size:", len(js_dashboard), "bytes")
print("Species JS size:", len(js_species), "bytes")
print("CSS size:", len(css), "bytes")

# Check all getElementById calls in JS
dom_ids_in_js = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", js_dashboard)
unique_ids = sorted(list(set(dom_ids_in_js)))
print(f"\nChecking {len(unique_ids)} DOM IDs referenced in JS against index.html:")

missing_ids = []
for dom_id in unique_ids:
    if f'id="{dom_id}"' not in html and f"id='{dom_id}'" not in html:
        missing_ids.append(dom_id)

if missing_ids:
    print("WARNING: Missing IDs in HTML:", missing_ids)
else:
    print("All DOM IDs exist in index.html!")
