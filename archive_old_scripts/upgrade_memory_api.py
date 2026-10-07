import os

roots = [r'g:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']

for root in roots:
    core_p = os.path.join(root, 'server', 'server_core.py')
    if os.path.exists(core_p):
        with open(core_p, 'r', encoding='utf-8') as f:
            content = f.read()
        
        old_fn = '''@app.post("/api/optimize_memory")
async def optimize_memory():
    import gc
    import ctypes
    # 파이썬 내부 쓰레기 수집기 강제 실행
    gc.collect()
    # 윈도우 API를 호출해 프로세스 잉여 메모리를 OS에 즉각 반환
    try:
        ctypes.windll.kernel32.SetProcessWorkingSetSize(ctypes.windll.kernel32.GetCurrentProcess(), -1, -1)
    except Exception as e:
        logger.warning(f"메모리 반환 에러: {e}")
    return {"status": "ok"}'''

        new_fn = '''@app.post("/api/optimize_memory")
async def optimize_memory():
    """윈도우 OS의 전체 프로세스 유휴 캐시 메모리를 안전하게 회수 (EmptyWorkingSet)"""
    import gc
    import ctypes
    import psutil

    gc.collect()
    before_vm = psutil.virtual_memory()

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    trimmed_count = 0

    for proc in psutil.process_iter(['pid']):
        try:
            pid = proc.info['pid']
            if pid <= 4:
                continue
            h_process = kernel32.OpenProcess(0x001F0FFF, False, pid)
            if h_process:
                if psapi.EmptyWorkingSet(h_process):
                    trimmed_count += 1
                kernel32.CloseHandle(h_process)
        except Exception:
            pass

    after_vm = psutil.virtual_memory()
    freed_mb = round((before_vm.used - after_vm.used) / (1024 * 1024), 1)
    logger.info(f"⚡ [메모리 최적화 완료] {trimmed_count}개 프로세스 정리, {freed_mb}MB 메모리 즉시 확보 (현재 점유율: {after_vm.percent}%)")

    return {
        "status": "ok",
        "trimmed_count": trimmed_count,
        "freed_mb": freed_mb,
        "current_ram_percent": after_vm.percent,
        "available_gb": round(after_vm.available / (1024**3), 2)
    }'''

        if old_fn in content:
            content = content.replace(old_fn, new_fn)
            with open(core_p, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {core_p}")
        else:
            print(f"Could not find exact old_fn in {core_p}")
