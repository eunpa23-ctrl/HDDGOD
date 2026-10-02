# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 관제 서버 무한 자동 재시작 감시자 (Crash Watchdog Supervisor)
- 관제 서버(run_server.py)가 예기치 않게 종료되거나 크래시 발생 시 2초 내에 즉시 자동 부활
- 윈도우 백그라운드 무음 상시 감시
"""
import os
import sys
import time
import subprocess
import json

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(ROOT_DIR, "server", ".supervisor_status.json")
STOP_FLAG_FILE = os.path.join(ROOT_DIR, "server", ".stop_supervisor")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def update_status(is_running: bool, restart_count: int, last_exit_code=None):
    try:
        data = {
            "supervisor_pid": os.getpid(),
            "is_running": is_running,
            "restart_count": restart_count,
            "last_exit_code": last_exit_code,
            "last_heartbeat": time.time()
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def main():
    if os.path.exists(STOP_FLAG_FILE):
        try:
            os.remove(STOP_FLAG_FILE)
        except Exception:
            pass

    restart_count = 0
    print("[*] 제우스 관제 서버 무한 자동 재시작 감시자(Supervisor) 가동")

    while True:
        if os.path.exists(STOP_FLAG_FILE):
            print("[*] 정지요청 플래그 감지 -> 감시자 종료")
            try:
                os.remove(STOP_FLAG_FILE)
            except Exception:
                pass
            update_status(False, restart_count, 0)
            break

        update_status(True, restart_count)
        
        # run_server.py 실행
        cmd = [sys.executable, "run_server.py"]
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT_DIR)
            while proc.poll() is None:
                update_status(True, restart_count)
                if os.path.exists(STOP_FLAG_FILE):
                    print("[*] 정지요청 플래그 감지 -> 서버 프로세스 종료")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                    break
                time.sleep(2)

            exit_code = proc.returncode
            update_status(False, restart_count, exit_code)

            # 정상 종료(0) 또는 Ctrl+C(3221225786 등)로 종료된 경우
            if exit_code == 0 or os.path.exists(STOP_FLAG_FILE):
                print(f"[*] 서버 정상 종료 감지 (종료 코드: {exit_code})")
                break

            restart_count += 1
            print(f"[!] 서버 비정상 종료 감지 (코드: {exit_code}) -> 2초 후 자동 부활 (#{restart_count})")
            time.sleep(2)

        except Exception as e:
            print(f"[!] 감시자 예외 발생: {e}")
            time.sleep(3)

    update_status(False, restart_count)

if __name__ == "__main__":
    main()
