# -*- coding: utf-8 -*-

with open(r'Z:\client\client_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'uwfmgr.exe file commit-delete' in line:
        # 이전의 try와 이후의 except pass 블록 제거는 앞뒤 2줄 정도
        continue
    new_lines.append(line)

# 더 깔끔하게 다시 로드해서 정리
content = "".join(new_lines)
import re
content = re.sub(r'(\s*#\s*UWF[^\n]*\n)?\s*try:\s*\n\s*except Exception:\s*\n\s*pass\s*\n', '', content)

with open(r'Z:\client\client_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Remaining uwfmgr removed successfully.")
