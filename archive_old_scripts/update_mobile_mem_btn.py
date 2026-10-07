import os

roots = [r'g:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']

for root in roots:
    p = os.path.join(root, 'server', 'templates', 'mobile_dashboard.html')
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()

        # 헤더 우측 버튼 그룹에 메모리 최적화 버튼 추가
        target = '''            <button onclick="openSettingsModal()" class="w-10 h-10 rounded-full bg-slate-800 text-amber-400 flex items-center justify-center active:bg-slate-700 shadow-[0_0_10px_rgba(251,191,36,0.3)]" title="환경설정">
                <i class="fa-solid fa-gear"></i>
            </button>'''

        replacement = '''            <button id="mob-mem-btn" onclick="optimizeMemoryMobile()" class="w-10 h-10 rounded-full bg-slate-800 text-emerald-400 flex items-center justify-center active:bg-slate-700 shadow-[0_0_10px_rgba(16,185,129,0.3)]" title="메모리 최적화">
                <i class="fa-solid fa-broom text-sm"></i>
            </button>
            <button onclick="openSettingsModal()" class="w-10 h-10 rounded-full bg-slate-800 text-amber-400 flex items-center justify-center active:bg-slate-700 shadow-[0_0_10px_rgba(251,191,36,0.3)]" title="환경설정">
                <i class="fa-solid fa-gear"></i>
            </button>'''

        if target in content:
            content = content.replace(target, replacement)

        # JS 함수 추가
        js_target = 'function sendCommand(target, action) {'
        js_replacement = '''function optimizeMemoryMobile() {
            const btn = document.getElementById('mob-mem-btn');
            if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i>';
            fetch('/api/optimize_memory', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (btn) {
                        btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400 text-sm"></i>';
                        setTimeout(() => { btn.innerHTML = '<i class="fa-solid fa-broom text-sm"></i>'; }, 2000);
                    }
                    alert(`⚡ 메모리 최적화 완료!\\n- 정리된 프로세스: ${data.trimmed_count}개\\n- 확보된 메모리: ${data.freed_mb} MB\\n- 현재 RAM 점유율: ${data.current_ram_percent}% (여유: ${data.available_gb} GB)`);
                })
                .catch(err => {
                    if (btn) btn.innerHTML = '<i class="fa-solid fa-broom text-sm"></i>';
                    alert('메모리 최적화 요청 중 오류가 발생했습니다.');
                });
        }

        function sendCommand(target, action) {'''

        if js_target in content:
            content = content.replace(js_target, js_replacement)

        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {p}")
