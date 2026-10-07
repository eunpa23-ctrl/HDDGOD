import os

roots = [r'g:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']

for root in roots:
    p = os.path.join(root, 'server', 'templates', 'dashboard.html')
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()

        target = '''        function optimizeServerMemory() {
            fetch('/api/optimize_memory', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    // 잠깐 동안 버튼 시각적 피드백 주기
                    const btn = document.querySelector('button[onclick="optimizeServerMemory()"]');
                    if (btn) {
                        const originalHTML = btn.innerHTML;
                        btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i> 완료';
                        setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
                    }
                })
                .catch(err => console.error("메모리 최적화 실패:", err));
        }'''

        replacement = '''        function optimizeServerMemory() {
            const btn = document.querySelector('button[onclick="optimizeServerMemory()"]');
            if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 정리 중';
            fetch('/api/optimize_memory', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (btn) {
                        btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i> 완료';
                        setTimeout(() => { btn.innerHTML = '<i class="fa-solid fa-broom"></i> 최적화'; }, 2000);
                    }
                    alert(`⚡ [메모리 최적화 완료]\\n• 정리된 프로세스: ${data.trimmed_count}개\\n• 즉시 확보된 메모리: ${data.freed_mb} MB\\n• 현재 전체 RAM 점유율: ${data.current_ram_percent}% (여유: ${data.available_gb} GB)`);
                })
                .catch(err => {
                    if (btn) btn.innerHTML = '<i class="fa-solid fa-broom"></i> 최적화';
                    console.error("메모리 최적화 실패:", err);
                    alert("메모리 최적화 요청 중 오류가 발생했습니다.");
                });
        }'''

        if target in content:
            content = content.replace(target, replacement)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {p}")
        else:
            print(f"Target not found in {p}")
