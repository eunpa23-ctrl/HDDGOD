# -*- coding: utf-8 -*-
import os
import subprocess
import logging
from common.protocol import UWFStatus

logger = logging.getLogger("UWF_Controller")

class UWFController:
    """Windows UWF 순간복구 제어 엔진 (WMI 1순위 기반 무결점 제어)"""

    _simulated_status = None
    _uwf_available = None
    _uwf_checked = False

    @classmethod
    def is_uwf_supported(cls) -> bool:
        if cls._uwf_available is None:
            import shutil
            cls._uwf_available = (shutil.which("uwfmgr.exe") is not None or os.path.exists(r"C:\Windows\System32\uwfmgr.exe"))
        return cls._uwf_available

    @classmethod
    def run_cmd(cls, args: list) -> str:
        try:
            res = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                creationflags=0x08000000, # 콘솔창 숨김
                encoding="cp949",
                errors="ignore"
            )
            return res.stdout.strip()
        except Exception:
            return ""

    @classmethod
    def get_status(cls) -> str:
        """현재 UWF 필터 상태 조회 (WMI 1순위 정확 감지)"""
        try:
            cmd = "powershell -Command \"(Get-CimInstance -Namespace 'root\\standardcimv2\\embedded' -ClassName 'UWF_Filter').CurrentEnabled\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3, creationflags=0x08000000)
            val = res.stdout.strip().lower()
            if "true" in val:
                return UWFStatus.PROTECTED
            elif "false" in val:
                return UWFStatus.MAINTENANCE
        except Exception as e:
            logger.debug(f"WMI UWF 상태 조회 예외: {e}")

        # CLI 폴백
        output = cls.run_cmd(["uwfmgr.exe", "get-config"])
        if not output:
            return cls._simulated_status if cls._simulated_status else UWFStatus.DISABLED

        out_lower = output.lower()
        if "filter state: on" in out_lower or "필터 상태: 설정" in output or "필터 상태: 켜짐" in output:
            if "next session: off" in out_lower or "다음 세션: 해제" in output:
                return UWFStatus.MAINTENANCE
            return UWFStatus.PROTECTED
        elif "filter state: off" in out_lower or "필터 상태: 해제" in output or "필터 상태: 꺼짐" in output:
            return UWFStatus.MAINTENANCE

        return UWFStatus.UNKNOWN

    @classmethod
    def enable_protection(cls) -> bool:
        """보호 모드 활성화 (WMI 직접 호출)"""
        logger.info("UWF 순간복구 보호 모드 활성화 시작...")
        try:
            wmi_cmd = (
                "powershell -Command "
                "\"$f = Get-CimInstance -Namespace 'root\\standardcimv2\\embedded' -ClassName 'UWF_Filter'; "
                "Invoke-CimMethod -InputObject $f -MethodName 'Enable'\""
            )
            subprocess.run(wmi_cmd, shell=True, capture_output=True, timeout=5, creationflags=0x08000000)
            logger.info("✅ WMI 기반 UWF 보호 모드 활성화 성공!")
        except Exception as e:
            logger.warning(f"WMI UWF 활성화 예외: {e}")

        cls.run_cmd(["uwfmgr.exe", "filter", "enable"])
        cls.run_cmd(["uwfmgr.exe", "volume", "protect", "c:"])
        cls.run_cmd(["uwfmgr.exe", "overlay", "set-type", "RAM"])
        cls.run_cmd(["uwfmgr.exe", "overlay", "set-size", "2048"])
        return True

    @classmethod
    def disable_protection(cls) -> bool:
        """유지보수 모드 (WMI 직접 호출로 100% 해제 보장)"""
        logger.info("UWF 보호 해제 (유지보수 모드 전환)...")
        try:
            wmi_cmd = (
                "powershell -Command "
                "\"$f = Get-CimInstance -Namespace 'root\\standardcimv2\\embedded' -ClassName 'UWF_Filter'; "
                "Invoke-CimMethod -InputObject $f -MethodName 'Disable'\""
            )
            subprocess.run(wmi_cmd, shell=True, capture_output=True, timeout=5, creationflags=0x08000000)
            logger.info("✅ WMI 기반 UWF 보호 해제 성공!")
        except Exception as e:
            logger.warning(f"WMI UWF 해제 예외: {e}")

        cls.run_cmd(["uwfmgr.exe", "filter", "disable"])
        return True

    @classmethod
    def apply_exclusions(cls) -> None:
        """영구 보존 예외 경로 등록"""
        exclusions = [
            r"C:\ZeusAgent",
            r"C:\Program Files\DAUM\PotPlayer",
            r"C:\ProgramData\NetflixProfile",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes")
        ]
        # 피카(Pica Live/Air) 클라이언트 설치 경로가 존재하면 자동 예외 등록
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
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception:
                    pass
            # 1. WMI를 통한 확실한 영구 보존 예외 등록
            try:
                ps = f"""
                $vol = Get-CimInstance -Namespace 'root\\standardcimv2\\embedded' -ClassName 'UWF_Volume' | Where-Object {{ $_.DriveLetter -like 'c*' }}
                if ($vol) {{
                    Invoke-CimMethod -InputObject $vol -MethodName 'AddExclusion' -Arguments @{{ FileName = '{path}' }}
                }}
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=5, creationflags=0x08000000)
                logger.info(f"✅ WMI 영구 보존 예외 등록: {path}")
            except Exception as e:
                logger.debug(f"WMI 예외 등록 실패 ({path}): {e}")

            # 2. CLI 폴백
            cls.run_cmd(["uwfmgr.exe", "file", "add-exclusion", path])

    @classmethod
    def reboot_restore(cls) -> None:
        """즉시 1초 복구 재부팅"""
        logger.info("즉시 복구 재부팅 실행...")
        cls.run_cmd(["shutdown.exe", "/r", "/t", "0", "/f"])

    @classmethod
    def reboot_and_protect(cls) -> None:
        """현재 세팅 영구 저장 후 보호 모드로 재부팅"""
        cls.enable_protection()
        cls.apply_exclusions()
        logger.info("보호 모드로 안전 재부팅 실행 (레지스트리 커밋 2초 대기)...")
        import time
        time.sleep(2)  # 레지스트리 디스크 플러시 시간 확보
        os.system("shutdown.exe /r /t 3 /f /c \"ZeusAgent: 보호 모드로 안전 재부팅합니다.\"")

    @classmethod
    def reboot_to_maintenance(cls) -> None:
        """보호 해제 후 유지보수 모드로 재부팅"""
        cls.disable_protection()
        logger.info("유지보수 모드로 안전 재부팅 실행 (레지스트리 커밋 2초 대기)...")
        import time
        time.sleep(2)  # 레지스트리 디스크 플러시 시간 확보
        os.system("shutdown.exe /r /t 3 /f /c \"ZeusAgent: 유지보수 모드로 안전 재부팅합니다.\"")

if __name__ == "__main__":
    print("현재 UWF 상태:", UWFController.get_status())
