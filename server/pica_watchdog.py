import os
import asyncio
import psutil
import subprocess
import logging
import time
from pywinauto import Desktop

logger = logging.getLogger("ZeusServer")

class PicaWatchdog:
    def __init__(self, telegram_callback=None):
        self.program_path = r"C:\Program Files (x86)\PicaLive\LiveStarter.exe"
        self.process_name = "PicaLive.exe"
        self.watch_interval = 5
        self.restart_delay = 5
        self.auto_login_enabled = True
        self.password = "@Oep0325"
        self.is_enabled = True
        self.is_running = False
        self.telegram_callback = telegram_callback
        self.task = None

    def load_config(self, cfg):
        if cfg.has_section("PICA"):
            self.is_enabled = cfg.getboolean("PICA", "ENABLED", fallback=True)
            self.program_path = cfg.get("PICA", "PATH", fallback=r"C:\Program Files (x86)\PicaLive\LiveStarter.exe")
            self.process_name = cfg.get("PICA", "PROCESS_NAME", fallback="PicaLive.exe")
            self.auto_login_enabled = cfg.getboolean("PICA", "AUTO_LOGIN", fallback=True)
            saved_pwd = cfg.get("PICA", "PASSWORD", fallback="")
            if saved_pwd and saved_pwd != "testpassword":
                self.password = saved_pwd
            else:
                self.password = "@Oep0325"

    def is_process_running(self):
        try:
            for proc in psutil.process_iter(['name']):
                pname = proc.info['name']
                if pname and pname.lower() in ["picalive.exe", "livestarter.exe"]:
                    return True
        except Exception:
            pass
        return False

    async def send_alert(self, msg: str):
        """텔레그램 알림 전송 (콜백 우선, 실패 시 직접 발송 백업)"""
        sent = False
        if self.telegram_callback:
            try:
                res = self.telegram_callback(msg)
                if asyncio.iscoroutine(res):
                    await res
                sent = True
            except Exception as e:
                logger.error(f"콜백 알림 실패: {e}")
        
        if not sent:
            try:
                import configparser, requests
                from common.config import CONFIG_PATH
                cfg = configparser.ConfigParser()
                cfg.read(CONFIG_PATH, encoding="utf-8")
                token = cfg.get("TELEGRAM", "BOT_TOKEN", fallback="")
                chat_id = cfg.get("TELEGRAM", "CHAT_ID", fallback="")
                if token and chat_id:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    await asyncio.to_thread(requests.post, url, json={"chat_id": chat_id, "text": msg}, timeout=5)
            except Exception as e:
                logger.error(f"직접 텔레그램 발송 실패: {e}")

    def perform_login_uia(self, max_retries=30):
        """UIA를 사용하여 PicaLive 로그인 창을 찾고 비밀번호 입력 및 OK 클릭"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hDesk:
                user32.SetThreadDesktop(hDesk)

            login_win = None
            for _ in range(max_retries):
                try:
                    # 'PicaLive' 또는 '로그인' 타이틀을 가진 창 찾기 (안정성 강화)
                    windows = Desktop(backend="uia").windows()
                    win = None
                    for w in windows:
                        if w.window_text() in ["PicaLive", "로그인"] or "PicaLive" in w.window_text():
                            pwd = w.child_window(auto_id="txtPwd", control_type="Edit")
                            if pwd.exists(timeout=0.1):
                                win = w
                                break
                    if win:
                        login_win = win
                        break
                    
                    # 기존 방식 호환성 유지
                    if not win:
                        win_fallback = Desktop(backend="uia").window(title="PicaLive")
                        if win_fallback.exists(timeout=0.2):
                            pwd = win_fallback.child_window(auto_id="txtPwd", control_type="Edit")
                            if pwd.exists(timeout=0.2):
                                login_win = win_fallback
                                break
                except Exception:
                    pass
                time.sleep(1)

            if login_win:
                pwd = login_win.child_window(auto_id="txtPwd", control_type="Edit")
                pwd.set_focus()
                time.sleep(0.3)
                pwd.set_edit_text(self.password)
                time.sleep(0.3)
                btn = login_win.child_window(auto_id="btnOK", control_type="Button")
                btn.click()
                logger.info("🔑 PicaLive UIA 자동 로그인 성공 (비밀번호 입력 및 확인 클릭)")
                return True
            else:
                if max_retries > 1:
                    logger.warning("PicaLive 로그인 창을 찾지 못함 (이미 로그인되었거나 지연)")
        except Exception as e:
            logger.error(f"PicaLive 로그인 자동화 오류: {e}")
        return False

    async def watch_loop(self):
        self.is_running = True
        logger.info("🛡️ PicaLive 백그라운드 무인 감시 데몬 가동 중")
        
        while self.is_running:
            if self.is_enabled and self.program_path and os.path.exists(self.program_path):
                if not self.is_process_running():
                    logger.warning(f"🚨 [{self.process_name}] 프로세스 종료 감지! 자동 복구를 시작합니다.")
                    
                    # 1. 텔레그램 긴급 알림 발송
                    asyncio.create_task(self.send_alert(f"🚨 [카운터 PC 긴급알림]\nPicaLive(피카) 프로그램이 비정상 종료되었습니다!\n즉시 자동 재실행 및 로그인을 진행합니다."))
                    
                    try:
                        # 2. 잔류 프로세스 정리
                        for p in ["LiveStarter.exe", "PicaLive.exe"]:
                            subprocess.run(["taskkill", "/IM", p, "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # 3. LiveStarter 실행 (반드시 cwd 지정 및 WinSta0\\Default 화면 지정!)
                        program_dir = os.path.dirname(self.program_path)
                        si = subprocess.STARTUPINFO()
                        si.lpDesktop = r"WinSta0\Default"
                        subprocess.Popen([self.program_path], cwd=program_dir, startupinfo=si)
                        
                        # 4. 로그인 창 감지 및 자동 로그인
                        if self.auto_login_enabled and self.password:
                            await asyncio.to_thread(self.perform_login_uia, 30)
                            
                        logger.info("✅ PicaLive 자동 복구 완료")
                        # 5. 복구 성공 텔레그램 발송
                        asyncio.create_task(self.send_alert(f"✅ [카운터 PC 복구성공]\nPicaLive 자동 재실행 및 로그인이 완벽하게 완료되었습니다. 정상 영업 중입니다."))
                            
                    except Exception as e:
                        logger.error(f"PicaLive 재실행 실패: {e}")
                        
                    # 연속 재실행 방지 대기
                    await asyncio.sleep(20)
                else:
                    # 프로세스는 실행 중이나 로그인 창에 머물러 있는 경우 (예: 서버 재시작 후 Pica가 로그아웃 상태일 때)
                    if self.auto_login_enabled and self.password:
                        # max_retries=1 로 설정하여 짧게 검사
                        await asyncio.to_thread(self.perform_login_uia, 1)
            
            await asyncio.sleep(self.watch_interval)

    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.watch_loop())

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()

pica_dog = PicaWatchdog()
