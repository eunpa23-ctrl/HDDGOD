import os

path = r'C:\HDDGOD\client\client_agent.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find def unlock_pica_screen and def show_update_complete_window
u_pos = content.find('    def unlock_pica_screen(self):')
end_pos = content.find('    def show_update_complete_window(self):')

if u_pos == -1 or end_pos == -1:
    print('Failed to locate anchors:', u_pos, end_pos)
    exit(1)

new_block = '''    def unlock_pica_screen(self):
        """PC 관리 에이전트(피카/PICA) 화면 잠금 해제 -> 관리자 로그인 수행 (피카 유지 및 카운터 관리자 표기)"""
        with self.pica_unlock_lock:
            now = time.time()
            if self.is_pica_unlocking or (now - self.last_pica_unlock_time < 3.0):
                logger.warning("⚠️ [피카 해제] 이미 잠금 해제가 진행 중이거나 최근 3초 내 실행됨 -> 중복 실행 방지 건너뜀")
                return
            self.is_pica_unlocking = True
            self.last_pica_unlock_time = now

        try:
            import ctypes
            from ctypes import wintypes
            import time
            import psutil
            from client.screen_streamer import ensure_default_desktop

            ensure_default_desktop()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Per-Monitor DPI Awareness V2 활성화 (해상도 및 DPI 왜곡 방지)
            try:
                user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        user32.SetProcessDPIAware()
                    except Exception:
                        pass

            BM_CLICK = 0x00F5
            BN_CLICKED = 0
            WM_COMMAND = 0x0111
            WM_SETTEXT = 0x000C
            EM_SETSEL = 0x00B1
            WM_CLEAR = 0x0303
            VK_RETURN = 0x0D
            VK_BACK = 0x08

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def get_all_pica_controls():
                controls = []
                top_hwnds = []
                pica_pids = set()
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        if any(k in p.info['name'].lower() for k in ['pmclient', 'pmlc', 'pica']):
                            pica_pids.add(p.info['pid'])
                    except Exception:
                        pass

                def enum_top_proc(h, lp):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pica_pids:
                        top_hwnds.append(h)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top_proc), 0)

                for th in top_hwnds:
                    def enum_child_proc(ch, lp):
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        is_vis = user32.IsWindowVisible(ch)
                        controls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom), is_vis))
                        return True
                    user32.EnumChildWindows(th, WNDENUMPROC(enum_child_proc), 0)
                return controls

            def click_control(hwnd, parent, rect=None):
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                user32.PostMessageW(hwnd, BM_CLICK, 0, 0)
                if parent:
                    cid = user32.GetDlgCtrlID(hwnd)
                    wparam = ((BN_CLICKED & 0xFFFF) << 16) | (cid & 0xFFFF)
                    user32.PostMessageW(parent, WM_COMMAND, wparam, hwnd)
                if rect:
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    if cx > 0 and cy > 0:
                        user32.SetCursorPos(cx, cy)
                        time.sleep(0.04)
                        user32.mouse_event(2, 0, 0, 0, 0)
                        time.sleep(0.04)
                        user32.mouse_event(4, 0, 0, 0, 0)

            target_pw = self.get_pica_admin_password()
            logger.info(f"🔑 [피카 관리자 로그인] 비밀번호: '{target_pw}' (카운터 '관리자' 동기화)")

            # 0. 이미 '관리자 로그아웃' 버튼이 존재하면 이미 관리자 로그인 완료 상태
            ctrls0 = get_all_pica_controls()
            for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls0:
                if is_vis and c_txt.replace(' ', '') in ['관리자로그아웃', '관리자로그아웃버튼']:
                    logger.info("🎉 [피카 해제] 이미 '관리자 로그아웃' 활성화 상태 -> 관리자 로그인 완료!")
                    return

            # 이전 오류 알림 팝업 정리
            for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls0:
                if is_vis and c_txt in ['확인', 'OK']:
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if 20 < w < 220 and 15 < h < 100:
                        logger.info(f"🎯 이전 오류 알림 팝업 '{c_txt}' 닫기 클릭!")
                        click_control(ch, parent, rect)
                        time.sleep(0.3)

            # [1단계: '관리자 로그인' 창 열기]
            ctrls = get_all_pica_controls()
            edit_box = None
            for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls:
                if is_vis and 'edit' in c_cls.lower():
                    edit_box = (ch, parent, rect)
                    logger.info(f"🎯 이미 열려 있는 비밀번호 Edit 박스(HWND: {ch}) 발견!")
                    break

            if not edit_box:
                logger.info("🔓 [피카 해제] 1단계: '관리자 로그인' 버튼 또는 단축키 전송...")
                admin_btn = None
                for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls:
                    t = c_txt.replace(' ', '')
                    if is_vis and t in ['관리자로그인', '관리자로그인버튼']:
                        admin_btn = (ch, parent, rect)
                        logger.info(f"🎯 '관리자 로그인' 버튼(HWND: {ch}) 포착!")
                        break

                if admin_btn:
                    user32.SetForegroundWindow(admin_btn[1])
                    time.sleep(0.05)
                    click_control(admin_btn[0], admin_btn[1], admin_btn[2])
                else:
                    logger.info("ℹ️ 단축키(Ctrl+Alt+Shift+X) 전송...")
                    user32.keybd_event(0x11, 0, 0, 0)
                    user32.keybd_event(0x12, 0, 0, 0)
                    user32.keybd_event(0x10, 0, 0, 0)
                    user32.keybd_event(0x58, 0, 0, 0)
                    time.sleep(0.12)
                    user32.keybd_event(0x58, 0, 2, 0)
                    user32.keybd_event(0x10, 0, 2, 0)
                    user32.keybd_event(0x12, 0, 2, 0)
                    user32.keybd_event(0x11, 0, 2, 0)

                # Edit 박스가 뜰 때까지 최대 2.0초 대기
                for _ in range(20):
                    time.sleep(0.1)
                    ctrls = get_all_pica_controls()
                    for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls:
                        if is_vis and 'edit' in c_cls.lower():
                            edit_box = (ch, parent, rect)
                            break
                    if edit_box:
                        break

            # [2단계: 비밀번호 1234 입력 및 확인]
            logger.info(f"🔓 [피카 해제] 2단계: 비밀번호 '{target_pw}' 주입 및 제출...")
            if edit_box:
                e_hwnd, e_parent, e_rect = edit_box
                logger.info(f"🎯 비밀번호 Edit 박스(HWND: {e_hwnd}) 포커스 설정")
                user32.SetForegroundWindow(e_parent)
                time.sleep(0.06)
                user32.SetFocus(e_hwnd)
                time.sleep(0.06)

                # Backspace 10회로 초기화
                for _ in range(10):
                    user32.keybd_event(VK_BACK, 0x0E, 0, 0)
                    user32.keybd_event(VK_BACK, 0x0E, 2, 0)

                # WM_SETTEXT로 주입
                try:
                    user32.SendMessageW(e_hwnd, EM_SETSEL, 0, -1)
                    user32.SendMessageW(e_hwnd, WM_CLEAR, 0, 0)
                    time.sleep(0.04)
                    user32.SendMessageW(e_hwnd, WM_SETTEXT, 0, ctypes.c_wchar_p(target_pw))
                    user32.SendMessageW(e_hwnd, EM_SETSEL, len(target_pw), len(target_pw))
                    time.sleep(0.05)
                except Exception as ex_set:
                    logger.warning(f"WM_SETTEXT 예외: {ex_set}")

                cur_len = user32.GetWindowTextLengthW(e_hwnd)
                if cur_len != len(target_pw):
                    # 키보드 직접 타이핑
                    for ch_digit in target_pw:
                        vk = ord(ch_digit)
                        sc = user32.MapVirtualKeyW(vk, 0)
                        user32.keybd_event(vk, sc, 0, 0)
                        time.sleep(0.04)
                        user32.keybd_event(vk, sc, 2, 0)
                        time.sleep(0.04)

                time.sleep(0.1)

                # [3단계: 확인 / 로그인 / 관리자 모드 변경 버튼 클릭]
                ctrls3 = get_all_pica_controls()
                ok_btn = None
                for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls3:
                    t = c_txt.replace(' ', '')
                    if is_vis and any(k in t for k in ['확인', '로그인', 'OK', '관리자모드변경']):
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if 25 < w < 250 and 15 < h < 100:
                            ok_btn = (ch, parent, rect)
                            break

                if ok_btn:
                    logger.info(f"🎯 로그인 확인 버튼(HWND: {ok_btn[0]}) 클릭")
                    click_control(ok_btn[0], ok_btn[1], ok_btn[2])

                # Enter 키 보조 전송
                user32.keybd_event(VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.08)
                user32.keybd_event(VK_RETURN, 0x1C, 2, 0)
                time.sleep(1.5)

            # 관리자 로그인 확인
            ctrls_final = get_all_pica_controls()
            has_admin = any(c[6] and c[2].replace(' ', '') in ['관리자로그아웃', '관리자로그아웃버튼'] for c in ctrls_final)
            if has_admin or not self.is_pica_locked():
                logger.info("🎉 [피카 해제 완료] 피카 관리자 로그인 100% 성공! (카운터 관리프로그램에 '관리자' 정상 표기)")
            else:
                logger.warning(f"⚠️ [피카 해제] 관리자 로그인 상태 확인 필요 (잠금 상태: {self.is_pica_locked()})")
        except Exception as e:
            logger.error(f"피카 해제 매크로 실행 오류: {e}")
        finally:
            self.is_pica_unlocking = False

    def lock_pica_screen(self):
        """PC 관리 에이전트(피카/PICA) 관리자 로그아웃 -> 화면보호기 잠금 복구 (카운터 정상 대기 복귀)"""
        try:
            import ctypes
            from ctypes import wintypes
            import time
            import psutil
            import subprocess
            from client.screen_streamer import ensure_default_desktop

            ensure_default_desktop()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            BM_CLICK = 0x00F5
            BN_CLICKED = 0
            WM_COMMAND = 0x0111
            VK_RETURN = 0x0D

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def get_all_pica_controls():
                controls = []
                top_hwnds = []
                pica_pids = set()
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        if any(k in p.info['name'].lower() for k in ['pmclient', 'pmlc', 'pica']):
                            pica_pids.add(p.info['pid'])
                    except Exception:
                        pass

                def enum_top_proc(h, lp):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pica_pids:
                        top_hwnds.append(h)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top_proc), 0)

                for th in top_hwnds:
                    def enum_child_proc(ch, lp):
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        is_vis = user32.IsWindowVisible(ch)
                        controls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom), is_vis))
                        return True
                    user32.EnumChildWindows(th, WNDENUMPROC(enum_child_proc), 0)
                return controls

            def click_control(hwnd, parent, rect=None):
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                user32.PostMessageW(hwnd, BM_CLICK, 0, 0)
                if parent:
                    cid = user32.GetDlgCtrlID(hwnd)
                    wparam = ((BN_CLICKED & 0xFFFF) << 16) | (cid & 0xFFFF)
                    user32.PostMessageW(parent, WM_COMMAND, wparam, hwnd)
                if rect:
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    if cx > 0 and cy > 0:
                        user32.SetCursorPos(cx, cy)
                        time.sleep(0.04)
                        user32.mouse_event(2, 0, 0, 0, 0)
                        time.sleep(0.04)
                        user32.mouse_event(4, 0, 0, 0, 0)

            # 0. 혹시 피카 프로세스가 꺼져 있다면 재실행
            pica_running = any(p.info['name'].lower() in ['pmclient.exe', 'pmlc.exe'] for p in psutil.process_iter(['name']))
            if not pica_running:
                logger.info("🔒 [피카 잠금] 피카 프로세스 미실행 -> 클라이언트 실행하여 복원")
                exe_to_run = getattr(self, 'pica_exe_path', r"C:\Program Files (x86)\PicaClient\pmclient.exe")
                if os.path.exists(exe_to_run):
                    subprocess.Popen([exe_to_run], shell=False)
                time.sleep(2.0)

            logger.info("🔒 [피카 잠금] '관리자 로그아웃' 버튼 탐색 및 복구 시도...")
            ctrls = get_all_pica_controls()
            logout_btn = None
            for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls:
                t = c_txt.replace(' ', '')
                if is_vis and t in ['관리자로그아웃', '관리자로그아웃버튼']:
                    logout_btn = (ch, parent, rect, c_txt)
                    logger.info(f"🎯 1순위 '{c_txt}' 버튼(HWND:{ch}) 포착!")
                    break

            if not logout_btn:
                for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls:
                    t = c_txt.replace(' ', '')
                    if is_vis and t in ['후불로그아웃', '로그아웃']:
                        logout_btn = (ch, parent, rect, c_txt)
                        logger.info(f"🎯 2순위 '{c_txt}' 버튼(HWND:{ch}) 포착!")
                        break

            if logout_btn:
                btn_hwnd, parent_hwnd, btn_rect, btn_title = logout_btn
                user32.SetForegroundWindow(parent_hwnd)
                time.sleep(0.05)
                click_control(btn_hwnd, parent_hwnd, btn_rect)
                logger.info(f"✅ '{btn_title}' 버튼 클릭 완료!")
                time.sleep(0.8)

                # 로그아웃 확인 다이얼로그 ("로그아웃 하시겠습니까?")
                ctrls2 = get_all_pica_controls()
                for ch, c_cls, c_txt, parent, cid, rect, is_vis in ctrls2:
                    if is_vis and c_txt in ['확인', '예', 'OK']:
                        logger.info(f"🎯 로그아웃 확인 다이얼로그 버튼('{c_txt}', HWND:{ch}) 클릭!")
                        click_control(ch, parent, rect)
                        break

                user32.keybd_event(VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(VK_RETURN, 0x1C, 2, 0)
                time.sleep(1.0)
                logger.info("🎉 [피카 잠금 완료] 관리자 로그아웃 완료 -> 화면보호기 잠금 정상 복귀!")
            else:
                logger.info("ℹ️ '관리자 로그아웃' 버튼이 없음 (이미 잠금 상태이거나 대기 화면)")
        except Exception as e:
            logger.error(f"피카 잠금 매크로 실행 오류: {e}")
'''

content = content[:u_pos] + new_block + '\n' + content[end_pos:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated client_agent.py successfully!')
