# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 넷플릭스 CDP 자동화 & 격리 프로필 봇
G:\내 드라이브\PROJECT\HDDGOD\client\netflix_bot.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import json
import logging
import subprocess
import requests
try:
    from websockets.sync.client import connect as ws_connect
except ImportError:
    ws_connect = None
from common.config import (
    NETFLIX_EMAIL,
    NETFLIX_PASSWORD,
    CHROME_CDP_PORT,
    NETFLIX_PROFILE_DIR,
    config
)
from common.protocol import NetflixStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NetflixBot")

class NetflixBot:
    """크롬 CDP(포트 9222)를 이용한 넷플릭스 DRM 우회 자동화 및 4자리 OTP 자동 타이핑"""

    def __init__(self):
        self.cdp_port = CHROME_CDP_PORT
        self.profile_dir = NETFLIX_PROFILE_DIR
        self.start_url = config.get('NETFLIX', 'START_URL', fallback='https://www.netflix.com')
        self.ws_url = None
        self.current_status = NetflixStatus.CLOSED

    def find_chrome_path(self) -> str:
        # 1. 윈도우 레지스트리 App Paths 조회 (가장 정확한 설치 경로)
        import winreg
        for app in ["chrome.exe", "msedge.exe", "whale.exe"]:
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app}") as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    pass

        # 2. 일반적인 기본 설치 경로 폴백
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "chrome.exe"

    def ensure_desktop_shortcut(self) -> bool:
        """바탕화면에 넷플릭스 전용 아이콘 바로가기(.lnk) 생성"""
        chrome_exe = self.find_chrome_path()
        icon_path = os.path.join(self.profile_dir, "netflix.ico")
        local_ico = r"C:\ZeusAgent\netflix.ico"

        # 아이콘 파일 확보 (로컬 배포본 우선 복사 -> 인터넷 다운로드 시도)
        if not os.path.exists(icon_path):
            try:
                os.makedirs(self.profile_dir, exist_ok=True)
                if os.path.exists(local_ico):
                    import shutil
                    shutil.copy2(local_ico, icon_path)
                else:
                    import urllib.request
                    urllib.request.urlretrieve("https://assets.nflxext.com/ffe/siteui/common/icons/nficon2016.ico", icon_path)
            except Exception as e:
                logger.debug(f"아이콘 복사/다운로드 건너뜀: {e}")

        # 1. 실행기 타깃 결정:
        # 크롬/엣지 실행 파일이 존재하면 직접 CDP 인자 장착하여 바로가기 생성 (딜레이 제로 즉시 기동)
        if chrome_exe and chrome_exe != "chrome.exe" and os.path.exists(chrome_exe):
            target_path = chrome_exe
            target_args = f'--remote-debugging-port={self.cdp_port} --user-data-dir="{self.profile_dir}" --start-maximized --no-first-run --no-default-browser-check --disable-popup-blocking "{self.start_url}"'
            work_dir = os.path.dirname(chrome_exe)
        else:
            zeus_exe = r"C:\ZeusAgent\ZeusAgent.exe"
            if os.path.exists(zeus_exe):
                target_path = zeus_exe
                target_args = "--launch-netflix"
                work_dir = r"C:\ZeusAgent"
            else:
                pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
                launcher_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_netflix.py")
                target_path = pythonw_exe
                target_args = f'"{launcher_py}"'
                work_dir = os.path.dirname(launcher_py)

        # 2. 바탕화면 바로가기(.lnk) 생성 (사용자 및 공용 바탕화면)
        desktop_dirs = []
        user_desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        if os.path.exists(user_desktop):
            desktop_dirs.append(user_desktop)
        public_desktop = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")
        if os.path.exists(public_desktop):
            desktop_dirs.append(public_desktop)

        final_icon = icon_path if os.path.exists(icon_path) else (local_ico if os.path.exists(local_ico) else target_path)

        for d_dir in desktop_dirs:
            lnk_path = os.path.join(d_dir, "넷플릭스.lnk")
            try:
                ps_script = f"""
                $ws = New-Object -ComObject WScript.Shell
                $s = $ws.CreateShortcut('{lnk_path}')
                $s.TargetPath = '{target_path}'
                $s.Arguments = '{target_args}'
                $s.WorkingDirectory = '{work_dir}'
                if (Test-Path '{final_icon}') {{ $s.IconLocation = '{final_icon},0' }}
                $s.Save()
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=5)
            except Exception as e:
                logger.warning(f"바로가기 생성 건너뜀 ({lnk_path}): {e}")

        logger.info("바탕화면 [넷플릭스.lnk] 바로가기 보장 완료")
        return True

    def _clean_chrome_profile(self):
        """크롬 비정상 종료 시 나타나는 '페이지 복구' 팝업을 영구 제거 및 강제 삭제"""
        import json, glob
        # 1. Preferences 파일 수정
        pref_path = os.path.join(self.profile_dir, "Default", "Preferences")
        if os.path.exists(pref_path):
            try:
                with open(pref_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "profile" not in data:
                    data["profile"] = {}
                data["profile"]["exit_type"] = "Normal"
                data["profile"]["exited_cleanly"] = True
                with open(pref_path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception:
                pass
        
        # 2. 세션 복구 파일 강제 삭제 (이게 확실함)
        default_dir = os.path.join(self.profile_dir, "Default")
        if os.path.exists(default_dir):
            for filename in ["Last Session", "Last Tabs", "Current Session", "Current Tabs"]:
                try:
                    target = os.path.join(default_dir, filename)
                    if os.path.exists(target):
                        os.remove(target)
                except Exception:
                    pass
            # Sessions 폴더가 있는 최신 크롬 대응
            sessions_dir = os.path.join(default_dir, "Sessions")
            if os.path.exists(sessions_dir):
                for f in glob.glob(os.path.join(sessions_dir, "*")):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    def launch_chrome_with_cdp(self) -> bool:
        """손님 프로필과 완전히 분리된 넷플릭스 전용 프로필로 크롬 실행"""
        os.makedirs(self.profile_dir, exist_ok=True)
        self._clean_chrome_profile()
        
        chrome_exe = self.find_chrome_path()

        cmd = [
            chrome_exe,
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={self.profile_dir}",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--hide-crash-restore-bubble",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            self.start_url
        ]

        logger.info(f"넷플릭스 전용 크롬 실행 (CDP 포트 {self.cdp_port}, 프로필 {self.profile_dir})")
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
            subprocess.Popen(cmd, creationflags=creationflags)
            return True
        except Exception as e:
            logger.error(f"크롬 실행 실패: {e}")
            return False

    def is_cdp_available(self) -> bool:
        """CDP HTTP 엔드포인트 활성화 여부 확인"""
        try:
            resp = requests.get(f"http://127.0.0.1:{self.cdp_port}/json", timeout=1)
            return resp.status_code == 200
        except Exception:
            return False

    def connect_cdp(self, retries=5) -> bool:
        """CDP HTTP 엔드포인트에서 활성 넷플릭스 탭의 WebSocket URL 검색 (항상 최신 탭 조회)"""
        self.ws_url = None
        url = f"http://127.0.0.1:{self.cdp_port}/json"
        for _ in range(retries):
            try:
                resp = requests.get(url, timeout=2)
                if resp.status_code == 200:
                    targets = resp.json()
                    # 1순위: 넷플릭스 탭
                    for target in targets:
                        t_url = target.get("url", "")
                        if target.get("type") == "page" and ("netflix.com" in t_url or "about:blank" in t_url):
                            self.ws_url = target.get("webSocketDebuggerUrl")
                            logger.info(f"CDP WebSocket 연결 대상 확보: {self.ws_url}")
                            return True
                    # 2순위: 기타 활성 탭
                    for target in targets:
                        if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                            self.ws_url = target.get("webSocketDebuggerUrl")
                            return True
            except Exception:
                time.sleep(1)
        logger.warning("CDP 엔드포인트 연결 대기 중...")
        return False

    def eval_js(self, expression: str) -> dict:
        """CDP를 통해 자바스크립트 실행 (창 닫힘/재실행 시 자동 탭 갱신)"""
        if not ws_connect:
            return {}

        if not self.is_cdp_available():
            self.ws_url = None
            return {}

        if not self.ws_url and not self.connect_cdp(retries=2):
            return {}

        try:
            with ws_connect(self.ws_url, open_timeout=2, close_timeout=1) as ws:
                payload = {
                    "id": int(time.time() * 1000) % 100000,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": True
                    }
                }
                ws.send(json.dumps(payload))
                res = json.loads(ws.recv(timeout=8.0))
                return res.get("result", {}).get("result", {}).get("value", {})
        except Exception as e:
            # 탭이 새로 열렸거나 변경되었을 경우 ws_url 초기화 후 1회 재시도
            self.ws_url = None
            if self.connect_cdp(retries=2):
                try:
                    with ws_connect(self.ws_url, open_timeout=2, close_timeout=1) as ws:
                        payload = {
                            "id": int(time.time() * 1000) % 100000,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": expression,
                                "returnByValue": True,
                                "awaitPromise": True
                            }
                        }
                        ws.send(json.dumps(payload))
                        res = json.loads(ws.recv(timeout=8.0))
                        return res.get("result", {}).get("result", {}).get("value", {})
                except Exception as e2:
                    logger.error(f"CDP 재연결 후 JS 실행 재실패: {e2}")
                    self.ws_url = None
            return {}

    def check_and_handle_login(self) -> str:
        """넷플릭스 로그인 상태 점검 및 자동 분기 처리"""
        if not self.is_cdp_available():
            self.ws_url = None
            self.current_status = NetflixStatus.CLOSED
            return self.current_status

        check_script = """
        (function() {
            var url = window.location.href;
            
            // 1. 이미 로그인된 상태 (/browse 또는 프로필 선택 화면)
            if (url.indexOf('/browse') !== -1 || document.querySelector('.profile-icon, .avatar-wrapper, [data-uia="profile-link"], [data-uia="header-profile-menu"]')) {
                return { status: 'LOGGED_IN', url: url };
            }

            // 2. 4자리 OTP 인증 화면 감지
            if (document.querySelector('input[type="tel"]') || 
                document.querySelector('input[name*="code"]') ||
                document.querySelector('input[data-uia*="otp"]') ||
                document.body.innerText.indexOf('인증 코드') !== -1 ||
                document.body.innerText.indexOf('임시 코드') !== -1 ||
                document.body.innerText.indexOf('확인 코드') !== -1) {
                return { status: 'OTP_WAITING', url: url };
            }

            // 2.5 넷플릭스 일시적 차단 / 쿨다운 에러 감지 (무한 반복 방지)
            if (document.body.innerText.indexOf('오류가 발생했습니다') !== -1 || document.body.innerText.indexOf('다시 시도해 주시기 바랍니다') !== -1) {
                return { status: 'RATE_LIMITED', url: url };
            }

            // 3. 로그인 폼이 있는 /login 페이지
            if (url.indexOf('/login') !== -1 || document.querySelector('input[name="userLoginId"], input[type="password"]')) {
                return { status: 'NEED_LOGIN', url: url };
            }

            // 4. 메인 랜딩 페이지에 머물러 있는 경우 -> /login으로 이동 유도
            var loginLink = document.querySelector('a[href*="/login"], [data-uia="header-login-button"]');
            if (loginLink) {
                loginLink.click();
                return { status: 'NAVIGATING_TO_LOGIN', url: url };
            } else if (url.indexOf('netflix.com') !== -1) {
                window.location.href = 'https://www.netflix.com/login';
                return { status: 'NAVIGATING_TO_LOGIN', url: url };
            } else if (url === 'about:blank' || url.indexOf('netflix.com') === -1) {
                window.location.href = 'https://www.netflix.com/browse';
                return { status: 'NAVIGATING_TO_LOGIN', url: url };
            }

            return { status: 'UNKNOWN', url: url };
        })()
        """
        result = self.eval_js(check_script)
        if not isinstance(result, dict) or not result:
            self.current_status = NetflixStatus.RUNNING
            return self.current_status

        status = result.get("status", "UNKNOWN")
        logger.info(f"넷플릭스 현재 상태 감지: {status} ({result.get('url', '')})")

        if status == "LOGGED_IN":
            self.current_status = NetflixStatus.LOGGED_IN
            return self.current_status
        elif status == "OTP_WAITING":
            self.current_status = NetflixStatus.OTP_WAITING
            return self.current_status
        elif status == "RATE_LIMITED":
            logger.warning("⚠️ [NetflixBot] 넷플릭스 요청 제한(Rate Limit/쿨다운) 감지: 15초간 대기합니다.")
            self.current_status = NetflixStatus.RUNNING
            time.sleep(15)
            return self.current_status
        elif status == "NAVIGATING_TO_LOGIN":
            time.sleep(2)
            return self.check_and_handle_login()
        elif status == "NEED_LOGIN":
            # 자동 로그인 시도
            res = self.do_auto_login()
            logger.info(f"자동 로그인 실행 결과: {res}")
            time.sleep(3)
            # 로그인 후 상태 재점검
            second_check = self.eval_js(check_script)
            second_status = second_check.get("status") if isinstance(second_check, dict) else "UNKNOWN"
            if second_status == "OTP_WAITING":
                self.current_status = NetflixStatus.OTP_WAITING
            elif second_status == "LOGGED_IN":
                self.current_status = NetflixStatus.LOGGED_IN
            else:
                self.current_status = NetflixStatus.RUNNING
            return self.current_status

        self.current_status = NetflixStatus.RUNNING
        return self.current_status

    def send_cdp_command(self, method: str, params: dict) -> dict:
        """CDP 원시 명령어 전송 (키보드 타이핑 등)"""
        if not ws_connect: return {}
        if not self.ws_url and not self.connect_cdp(retries=2): return {}
        try:
            with ws_connect(self.ws_url, open_timeout=2, close_timeout=1) as ws:
                payload = {
                    "id": int(time.time() * 1000) % 100000,
                    "method": method,
                    "params": params
                }
                ws.send(json.dumps(payload))
                res = json.loads(ws.recv(timeout=5.0))
                return res
        except Exception:
            return {}

    def do_auto_login(self) -> dict:
        """CDP 원격 제어(Input.insertText)를 통해 실제 키보드 타이핑처럼 ID/PW 강제 입력
        넷플릭스는 이메일 입력 → 다음 버튼 → 비밀번호 입력의 2단계 구조임에 주의
        """
        logger.info("넷플릭스 ID/PW 자동 로그인 시도 중 (CDP 타이핑 2단계)...")

        # === STEP 1: 이메일 입력창 포커스 및 입력 ===
        focus_email_js = """
        (function() {
            var el = document.querySelector(
                'input[data-uia="field-userLoginId"], input[name="userLoginId"], input[type="email"], #id_userLoginId'
            );
            if (el) { el.focus(); el.select(); return true; }
            return false;
        })()
        """
        if not self.eval_js(focus_email_js):
            return {"success": False, "message": "이메일 입력창을 찾지 못함"}

        time.sleep(0.2)
        # 기존 내용 전체 지우기 (Ctrl+A → Delete)
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2  # Ctrl
        })
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "a", "code": "KeyA"
        })
        time.sleep(0.1)
        self.send_cdp_command("Input.insertText", {"text": NETFLIX_EMAIL})
        time.sleep(0.4)

        # === STEP 2: "Enter" 키 입력 ("다음" 버튼 클릭 효과) ===
        # 비밀번호 입력창이 이미 있으면 Enter 생략
        pw_check_js = """
        (function() {
            var pw = document.querySelector('input[type="password"], input[name="password"], input[data-uia="field-password"]');
            return pw ? true : false;
        })()
        """
        has_pw = self.eval_js(pw_check_js)

        if not has_pw:
            # 비밀번호 입력창이 없음 = 이메일만 받는 1페이지 → Enter 키 눌러서 "다음"으로 넘어가기
            logger.info("넷플릭스 2단계 로그인: 이메일 입력 후 Enter 키 전송, 비밀번호 창 대기 중...")
            self.send_cdp_command("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
            })
            self.send_cdp_command("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
            })
            time.sleep(2.5)  # 화면 전환 대기

        # === STEP 3: 비밀번호 입력창 포커스 및 입력 ===
        focus_pass_js = """
        (function() {
            var el = document.querySelector(
                'input[type="password"], input[name="password"], input[data-uia="field-password"], #id_password'
            );
            if (el) { el.focus(); el.select(); return true; }
            return false;
        })()
        """
        found_pw = self.eval_js(focus_pass_js)
        if found_pw:
            time.sleep(0.2)
            self.send_cdp_command("Input.insertText", {"text": NETFLIX_PASSWORD})
            time.sleep(0.5)
            logger.info("비밀번호 입력 완료")
        else:
            logger.warning("비밀번호 입력창을 찾지 못했습니다.")
            return {"success": False, "message": "비밀번호 입력창 미발견"}

        # === STEP 4: 로그인 제출 버튼 클릭 또는 Enter 전송 ===
        submit_js = """
        (function() {
            var remember = document.querySelector('input[name="rememberMe"], input[data-uia*="remember-me"]');
            if (remember && !remember.checked) { remember.click(); }
        })()
        """
        self.eval_js(submit_js)
        
        # 비밀번호 창에서 Enter 전송하여 최종 로그인
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
        })
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13
        })

        logger.info("로그인 최종 엔터(Enter) 전송 완료!")
        return {"success": True, "message": "CDP 2단계 로그인 완료"}

    def input_otp_code(self, code_str: str) -> bool:
        """전달받은 4자리 OTP 코드를 크롬 화면에 0.1초 만에 자동 타이핑"""
        logger.info(f"넷플릭스 4자리 인증번호 [{code_str}] 자동 입력 실행!")
        code_str = code_str.strip()
        otp_script = f"""
        (function() {{
            function setNativeVal(el, val) {{
                if (!el) return false;
                var lastValue = el.value;
                el.value = val;
                var event = new Event('input', {{ bubbles: true }});
                var tracker = el._valueTracker;
                if (tracker) tracker.setValue(lastValue);
                el.dispatchEvent(event);
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}

            var code = '{code_str}';
            var inputs = document.querySelectorAll('input[type="tel"], input[name*="code"], input[data-uia*="otp"]');
            if (inputs.length >= 4) {{
                for (var i = 0; i < 4; i++) {{
                    setNativeVal(inputs[i], code[i] || '');
                }}
            }} else if (inputs.length === 1) {{
                setNativeVal(inputs[0], code);
            }}
            
            setTimeout(function() {{
                var submitBtn = document.querySelector('button[data-uia*="submit"], button[type="submit"]');
                if (submitBtn) submitBtn.click();
            }}, 300);

            return true;
        }})()
        """
        res = self.eval_js(otp_script)
        logger.info(f"OTP 입력 결과: {res}")
        return True

if __name__ == "__main__":
    bot = NetflixBot()
    bot.launch_chrome_with_cdp()
    bot.connect_cdp()
    print("넷플릭스 봇 상태:", bot.check_and_handle_login())
