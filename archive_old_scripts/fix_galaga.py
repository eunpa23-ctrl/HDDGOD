import os

for path in ['server/templates/galaga.html', 'g:/내 드라이브/PROJECT/HDDGOD/server/templates/galaga.html']:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        fixed = content.replace("document.getElementById('gameCanvas');\\n", "document.getElementById('gameCanvas');\n")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print(f"Fixed {path}")
