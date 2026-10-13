# 🚀 [HDDGOD / 제우스] 새 PC 환경 구축 및 Antigravity 테스트 가이드

이 문서는 **새로운 PC 또는 다른 PC에 Google Antigravity를 설치하고, HDDGOD(제우스 HDD PROTECTOR) 프로젝트를 연동하여 개발, 빌드, 테스트를 수행하는 전체 절차**를 정리한 가이드입니다.

---

## 📌 목차
1. [사전 준비 (필수 소프트웨어 설치)](#1-사전-준비-필수-소프트웨어-설치)
2. [Google Antigravity 설치 및 초기 설정](#2-google-antigravity-설치-및-초기-설정)
3. [HDDGOD 프로젝트 가져오기 및 파이썬 환경 설정](#3-hddgod-프로젝트-가져오기-및-파이썬-환경-설정)
4. [설정 파일(config.ini) 및 네트워크 점검](#4-설정-파일configini-및-네트워크-점검)
5. [테스트 시나리오별 실행 방법](#5-테스트-시나리오별-실행-방법)
   - [시나리오 A: 새 PC에서 [서버 + 클라이언트] 1인 로컬 테스트](#시나리오-a-새-pc에서-서버--클라이언트-1인-로컬-테스트)
   - [시나리오 B: 새 PC를 [클라이언트(손님석)]로 실제 매장 서버에 연결 테스트](#시나리오-b-새-pc를-클라이언트손님석로-실제-매장-서버에-연결-테스트)
   - [시나리오 C: Antigravity AI 에이전트로 빌드(PyInstaller) 테스트](#시나리오-c-antigravity-ai-에이전트로-빌드pyinstaller-테스트)
6. [자주 발생하는 문제 및 문제 해결 (FAQ)](#6-자주-발생하는-문제-및-문제-해결-faq)

---

## 1. 사전 준비 (필수 소프트웨어 설치)

새 PC에 아래 2가지 기본 프로그램을 먼저 설치합니다.

### ① Python (파이썬) 설치
* **권장 버전**: Python 3.10 ~ 3.14 (64-bit)
* **다운로드**: [python.org/downloads](https://www.python.org/downloads/)
* ⚠️ **주의사항 (매우 중요)**:
  * 설치 마법사 첫 화면 맨 아래의 **`Add python.exe to PATH`** 체크박스를 **반드시 체크**하고 설치해야 합니다!

### ② Google Drive 데스크톱 (또는 Git)
* 현재 프로젝트 코드가 구글 드라이브(`g:\내 드라이브\PROJECT\HDDGOD`)에 있으므로, **Google Drive 데스크톱 앱**을 설치하고 동일한 구글 계정으로 로그인하여 드라이브를 동기화합니다.
* *(Git 저장소를 이용하는 경우: `git clone <저장소URL>`로 프로젝트 폴더를 내려받습니다.)*

---

## 2. Google Antigravity 설치 및 초기 설정

### ① Antigravity 설치 및 실행
1. Google Antigravity 설치 파일을 다운로드하여 설치합니다.
2. 실행 후 구글 계정으로 로그인합니다.

### ② 워크스페이스(프로젝트 폴더) 열기
1. Antigravity 상단 메뉴 또는 좌측 메뉴에서 **[Open Folder]** (폴더 열기)를 클릭합니다.
2. HDDGOD 프로젝트 루트 폴더를 선택합니다:
   * 예: `G:\내 드라이브\PROJECT\HDDGOD` 또는 `C:\Users\<사용자명>\Documents\HDDGOD`
3. 폴더를 열면 프로젝트 내 `.agents/` 폴더가 자동 인식되며, 프로젝트 전용 스킬(`build-zeus` 등)이 자동으로 로드됩니다.

### ③ Antigravity 에이전트 권한 설정
Antigravity 좌측 하단 **[Settings (설정)]** 아이콘 클릭:
* **Tool Execution Policy**: `always-proceed` 또는 `request-review` (터미널 명령 자동 실행 허용 권한)
* **Terminal Sandbox**: 필요에 따라 설정 (로컬 환경 테스트 시 `proceed-in-sandbox` 또는 기본값)

---

## 3. HDDGOD 프로젝트 가져오기 및 파이썬 환경 설정

새 PC의 파이썬에 필요한 라이브러리를 설치합니다. 프로젝트 내에 원클릭 자동 설치 스크립트가 준비되어 있습니다.

### 방법 1: 원클릭 자동 설치 (가장 추천)
1. 프로젝트 폴더 루트에서 **`0_라이브러리_자동설치.bat`** 파일을 더블클릭합니다.
2. 스크립트가 실행되면서 아래 필수 패키지를 자동으로 검사하고 설치합니다:
   * `fastapi`, `uvicorn`, `websockets`, `aiohttp`, `requests`, `jinja2`
   * `pillow`, `mss`, `pyautogui`, `pystray`, `wakeonlan`, `pycaw`, `comtypes`, `psutil`
3. `[OK] 필수 파이썬 라이브러리 점검 완료` 메시지가 나오면 창을 닫습니다.

### 방법 2: 수동 터미널 명령 설치
Antigravity 내부 터미널(또는 CMD/PowerShell)에서 아래 명령어를 실행합니다:
```powershell
pip install -r requirements.txt pyinstaller
```

---

## 4. 설정 파일(config.ini) 및 네트워크 점검

### ① 설정 파일 위치
* 마스터 설정 파일: `deploy/ClientDeploy/core/config.ini`
* 기본 설정 내용:
  ```ini
  [SERVER]
  server_host = 0.0.0.0
  server_port = 8000

  [CLIENT]
  server_ip = 192.168.0.100    # 카운터 서버 PC의 IP
  server_port = 8000
  heartbeat_interval = 3
  admin_password = 1234
  ```

### ② 윈도우 방화벽 포트 허용 (새 PC가 서버 역할을 할 경우)
* 새 PC에서 `ZeusServer`를 실행해 다른 PC들의 접속을 받으려면, Windows 방화벽에서 **`8000`번 포트(TCP)**를 열어주어야 합니다.
```powershell
netsh advfirewall firewall add rule name="ZeusServer_8000" dir=in action=allow protocol=TCP localport=8000
```

---

## 5. 테스트 시나리오별 실행 방법

새 PC를 어떤 용도로 테스트할 것인지에 따라 아래 시나리오를 선택하세요.

---

### 시나리오 A: 새 PC에서 [서버 + 클라이언트] 1인 로컬 테스트
> **목적**: 다른 손님석 PC 없이, 새 PC 한 대 안에서 관제 서버와 클라이언트 에이전트가 정상 통신하는지 검증합니다.

1. **서버(ZeusServer) 실행**:
   * Antigravity 터미널에서 실행:
     ```powershell
     python -m server.server_core
     ```
   * 터미널에 `Uvicorn running on http://0.0.0.0:8000`이 뜨면 서버가 켜진 것입니다.

2. **관제 대시보드 열기**:
   * 크롬 브라우저를 열고 `http://localhost:8000`에 접속합니다.
   * 모바일 관제 화면은 `http://localhost:8000/mobile`로 접속합니다.

3. **클라이언트(ZeusAgent) 실행**:
   * 새 터미널 창을 하나 더 열고 실행:
     ```powershell
     python -m client.client_agent
     ```
   * 에이전트는 로컬 8000번 포트가 열려 있으면 자동으로 `127.0.0.1`로 서버를 감지하여 연결합니다.
   * 작업표시줄 오른쪽 트레이에 제우스 아이콘이 생성됩니다.

4. **검증**:
   * 대시보드 화면에 새 PC의 호스트명이 **초록색 ONLINE** 카드로 나타나는지 확인합니다.
   * 화면 캡처, 볼륨 제어, 넷플릭스 루틴 등 기능이 대시보드에서 정상 동작하는지 테스트합니다.

---

### 시나리오 B: 새 PC를 [클라이언트(손님석)]로 실제 매장 서버에 연결 테스트
> **목적**: 새 PC를 실제 PC방 손님석처럼 세팅하여, 카운터 메인 서버(`192.168.0.100`)와 통신하는지 검증합니다.

1. **카운터 서버 IP 확인**:
   * 실제 카운터 PC의 IP가 `192.168.0.100`인지 확인합니다.
   * 만약 다르다면 `deploy/ClientDeploy/core/config.ini` 파일의 `server_ip` 값을 실제 카운터 IP로 변경합니다.

2. **원클릭 자동 설치 실행**:
   * `deploy/ClientDeploy/1_설치하기.bat` (또는 `install.bat`) 파일을 **우클릭 ➡️ [관리자 권한으로 실행]** 합니다.
   * 스크립트가 `C:\ZeusAgent` 폴더를 생성하고, 보안 예외/방화벽/시작프로그램을 등록한 후 `ZeusAgent.exe`를 구동합니다.

3. **순간복구(UWF) 테스트 참고사항**:
   * **일반 PC (Windows 10/11 Home/Pro)**:
     * UWF 드라이버가 없으므로 `UWFController`가 자동으로 **"가상 테스트 모드(Simulated Mode)"**로 동작합니다.
     * 대시보드에서 [유지보수 모드], [세팅저장&보호]를 누르면 오류 없이 가상 상태가 전환되므로 안심하고 테스트할 수 있습니다.
   * **실제 PC방 PC (Windows Enterprise/IoT)**:
     * 실제 `uwfmgr.exe` 순간복구 엔진과 연동되어 3초 안전 유예 후 실제 재부팅 및 롤백 방지 기능이 가동됩니다.

---

### 시나리오 C: Antigravity AI 에이전트로 빌드(PyInstaller) 테스트
> **목적**: 코드 수정 후 최신 실행 파일(`ZeusServer.exe`, `ZeusAgent.exe`)을 정상 생성할 수 있는지 검증합니다.

Antigravity 채팅창에서 자연어로 요청하거나 직접 터미널 명령으로 빌드할 수 있습니다:

1. **클라이언트 단일 실행 파일 빌드**:
   * **명령어**:
     ```powershell
     pyinstaller ZeusAgent.spec --clean -y
     ```
   * **결과물**: `dist/ZeusAgent.exe` (약 24.9MB, 단일 실행 파일)
   * 빌드된 실행 파일은 `deploy/ClientDeploy/core/ZeusAgent.exe`에 복사하여 배포합니다.

2. **서버 실행 파일 빌드**:
   * **명령어**:
     ```powershell
     pyinstaller ZeusServer.spec --clean -y
     ```
   * **결과물**: `dist/ZeusServer.exe`

3. **Antigravity 에이전트 대화창에 직접 요청하기**:
   * 채팅창에 `클라이언트 최신 버전으로 빌드해줘` 또는 `build-zeus 스킬로 서버 빌드해줘`라고 입력하면 Antigravity 에이전트가 알아서 빌드 및 배포 경로 복사까지 원스톱으로 처리합니다.

---

## 6. 자주 발생하는 문제 및 문제 해결 (FAQ)

### Q1. 터미널에서 `python : 'python' 용어가 cmdlet, 함수...` 오류가 납니다.
* **원인**: 파이썬 설치 시 PATH(환경변수) 등록이 누락되었습니다.
* **해결**: 파이썬 설치 프로그램을 다시 실행하여 **Modify(수정)** 선택 ➡️ **`Add Python to environment variables`**를 체크하고 완료하거나, 시스템 환경변수에 파이썬 경로를 직접 추가하세요.

### Q2. 한글 파일명이나 로그가 깨지거나 크래시가 납니다.
* **원인**: Windows 기본 콘솔 인코딩(CP949)과 프로젝트 UTF-8 인코딩 간의 충돌입니다.
* **해결**: PowerShell/CMD에서 `chcp 65001` 명령을 실행하거나, 배치 파일 첫 줄에 `chcp 65001 >nul` 또는 `chcp 949 >nul`이 올바르게 명시되어 있는지 확인하세요.

### Q3. 클라이언트가 서버에 연결되지 않고 `서버 연결 대기 중 (5초 후 재시도)`만 반복됩니다.
* **원인**:
  1. 카운터 서버가 실행 중이 아닙니다 (`python -m server.server_core` 실행 필요).
  2. `config.ini`의 `server_ip`가 잘못 입력되었습니다.
  3. 카운터 PC의 8000번 방화벽 포트가 닫혀 있습니다.
* **해결**: 카운터 PC에서 `ping 192.168.0.100` 및 방화벽 8000 포트 허용 여부를 점검하세요.

### Q4. PyInstaller 빌드 시 `No module named ...` 오류가 납니다.
* **해결**: 새 PC에 일부 라이브러리가 덜 설치된 상태입니다. `0_라이브러리_자동설치.bat`를 다시 실행해 누락된 모듈을 전부 설치한 후 빌드하세요.
