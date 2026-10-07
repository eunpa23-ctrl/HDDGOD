with open('server/templates/galaga.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 버튼에 ontouchstart 추가
old_btn = '<button id="start-btn" onclick="startGame()"'
new_btn = '<button id="start-btn" onclick="startGame()" ontouchstart="startGame(); event.preventDefault();"'
text = text.replace(old_btn, new_btn)

with open('server/templates/galaga.html', 'w', encoding='utf-8') as f:
    f.write(text)

with open('g:/내 드라이브/PROJECT/HDDGOD/server/templates/galaga.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated start button with ontouchstart!')
