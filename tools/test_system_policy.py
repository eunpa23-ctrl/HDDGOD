# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 시스템 정책 및 최적화 점검/테스트 도구
G:\내 드라이브\PROJECT\HDDGOD\tools\test_system_policy.py
"""
import os
import sys
import winreg
import ctypes
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def get_reg_val(root, subkey, name):
    try:
        key = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except Exception:
        return None

def main():
    print("=" * 65)
    print("  ⚡ [제우스 HDD PROTECTOR] 윈도우 시스템 정책 점검 도구")
    print("=" * 65)
    print(f"[*] 현재 실행 권한: {'👑 관리자 권한 (정상)' if is_admin() else '⚠️ 일반 사용자 권한 (관리자 필요)'}")
    print("-" * 65)

    # 1. 시작메뉴 전원 버튼 (NoClose)
    hkcu_noclose = get_reg_val(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoClose")
    hklm_noclose = get_reg_val(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoClose")
    noclose_status = "🔴 전원버튼 숨김 적용됨 (NoClose=1)" if (hkcu_noclose == 1 or hklm_noclose == 1) else "🟢 전원버튼 정상 표시 (기본값)"
    print(f"[1] 시작메뉴 시스템 종료 버튼: {noclose_status}")

    # 2. MS 참여/설정 방해화면 (SCOOBE)
    scoobe = get_reg_val(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled")
    scoobe_status = "🛡️ 방해화면 차단 적용됨 (0)" if scoobe == 0 else "⚪ 기본값 (방해화면 뜰 수 있음)"
    print(f"[2] MS '장치 설정 완료' SCOOBE: {scoobe_status}")

    # 3. MS 계정 전환 차단
    no_conn = get_reg_val(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "NoConnectedUser")
    no_conn_status = "🛡️ MS 계정 전환 차단 적용됨 (1)" if no_conn == 1 else "⚪ 기본값"
    print(f"[3] 로컬 계정 유지 (MS계정 차단): {no_conn_status}")

    # 4. 자동 업데이트 강제 재부팅 방지
    au = get_reg_val(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU", "NoAutoRebootWithLoggedOnUsers")
    au_status = "🛡️ 강제 재부팅 차단 적용됨 (1)" if au == 1 else "⚪ 기본값"
    print(f"[4] 손님 이용 중 업데이트 재부팅: {au_status}")

    # 5. UWF 순간복구 엔진 설치 여부
    import shutil
    uwf_exists = shutil.which("uwfmgr.exe") is not None or os.path.exists(r"C:\Windows\System32\uwfmgr.exe")
    print(f"[5] Windows UWF 순간복구 엔진: {'🟢 설치됨 (정상 작동 가능)' if uwf_exists else '⚪ 미설치 (테스트 가상 모드로 동작)'}")

    print("=" * 65)

if __name__ == "__main__":
    main()
