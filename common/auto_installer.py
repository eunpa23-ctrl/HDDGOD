# -*- coding: utf-8 -*-
"""
[제우스 HDD PROTECTOR] 파이썬 필수 패키지 오프라인/온라인 자동 설치기
- PC에 필요한 라이브러리가 없을 때 packages/ 폴더에 모아둔 오프라인 패키지(.whl)를 감지하여 1초 만에 자동 설치
- 오프라인 패키지가 부족하거나 없을 경우 온라인 pip install로 자동 백업 설치
"""

import os
import sys
import subprocess
import importlib.util

# 윈도우 콘솔 인코딩 안전화 (cp949 유니코드 깨짐 및 크래시 방지)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 검사할 핵심 필수 패키지 모듈 목록 및 대응 패키지명
REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn[standard]",
    "websockets": "websockets",
    "requests": "requests",
    "jinja2": "jinja2",
    "PIL": "pillow",
    "mss": "mss",
    "pyautogui": "pyautogui",
    "pystray": "pystray",
    "wakeonlan": "wakeonlan",
    "pycaw": "pycaw",
    "comtypes": "comtypes",
    "aiohttp": "aiohttp",
}

def get_missing_modules():
    """설치되지 않은 모듈 목록 반환"""
    missing = []
    for mod_name, pkg_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(mod_name) is None:
            missing.append(pkg_name)
    return missing

def ensure_dependencies(project_root=None, silent=False):
    """
    필수 라이브러리 검사 및 누락 시 자동 설치
    1순위: packages/ 폴더 내 오프라인 wheel 설치 (--no-index --find-links=packages)
    2순위: 온라인 pip 설치
    """
    # PyInstaller 빌드 실행 파일인 경우 이미 모든 라이브러리가 포함되어 있으므로 통과
    if getattr(sys, "frozen", False):
        return True

    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    req_file = os.path.join(project_root, "requirements.txt")
    packages_dir = os.path.join(project_root, "packages")

    missing = get_missing_modules()
    if not missing:
        if not silent:
            print("[OK] 필수 파이썬 라이브러리 점검 완료 (모든 모듈 정상)")
        return True

    print("=" * 60)
    print("  [제우스 라이브러리 자동 설치기] 누락된 패키지 감지!")
    print(f"  설치 필요 항목: {', '.join(missing)}")
    print("=" * 60)

    # 1. 오프라인 설치 시도 (packages 폴더가 존재하는 경우)
    if os.path.isdir(packages_dir) and any(f.endswith((".whl", ".tar.gz", ".zip")) for f in os.listdir(packages_dir)):
        print(f"[*] 오프라인 저장소({packages_dir})에서 초고속 무인 설치를 진행합니다...")
        try:
            cmd = [
                sys.executable, "-m", "pip", "install",
                "--no-index",
                f"--find-links={packages_dir}",
                "-r", req_file
            ]
            res = subprocess.run(cmd, check=False)
            if res.returncode == 0:
                print("[OK] 오프라인 패키지 자동 설치가 성공적으로 완료되었습니다!")
                return True
            else:
                print("[!] 오프라인 설치 일부 실패. 온라인 설치로 전환합니다.")
        except Exception as e:
            print(f"[!] 오프라인 설치 예외: {e}")

    # 2. 온라인 설치 시도 (인터넷 연결 환경)
    print("[*] 온라인 저장소(PyPI)에서 패키지를 자동 설치합니다...")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            print("[OK] 온라인 패키지 자동 설치가 완료되었습니다!")
            return True
        else:
            print("[오류] 패키지 설치 실패. 관리자 권한으로 실행하거나 네트워크를 확인하세요.")
            return False
    except Exception as e:
        print(f"[오류] 자동 설치 중 예외 발생: {e}")
        return False

if __name__ == "__main__":
    ensure_dependencies()
