with open('server/templates/galaga.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. 배경 이미지 로더 추가
old_loader = "      boss: [new Image(), new Image(), new Image()],"
new_loader = """      boss: [new Image(), new Image(), new Image()],
      seaBg: new Image(),
      islandBg: new Image(),"""
text = text.replace(old_loader, new_loader)

old_src = "    assets.boss[2].src = '/static/game_assets/boss_3.png';"
new_src = """    assets.boss[2].src = '/static/game_assets/boss_3.png';
    assets.seaBg.src = '/static/game_assets/ocean_texture.jpg';
    assets.islandBg.src = '/static/game_assets/island_aerial.jpg';"""
text = text.replace(old_src, new_src)

# 2. 난이도 완화: 플레이어 목숨 5개, 폭탄 5개, 탄환 판정 축소
text = text.replace("let lives = 3;\n    let bombs = 3;", "let lives = 5;\n    let bombs = 5;")
text = text.replace("let lives = 3;\r\n    let bombs = 3;", "let lives = 5;\r\n    let bombs = 5;")
text = text.replace("lives = 3;\n      bombs = 3;", "lives = 5;\n      bombs = 5;")
text = text.replace("lives = 3;\r\n      bombs = 3;", "lives = 5;\r\n      bombs = 5;")
text = text.replace("lives-val').innerText = '✈✈✈';", "lives-val').innerText = '✈✈✈✈✈';")
text = text.replace("lives-val\" class=\"text-rose-400 text-xs\">✈✈✈<", "lives-val\" class=\"text-rose-400 text-xs\">✈✈✈✈✈<")
text = text.replace("bombs-val\" class=\"font-mono font-black text-sm\">3<", "bombs-val\" class=\"font-mono font-black text-sm\">5<")

# 3. 난이도 완화: 적 공격 쿨다운 증가 (탄막 빈도 절반으로 감소), 탄속 1.8 -> 1.25로 하향
text = text.replace("e.shootCooldown = e.type === 'bomber' ? 60 : 90;", "e.shootCooldown = e.type === 'bomber' ? 110 : 150;")
text = text.replace("vx: Math.cos(angle) * 1.8,\n            vy: Math.sin(angle) * 1.8", "vx: Math.cos(angle) * 1.25,\n            vy: Math.sin(angle) * 1.25")
text = text.replace("vx: Math.cos(angle) * 1.8,\r\n            vy: Math.sin(angle) * 1.8", "vx: Math.cos(angle) * 1.25,\r\n            vy: Math.sin(angle) * 1.25")

# 4. 보스 탄환 난이도 완화 (공격 주기 55 -> 95, 탄속 2.1 -> 1.4)
text = text.replace("if (boss.attackTimer % 55 === 0) {", "if (boss.attackTimer % 95 === 0) {")
text = text.replace("vy: 2.1", "vy: 1.4")
text = text.replace("vx: spread * 2.0,", "vx: spread * 1.3,")

# 5. 피격 판정 범위(Hitbox) 축소로 회피 난이도 대폭 하향 (스치면 사는 피탄 판정)
old_hit = """        if (player.isInvulnerable <= 0 &&
            eb.x > player.x + 4 && eb.x < player.x + player.w - 4 &&
            eb.y > player.y + 4 && eb.y < player.y + player.h - 4) {"""

new_hit = """        // 관대한 피탄 판정 (기체 중앙 12x12 코어에만 피격 적용)
        const pCenterX = player.x + player.w / 2;
        const pCenterY = player.y + player.h / 2;
        if (player.isInvulnerable <= 0 &&
            eb.x > pCenterX - 6 && eb.x < pCenterX + 6 &&
            eb.y > pCenterY - 6 && eb.y < pCenterY + 6) {"""
text = text.replace(old_hit, new_hit)

# 6. 배경 렌더링을 실제 해양 항공사진으로 교체 (실제 바다 수면 텍스처 무한 스크롤 + 섬 사진)
old_bg_draw = """      // 1. 깊은 바다 렌더링
      ctx.fillStyle = '#0a192f';
      ctx.fillRect(0, 0, W, H);

      // 군도 섬 & 모래사장 연출
      islands.forEach(isl => {
        ctx.fillStyle = '#1e3a8a';
        ctx.beginPath();
        ctx.arc(isl.x, isl.y, isl.r + 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = isl.color;
        ctx.beginPath();
        ctx.arc(isl.x, isl.y, isl.r, 0, Math.PI * 2);
        ctx.fill();
      });"""

new_bg_draw = """      // 1. 실제 태평양 항공 실사 바다 렌더링 (무한 스크롤)
      if (assets.seaBg && assets.seaBg.complete && assets.seaBg.naturalWidth > 0) {
        const bgH = H;
        const scrollY = oceanOffset % bgH;
        // 2장 연속 배치로 끊김없는 무한 스크롤
        ctx.drawImage(assets.seaBg, 0, scrollY - bgH, W, bgH);
        ctx.drawImage(assets.seaBg, 0, scrollY, W, bgH);
        // 바다 위에 약간의 푸른 틴트 필터
        ctx.fillStyle = 'rgba(10, 30, 60, 0.25)';
        ctx.fillRect(0, 0, W, H);
      } else {
        ctx.fillStyle = '#0a192f';
        ctx.fillRect(0, 0, W, H);
      }

      // 실제 항공 섬 사진 렌더링
      islands.forEach(isl => {
        if (assets.islandBg && assets.islandBg.complete && assets.islandBg.naturalWidth > 0) {
          ctx.save();
          // 원형 클리핑으로 자연스러운 열대 섬 연출
          ctx.beginPath();
          ctx.arc(isl.x, isl.y, isl.r, 0, Math.PI * 2);
          ctx.clip();
          ctx.drawImage(assets.islandBg, isl.x - isl.r, isl.y - isl.r, isl.r * 2, isl.r * 2);
          ctx.restore();
          // 산호초 에메랄드 링 테두리
          ctx.strokeStyle = 'rgba(45, 212, 191, 0.4)';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.arc(isl.x, isl.y, isl.r + 2, 0, Math.PI * 2);
          ctx.stroke();
        } else {
          ctx.fillStyle = isl.color;
          ctx.beginPath();
          ctx.arc(isl.x, isl.y, isl.r, 0, Math.PI * 2);
          ctx.fill();
        }
      });"""
text = text.replace(old_bg_draw, new_bg_draw)

# 저장
with open('server/templates/galaga.html', 'w', encoding='utf-8') as f:
    f.write(text)

with open('g:/내 드라이브/PROJECT/HDDGOD/server/templates/galaga.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated galaga.html with real photo backgrounds and easy difficulty!')
