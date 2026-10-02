# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 24시간 무인 전원 및 볼륨/절전 제어 모듈
G:\내 드라이브\PROJECT\HDDGOD\client\power_policy.py
"""
import os
import subprocess
import winreg
import logging
from common.config import DEFAULT_VOLUME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PowerPolicy")

class PowerPolicy:
    """전원 정책, 볼륨 100% 고정, 모니터 절전 차단, 전원버튼 봉쇄 관리자"""

    @staticmethod
    def run_cmd(cmd_list: list) -> str:
        try:
            res = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                check=False,
                encoding="cp949",
                errors="ignore"
            )
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"명령어 실패 {cmd_list}: {e}")
            return ""

    @classmethod
    def set_master_volume_100(cls) -> None:
        """마스터 볼륨을 100%로 강제 설정하고 음소거를 해제"""
        logger.info(f"스피커 마스터 볼륨 {DEFAULT_VOLUME}% 설정 및 음소거 해제 중...")
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            volume = getattr(speakers, "EndpointVolume", None)
            if volume is None and hasattr(speakers, "Activate"):
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume
                interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

            if volume:
                volume.SetMute(0, None)  # 음소거 해제
                volume.SetMasterVolumeLevelScalar(DEFAULT_VOLUME / 100.0, None)  # 1.0 = 100%
                logger.info(f"스피커 마스터 볼륨 {DEFAULT_VOLUME}% 설정 성공!")
                return
        except Exception as e:
            logger.debug(f"pycaw 볼륨 제어 실패: {e}")

        # 2차 시도: PowerShell WScript.Shell 가상 볼륨키 연타 (최대치로 올림)
        ps_script = """
        $wsh = New-Object -ComObject Wscript.Shell
        # 음소거 해제 위해 볼륨업 키 반복 전송
        for ($i=0; $i -lt 50; $i++) {
            $wsh.SendKeys([char]175) # Volume Up
        }
        """
        cls.run_cmd(["powershell.exe", "-NoProfile", "-Command", ps_script])

    @classmethod
    def apply_power_safety(cls) -> None:
        """24시간 무인 매장 전원 정책 적용 (빠른시작 OFF, 절전 OFF, 전원버튼 DoNothing)"""
        logger.info("24시간 무인 전원 및 절전 정책 적용 시작...")

        # 1. 빠른 시작(Fast Startup) 끄기 - WOL 완벽 수신 필수
        cls.run_cmd(["powercfg.exe", "/h", "off"])

        # 2. 모니터 꺼짐 및 절전 모드 영구 차단 (0 = 사용 안 함)
        cls.run_cmd(["powercfg.exe", "/change", "monitor-timeout-ac", "0"])
        cls.run_cmd(["powercfg.exe", "/change", "standby-timeout-ac", "0"])
        cls.run_cmd(["powercfg.exe", "/change", "hibernate-timeout-ac", "0"])

        # 3. 본체 전원 버튼 눌렀을 때 '아무것도 안 함' (0 = Do Nothing)
        cls.run_cmd(["powercfg.exe", "-setacvalueindex", "SCHEME_CURRENT", "SUB_BUTTONS", "PBUTTONACTION", "0"])
        cls.run_cmd(["powercfg.exe", "-SetActive", "SCHEME_CURRENT"])

    @classmethod
    def hide_only_shutdown_keep_restart(cls) -> bool:
        """시작메뉴에서 '시스템 종료'만 숨기고 '다시 시작(재부팅)'은 유지 (HideShutDown=1)"""
        logger.info("시작메뉴 종료 숨김 및 다시 시작 유지 정책 적용 중...")
        # 1. NoClose는 전체 전원 메뉴를 차단하므로 무조건 삭제
        cls.restore_shutdown_button()
        
        # 2. Windows 10/11 PolicyManager HideShutDown 정책 적용 (시스템 종료만 숨김)
        cls.run_cmd(["reg", "add", r"HKLM\SOFTWARE\Microsoft\PolicyManager\default\Start\HideShutDown", "/v", "value", "/t", "REG_DWORD", "/d", "1", "/f"])
        cls.run_cmd(["reg", "add", r"HKLM\SOFTWARE\Microsoft\PolicyManager\current\device\Start", "/v", "HideShutDown", "/t", "REG_DWORD", "/d", "1", "/f"])
        cls.run_cmd(["reg", "add", r"HKLM\SOFTWARE\Microsoft\PolicyManager\default\Start\HideRestart", "/v", "value", "/t", "REG_DWORD", "/d", "0", "/f"])
        logger.info("시작메뉴 '시스템 종료 숨김 / 다시 시작 유지' 적용 완료")
        return True

    @classmethod
    def hide_shutdown_button(cls) -> bool:
        """하위 호환성 유지: 시스템 종료만 숨기고 다시 시작은 유지하도록 위임"""
        return cls.hide_only_shutdown_keep_restart()

    @classmethod
    def restore_shutdown_button(cls) -> bool:
        """시작메뉴 전원 버튼 전체 복원 (NoClose 삭제 및 HideShutDown 해제)"""
        logger.info("시작메뉴 전원 버튼 복원 중...")
        reg_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer")
        ]
        for root_key, sub_key in reg_paths:
            try:
                key = winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, "NoClose")
                winreg.CloseKey(key)
            except Exception:
                pass
        return True

    @classmethod
    def restart_explorer(cls) -> None:
        """작업표시줄 재시작 (시작메뉴 정책 즉각 새로고침)"""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.Popen(["explorer.exe"])
            logger.info("작업표시줄(explorer.exe) 새로고침 완료")
        except Exception as e:
            logger.warning(f"explorer.exe 재시작 실패: {e}")

    @classmethod
    def setup_nic_wol(cls) -> None:
        """랜카드 고급 설정에서 WOL 매직패킷 수신 활성화"""
        ps_cmd = """
        Get-NetAdapter | ForEach-Object {
            Enable-NetAdapterPowerManagement -Name $_.Name -WakeOnMagicPacket -ErrorAction SilentlyContinue
        }
        """
        cls.run_cmd(["powershell.exe", "-NoProfile", "-Command", ps_cmd])

if __name__ == "__main__":
    PowerPolicy.set_master_volume_100()
    PowerPolicy.apply_power_safety()
    PowerPolicy.hide_shutdown_button()
    PowerPolicy.setup_nic_wol()
    print("전원 및 볼륨 정책 적용 완료!")
