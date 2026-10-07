import os

roots = [r'g:\내 드라이브\PROJECT\HDDGOD', r'C:\Users\USER\Documents\HDDGOD']

new_loop_code = '''async def telegram_alert_loop():
    """서버 CPU/RAM 사용량 정밀 감시 및 지능형 알림/자동 최적화 데몬
    - 0.001초 순간 스파이크(착시) 필터링 (최소 30초 이상 실제 초과 시에만 발송)
    - RAM 85% 초과 감지 시 자동으로 EmptyWorkingSet 최적화 1차 선제 실행
    - CPU와 RAM 알림을 명확히 분리하여 오해 방지
    """
    last_cpu_alert_time = 0
    last_ram_alert_time = 0
    consecutive_high_cpu = 0
    consecutive_high_ram = 0

    while True:
        try:
            # 1초 평균 CPU 측정 (interval=None의 찰나 스파이크 제거)
            cpu_usage = await asyncio.to_thread(psutil.cpu_percent, 1.0)
            ram_info = psutil.virtual_memory()
            ram_usage = ram_info.percent
            ram_used_gb = round(ram_info.used / (1024**3), 2)
            ram_total_gb = round(ram_info.total / (1024**3), 2)
            current_time = time.time()

            # 1. CPU 고부하 감시 (임계치 85% 이상이 3회 연속 = 30초 이상 지속될 때만)
            if cpu_usage >= 85.0:
                consecutive_high_cpu += 1
            else:
                consecutive_high_cpu = 0

            if consecutive_high_cpu >= 3:
                if current_time - last_cpu_alert_time > 600:  # 10분 쿨타임
                    msg = (
                        f"⚠️ [제우스 서버 경고 - CPU 지속 과부하]\\n"
                        f"카운터 PC CPU가 30초 이상 고부하 상태입니다!\\n\\n"
                        f"💻 실측 CPU: {cpu_usage}% (지속)\\n"
                        f"🧠 현재 RAM: {ram_used_gb}GB / {ram_total_gb}GB ({ram_usage}%)"
                    )
                    await send_telegram_msg(msg)
                    logger.warning(f"텔레그램 CPU 과부하 알림 발송: CPU {cpu_usage}%")
                    last_cpu_alert_time = current_time
                    consecutive_high_cpu = 0

            # 2. RAM 고부하 감시 (임계치 85% 이상이 3회 연속 = 30초 이상 지속될 때만)
            if ram_usage >= 85.0:
                consecutive_high_ram += 1
            else:
                consecutive_high_ram = 0

            if consecutive_high_ram >= 3:
                # 85% 초과 시 먼저 안전 메모리 트림(EmptyWorkingSet) 자동 실행 시도!
                logger.warning(f"🚨 RAM 사용량 {ram_usage}% 감지! 자동 메모리 비우기 선제 실행...")
                try:
                    await optimize_memory()
                    # 최적화 후 재측정
                    after_ram = psutil.virtual_memory().percent
                    logger.info(f"선제 메모리 최적화 완료: {ram_usage}% -> {after_ram}%")
                    if after_ram < 80.0:
                        # 최적화로 해결되었으면 사장님께 경고 문자 안 보내고 조용히 해결!
                        consecutive_high_ram = 0
                        await asyncio.sleep(10)
                        continue
                except Exception as opt_err:
                    logger.error(f"선제 최적화 실패: {opt_err}")

                if current_time - last_ram_alert_time > 600:  # 10분 쿨타임
                    msg = (
                        f"⚠️ [제우스 서버 경고 - RAM 부족 위험]\\n"
                        f"카운터 PC 물리 메모리가 지속적으로 85%를 초과했습니다!\\n\\n"
                        f"🧠 실제 사용 RAM: {ram_used_gb}GB / {ram_total_gb}GB ({ram_usage}%)\\n"
                        f"💻 현재 CPU: {cpu_usage}%\\n"
                        f"💡 서버가 유휴 메모리 자동 회수를 시도했습니다."
                    )
                    await send_telegram_msg(msg)
                    logger.warning(f"텔레그램 RAM 부족 알림 발송: RAM {ram_usage}%")
                    last_ram_alert_time = current_time
                    consecutive_high_ram = 0

        except Exception as e:
            logger.error(f"텔레그램 알림 루프 오류: {e}")
        await asyncio.sleep(10)
'''

for root in roots:
    core_p = os.path.join(root, 'server', 'server_core.py')
    if not os.path.exists(core_p):
        continue
    with open(core_p, 'r', encoding='utf-8') as f:
        content = f.read()

    # 기존 telegram_alert_loop 찾아서 교체
    start_idx = content.find("async def telegram_alert_loop():")
    if start_idx != -1:
        end_idx = content.find("async def notify_tunnel_url_to_telegram():", start_idx)
        if end_idx != -1:
            content = content[:start_idx] + new_loop_code + "\n" + content[end_idx:]
            with open(core_p, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched telegram_alert_loop in {core_p}")
        else:
            print(f"Could not find end marker in {core_p}")
    else:
        print(f"Could not find start marker in {core_p}")
