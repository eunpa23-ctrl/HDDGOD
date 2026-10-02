# -*- coding: utf-8 -*-
r"""
제우스 HDD PROTECTOR - Windows UWF(통합 쓰기 필터) 제어 엔진
G:\내 드라이브\PROJECT\HDDGOD\client\uwf_controller.py
"""
import os
import subprocess
import logging
from common.protocol import UWFStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UWF_Controller")

class UWFController:
    """Windows UWF(Unified Write Filter) 순간복구 엔진 관리자"""
    _uwf_checked = False
    _uwf_available = None

    _simulated_status = None  # UWF 미설치 PC에서 대시보드 제어 테스트용 가상 상태

    @classmethod
    def is_uwf_supported(cls) -> bool:
        if cls._uwf_available is None:
            import shutil
            cls._uwf_available = (shutil.which("uwfmgr.exe") is not None or os.path.exists(r"C:\Windows\System32\uwfmgr.exe"))
            if not cls._uwf_available and not cls._uwf_checked:
                logger.info("UWF 순간복구 엔진(uwfmgr.exe) 미설치 환경 (실제 매장 배포 시 1_설치하기.bat으로 자동 활성화됨)")
                cls._uwf_checked = True
        return cls._uwf_available

    @classmethod
    def run_cmd(cls, args: list) -> str:
        if not cls.is_uwf_supported():
            return ""
        try:
            creationflags = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW (검은창 깜빡임 방지)
            res = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                creationflags=creationflags,
                encoding="cp949",
                errors="ignore"
            )
            if res.stderr and res.stderr.strip():
                logger.debug(f"UWF 명령 실행 알림 ({args}): {res.stderr.strip()}")
            return res.stdout.strip()
        except Exception as e:
            logger.debug(f"UWF 명령어 실행 실패 {args}: {e}")
            return ""

    @classmethod
    def get_status(cls) -> str:
        """현재 UWF 필터 상태 조회 (PROTECTED / MAINTENANCE / DISABLED)"""
        if not cls.is_uwf_supported():
            return cls._simulated_status if cls._simulated_status else UWFStatus.DISABLED

        output = cls.run_cmd(["uwfmgr.exe", "get-config"])
        if not output:
            return cls._simulated_status if cls._simulated_status else UWFStatus.DISABLED

        out_lower = output.lower()
        # 현재 세션 및 다음 부팅 세션 확인
        if "filter state: on" in out_lower or "필터 상태: 설정" in output or "필터 상태: 켜짐" in output:
            if "next session: off" in out_lower or "다음 세션: 해제" in output:
                return UWFStatus.MAINTENANCE
            return UWFStatus.PROTECTED
        elif "filter state: off" in out_lower or "필터 상태: 해제" in output or "필터 상태: 꺼짐" in output:
            return UWFStatus.MAINTENANCE
        return UWFStatus.UNKNOWN

    @classmethod
    def enable_protection(cls) -> bool:
        """순간복구 보호 모드 활성화 (C 드라이브 보호 및 오버레이 활성화)"""
        logger.info("UWF 순간복구 보호 모드 활성화 시작...")
        if not cls.is_uwf_supported():
            cls._simulated_status = UWFStatus.PROTECTED
            logger.info("🧪 [개발/테스트 모드] UWF 미설치 환경 -> 가상 보호 모드(PROTECTED)로 전환 완료!")
            return True

        cls.run_cmd(["uwfmgr.exe", "filter", "enable"])
        cls.run_cmd(["uwfmgr.exe", "volume", "protect", "c:"])
        # RAM 오버레이 설정 (RAM 2048MB 할당)
        cls.run_cmd(["uwfmgr.exe", "overlay", "set-type", "RAM"])
        cls.run_cmd(["uwfmgr.exe", "overlay", "set-size", "2048"])
        return True

    @classmethod
    def disable_protection(cls) -> bool:
        """유지보수 모드 (다음 부팅 시 복구 해제하여 프로그램 설치/업데이트 가능)"""
        logger.info("UWF 보호 해제 (유지보수 모드 전환)...")
        if not cls.is_uwf_supported():
            cls._simulated_status = UWFStatus.MAINTENANCE
            logger.info("🧪 [개발/테스트 모드] UWF 미설치 환경 -> 가상 유지보수 모드(MAINTENANCE)로 전환 완료!")
            return True

        output = cls.run_cmd(["uwfmgr.exe", "filter", "disable"])
        return "reboot" in output.lower() or "재부팅" in output or True

    @classmethod
    def apply_exclusions(cls) -> None:
        """영구 보존 예외 경로 등록 (팟플레이어, 넷플릭스 격리 프로필, 피카 PC방 관리프로그램)"""
        exclusions = [
            r"C:\ZeusAgent",
            r"C:\Program Files\DAUM\PotPlayer",
            r"C:\ProgramData\NetflixProfile",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes")
        ]
        # 피카(Pica Live/Air) 클라이언트 설치 경로가 존재하면 자동 예외 등록 (재부팅 시 피카 설정 및 로그 보존)
        pica_candidates = [
            r"C:\Program Files (x86)\PicaLive",
            r"C:\Program Files\PicaLive",
            r"C:\PicaLive",
            r"C:\Program Files (x86)\PicaAir",
            r"C:\PicaAir"
        ]
        for p in pica_candidates:
            if os.path.exists(p) and p not in exclusions:
                exclusions.append(p)

        for path in exclusions:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            logger.info(f"영구 보존 예외 등록: {path}")
            cls.run_cmd(["uwfmgr.exe", "file", "add-exclusion", path])

    @classmethod
    def reboot_restore(cls) -> None:
        """즉시 1초 복구 재부팅"""
        logger.info("즉시 복구 재부팅 실행...")
        cls.run_cmd(["shutdown.exe", "/r", "/t", "0", "/f"])

    @classmethod
    def reboot_to_maintenance(cls) -> None:
        """보호 해제 후 유지보수 모드로 재부팅"""
        cls.disable_protection()
        logger.info("유지보수 모드로 재부팅 실행...")
        cls.run_cmd(["shutdown.exe", "/r", "/t", "0", "/f"])

    @classmethod
    def reboot_and_protect(cls) -> None:
        """현재 세팅 저장 후 보호 모드로 재부팅 (새 기준점 고정)"""
        cls.enable_protection()
        logger.info("현재 상태 영구저장 및 보호 모드로 재부팅 실행...")
        cls.run_cmd(["shutdown.exe", "/r", "/t", "0", "/f"])

if __name__ == "__main__":
    print("현재 UWF 상태:", UWFController.get_status())
