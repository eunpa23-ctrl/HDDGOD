import os, re, shutil

roots = [r'g:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']

for root in roots:
    # 1. server_core.py에서 galaga 라우트 제거
    core_p = os.path.join(root, 'server', 'server_core.py')
    if os.path.exists(core_p):
        with open(core_p, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        skip = False
        for line in lines:
            if '@app.get("/galaga"' in line:
                skip = True
                continue
            if skip and (line.startswith('@app.') or line.startswith('def ') or line.startswith('async def ')):
                skip = False
            if not skip:
                new_lines.append(line)
        with open(core_p, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f'Cleaned galaga route in {core_p}')

    # 2. mobile_dashboard.html에서 galaga 버튼 제거
    mob_p = os.path.join(root, 'server', 'templates', 'mobile_dashboard.html')
    if os.path.exists(mob_p):
        with open(mob_p, 'r', encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'<a href="/galaga"[\s\S]*?</a>\s*', '', content)
        with open(mob_p, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Cleaned galaga button in {mob_p}')

    # 3. 파일 및 디렉토리 삭제
    galaga_html = os.path.join(root, 'server', 'templates', 'galaga.html')
    if os.path.exists(galaga_html):
        os.remove(galaga_html)
        print(f'Deleted {galaga_html}')

    game_assets = os.path.join(root, 'server', 'static', 'game_assets')
    if os.path.exists(game_assets):
        shutil.rmtree(game_assets, ignore_errors=True)
        print(f'Deleted {game_assets}')

    planes_art = os.path.join(root, 'server', 'static', 'planes_art')
    if os.path.exists(planes_art):
        shutil.rmtree(planes_art, ignore_errors=True)
        print(f'Deleted {planes_art}')
