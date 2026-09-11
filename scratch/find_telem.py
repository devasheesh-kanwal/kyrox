import re

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines):
    if any(p in line for p in ['lastBridgeTelemetry', 'fetchBridgeTelemetry', 'updateBridgeTelemetryUI', 'BACKEND_URL', 'localhost:8000', '127.0.0.1:8000']):
        stripped = line[:180].rstrip()
        safe = stripped.encode('ascii', errors='replace').decode('ascii')
        print(f'{i+1}: {safe}')
