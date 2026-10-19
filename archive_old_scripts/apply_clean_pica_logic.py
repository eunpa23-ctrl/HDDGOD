# -*- coding: utf-8 -*-
import os

agent_path = r'C:\HDDGOD\client\client_agent.py'
with open(agent_path, 'r', encoding='utf-8') as f:
    content = f.read()

u_start = content.find('    def unlock_pica_screen(self):')
end_pos = content.find('    def show_update_complete_window(self):')

if u_start == -1 or end_pos == -1:
    print('Failed to find anchors:', u_start, end_pos)
    exit(1)

new_code = '''    def unlock_pica_screen(self):
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
            import psutil
            from client.screen_streamer import ensure_default_desktop

            ensure_default_desktop()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Per-Monitor DPI Awareness V2 활성화
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
            EM_SETSEL = 0x00B1
            WM_CLEAR = 0x0303
            VK_RETURN = 0x0D
            VK_BACK = 0x08
            VK_CONTROL = 0x11
            VK_A = 0x41

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

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

            pica_pids = set()
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if any(k in p.info['name'].lower() for k in ['pmclient', 'pmlc', 'pica']):
                        pica_pids.add(p.info['pid'])
                except Exception:
                    pass

            def dump_all_pica():
                top_hwnds = []
                def enum_top(h, lp):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                    if pid.value in pica_pids and user32.IsWindowVisible(h) and not user32.IsIconic(h):
                        top_hwnds.append((h, pid.value))
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top), 0)

                all_ctrls = []
                for th, pid_val in top_hwnds:
                    t_top = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(th, t_top, 256)
                    c_top = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(th, c_top, 256)
                    r_top = wintypes.RECT()
                    user32.GetWindowRect(th, ctypes.byref(r_top))
                    all_ctrls.append((th, c_top.value, t_top.value.strip(), 0, 0, (r_top.left, r_top.top, r_top.right, r_top.bottom), True, True))

                    def enum_ch(ch, lp):
                        if not user32.IsWindowVisible(ch):
                            return True
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        all_ctrls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom), True, False))
                        return True
                    user32.EnumChildWindows(th, WNDENUMPROC(enum_ch), 0)
                return all_ctrls, top_hwnds

            def find_admin_dialog_pair(ctrls):
                ok_candidate = None
                for c in ctrls:
                    ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                    t = txt.replace(' ', '')
                    if t in ['확인', 'OK'] and not is_top:
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        # 다이얼로그 확인 버튼 크기 (너비 30~130, 높이 15~55)
                        if 30 <= w <= 130 and 15 <= h <= 55:
                            ok_candidate = (ch, parent, rect, txt)
                            break

                if ok_candidate:
                    dlg_hwnd = ok_candidate[1]
                    for c in ctrls:
                        ch, cls_nm, txt, parent, cid, rect, is_vis, is_top = c
                        if parent == dlg_hwnd and 'edit' in cls_nm.lower():
                            return (ch, parent, rect), ok_candidate

                return None, None

            # [1단계: 이미 열려 있는 관리자 로그인 창 탐색]
            ctrls, tops = dump_all_pica()
            admin_edit, admin_ok = find_admin_dialog_pair(ctrls)

            if not admin_edit:
                logger.info("🔓 [피카 해제] 1단계: '관리자 로그인' 창 미발견 -> 단축키 Ctrl+Alt+Shift+X 전송...")
                for th, _ in tops:
                    user32.SetForegroundWindow(th)
                    time.sleep(0.05)
                    break

                user32.keybd_event(0x11, 0x1D, 0, 0)
                user32.keybd_event(0x10, 0x2A, 0, 0)
                user32.keybd_event(0x12, 0x38, 0, 0)
                user32.keybd_event(0x58, 0x2D, 0, 0)
                time.sleep(0.15)
                user32.keybd_event(0x58, 0x2D, 2, 0)
                user32.keybd_event(0x12, 0x38, 2, 0)
                user32.keybd_event(0x10, 0x2A, 2, 0)
                user32.keybd_event(0x11, 0x1D, 2, 0)

                for _ in range(25):
                    time.sleep(0.1)
                    ctrls, tops = dump_all_pica()
                    admin_edit, admin_ok = find_admin_dialog_pair(ctrls)
                    if admin_edit:
                        break

            # [2단계: 비밀번호 1234 단독 입력 및 확인 클릭]
            if admin_edit and admin_ok:
                e_hwnd, e_parent, e_rect = admin_edit
                ok_hwnd, ok_parent, ok_rect, ok_txt = admin_ok
                logger.info(f"🎯 관리자 로그인 다이얼로그 포착 완료! (Dialog HWND: {e_parent}, Edit HWND: {e_hwnd}, OK HWND: {ok_hwnd})")

                # 대화상자 포그라운드 활성화
                user32.SetForegroundWindow(e_parent)
                time.sleep(0.06)
                user32.SetFocus(e_hwnd)
                time.sleep(0.06)

                # Edit 박스 내부 마우스 클릭으로 확실한 포커스 위치
                cx = (e_rect[0] + e_rect[2]) // 2
                cy = (e_rect[1] + e_rect[3]) // 2
                user32.SetCursorPos(cx, cy)
                time.sleep(0.04)
                user32.mouse_event(2, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(0.06)

                # 기존 텍스트 완전 삭제 (Ctrl+A -> Backspace)
                user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
                user32.keybd_event(VK_A, 0x1E, 0, 0)
                time.sleep(0.04)
                user32.keybd_event(VK_A, 0x1E, 2, 0)
                user32.keybd_event(VK_CONTROL, 0x1D, 2, 0)
                time.sleep(0.04)

                for _ in range(12):
                    user32.keybd_event(VK_BACK, 0x0E, 0, 0)
                    time.sleep(0.02)
                    user32.keybd_event(VK_BACK, 0x0E, 2, 0)
                    time.sleep(0.02)

                user32.SendMessageW(e_hwnd, EM_SETSEL, 0, -1)
                user32.SendMessageW(e_hwnd, WM_CLEAR, 0, 0)
                time.sleep(0.06)

                # 순수 키보드 타이핑으로 비밀번호 4자리만 1회 주입
                logger.info(f"⌨️ 키보드 직접 타이핑으로 비밀번호 '{target_pw}' 주입 중...")
                for ch_digit in target_pw:
                    vk = ord(ch_digit)
                    sc = user32.MapVirtualKeyW(vk, 0)
                    user32.keybd_event(vk, sc, 0, 0)
                    time.sleep(0.05)
                    user32.keybd_event(vk, sc, 2, 0)
                    time.sleep(0.05)

                time.sleep(0.15)

                # 확인 버튼 클릭 (절대 종료 버튼 클릭 금지!)
                logger.info(f"🎯 로그인 확인 버튼('{ok_txt}', HWND: {ok_hwnd}) 클릭")
                click_control(ok_hwnd, ok_parent, ok_rect)

                # Enter 키 보조 전송
                user32.keybd_event(VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.08)
                user32.keybd_event(VK_RETURN, 0x1C, 2, 0)
                time.sleep(1.5)
            else:
                logger.warning("⚠️ '관리자 로그인' 창 쌍(Edit+OK)을 특정하지 못함!")

            # 최종 상태 확인
            if not self.is_pica_locked():
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
                    if pid.value in pica_pids and user32.IsWindowVisible(h) and not user32.IsIconic(h):
                        top_hwnds.append(h)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_top_proc), 0)

                for th in top_hwnds:
                    def enum_child_proc(ch, lp):
                        if not user32.IsWindowVisible(ch):
                            return True
                        c_cls = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(ch, c_cls, 256)
                        c_txt = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(ch, c_txt, 256)
                        cid = user32.GetDlgCtrlID(ch)
                        cr = wintypes.RECT()
                        user32.GetWindowRect(ch, ctypes.byref(cr))
                        controls.append((ch, c_cls.value, c_txt.value.strip(), th, cid, (cr.left, cr.top, cr.right, cr.bottom)))
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

            logger.info("🔒 [피카 잠금] '관리자 로그아웃' 버튼 탐색 및 복구 시도...")
            ctrls = get_all_pica_controls()
            logout_btn = None
            for ch, c_cls, c_txt, parent, cid, rect in ctrls:
                t = c_txt.replace(' ', '')
                if t in ['관리자로그아웃', '관리자로그아웃버튼']:
                    logout_btn = (ch, parent, rect, c_txt)
                    logger.info(f"🎯 1순위 '{c_txt}' 버튼(HWND:{ch}) 포착!")
                    break

            if not logout_btn:
                for ch, c_cls, c_txt, parent, cid, rect in ctrls:
                    t = c_txt.replace(' ', '')
                    if t in ['후불로그아웃', '로그아웃']:
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
                for ch, c_cls, c_txt, parent, cid, rect in ctrls2:
                    if c_txt in ['확인', '예', 'OK']:
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

content = content[:u_start] + new_code + '\n' + content[end_pos:]
with open(agent_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Successfully patched client_agent.py with pure keyboard typing!')
