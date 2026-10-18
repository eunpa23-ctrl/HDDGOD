# -*- coding: utf-8 -*-
import re

with open(r'Z:\client\client_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. update.bat template 내 where uwfmgr.exe 블록 제거
pattern1 = r':: UWF[^\n]*\nwhere uwfmgr\.exe >nul 2>&1\s*\nif not errorlevel 1 \([^)]*\)\s*\n'
content = re.sub(pattern1, '', content)

# 2. commit-delete 제거
pattern2 = r'# UWF[^\n]*\s*\ntry:\s*\n\s*subprocess\.run\(f[\'"]uwfmgr\.exe file commit-delete[^\n]*\n\s*except Exception:\s*\n\s*pass\s*\n'
content = re.sub(pattern2, '', content)

# 3. show_update_complete_window 간소화
pattern3 = r'lbl = tk\.Label\(root, text=f"[^"]*\\n\(UWF[^"]*", font=\("맑은 고딕", 10\)\)'
content = re.sub(pattern3, 'lbl = tk.Label(root, text=f"🎉 제우스 에이전트 v{current_version} 설치 완료!", font=("맑은 고딕", 10))', content)

with open(r'Z:\client\client_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("client_agent.py patch applied successfully.")
