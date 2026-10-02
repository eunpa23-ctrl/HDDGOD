# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - 윈도우 방해화면 박멸 & 매 부팅 자동 최적화 모듈
G:\내 드라이브\PROJECT\HDDGOD\client\windows_optimizer.py
"""
import winreg
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WindowsOptimizer")

class WindowsOptimizer:
    """MS 방해화면 차단, SCOOBE 파란화면 박멸, 윈도우 업데이트 강제 재부팅 차단"""

    @staticmethod
    def set_reg_value(root, path, name, val_type, value) -> bool:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
            winreg.SetValueEx(key, name, 0, val_type, value)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.debug(f"레지스트리 설정 실패 ({path}\\{name}): {e}")
            return False

    @classmethod
    def block_scoobe_and_ms_account(cls) -> None:
        """SCOOBE '장치 설정 완료' 파란 화면 및 MS 계정 전환 팝업 완전 차단"""
        logger.info("SCOOBE 방해화면 및 MS 계정 전환 차단 레지스트리 적용 중...")

        # 1. SCOOBE 장치 설정 완료 화면 차단
        cls.set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\UserProfileEngagement",
            "ScoobeSystemSettingEnabled",
            winreg.REG_DWORD,
            0
        )
        cls.set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\UserProfileEngagement",
            "ScoobeSystemSettingEnabled",
            winreg.REG_DWORD,
            0
        )

        # 2. MS 계정 연결 유도 차단 (로컬 계정 유지)
        cls.set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
            "NoConnectedUser",
            winreg.REG_DWORD,
            1
        )
        cls.set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\PolicyManager\default\Settings\AllowYourAccount",
            "value",
            winreg.REG_DWORD,
            0
        )

        # 3. 윈도우 환영 환경 및 팁 차단 (ContentDeliveryManager)
        cdm_path = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        cls.set_reg_value(winreg.HKEY_CURRENT_USER, cdm_path, "SubscribedContent-310093Enabled", winreg.REG_DWORD, 0)
        cls.set_reg_value(winreg.HKEY_CURRENT_USER, cdm_path, "SubscribedContent-338389Enabled", winreg.REG_DWORD, 0)
        cls.set_reg_value(winreg.HKEY_CURRENT_USER, cdm_path, "SubscribedContent-353694Enabled", winreg.REG_DWORD, 0)
        cls.set_reg_value(winreg.HKEY_CURRENT_USER, cdm_path, "SubscribedContent-353696Enabled", winreg.REG_DWORD, 0)

    @classmethod
    def block_browser_first_run(cls) -> None:
        """크롬 및 엣지 브라우저 첫 실행 마법사/동기화 팝업 차단"""
        logger.info("브라우저 첫 실행 마법사 차단 정책 적용 중...")

        # Edge 첫 실행 마법사 차단
        cls.set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Edge",
            "HideFirstRunExperience",
            winreg.REG_DWORD,
            1
        )

        # Chrome 첫 실행 홍보 탭 차단
        cls.set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Google\Chrome",
            "PromotionalTabsEnabled",
            winreg.REG_DWORD,
            0
        )

    @classmethod
    def block_windows_update_reboot(cls) -> None:
        """손님 이용 중 윈도우 자동 업데이트로 인한 새벽 강제 재부팅 방지"""
        logger.info("윈도우 자동 업데이트 강제 재부팅 방지 정책 적용 중...")
        wu_path = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
        cls.set_reg_value(winreg.HKEY_LOCAL_MACHINE, wu_path, "NoAutoRebootWithLoggedOnUsers", winreg.REG_DWORD, 1)
        cls.set_reg_value(winreg.HKEY_LOCAL_MACHINE, wu_path, "AUOptions", winreg.REG_DWORD, 2)  # 다운로드 전 확인

    @classmethod
    def disable_annoying_tasks(cls) -> None:
        """스케줄러에 등록된 MS 방해 작업 비활성화"""
        tasks = [
            r"\Microsoft\Windows\Setup\EOSNotify",
            r"\Microsoft\Windows\Setup\SetupCleanupTask"
        ]
        for task in tasks:
            subprocess.run(
                ["schtasks.exe", "/change", "/tn", task, "/disable"],
                capture_output=True,
                check=False
            )

    @classmethod
    def optimize_all_on_boot(cls) -> None:
        """매 부팅 시 0.1초 만에 실행되는 통합 방해화면 박멸 실행기"""
        cls.block_scoobe_and_ms_account()
        cls.block_browser_first_run()
        cls.block_windows_update_reboot()
        cls.disable_annoying_tasks()
        logger.info("MS 방해화면 및 업데이트 재부팅 방지 적용 완료")

if __name__ == "__main__":
    WindowsOptimizer.optimize_all_on_boot()
    print("윈도우 방해화면 박멸 완료!")
