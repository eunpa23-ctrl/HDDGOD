# Zeus HDD Protector - Workspace Rules & Constraints

## 1. Single Project Root & Drive Rules (Crucial)
- **Primary Single Working Directory**: The ONLY valid project location is `C:\HDDGOD`. All edits, builds, runs, and git commands MUST execute in `C:\HDDGOD`.
- **NO GOOGLE DRIVE SYNC (절대 금지)**: Do NOT read from, write to, copy to, or sync with Google Drive (`G:\내 드라이브`, `G:\`, etc.). Google Drive sync is completely disabled and prohibited.
- **Git Sync with GitHub**: All version control is strictly synchronized directly between local `C:\HDDGOD` and GitHub remote `origin` (`https://github.com/eunpa23-ctrl/HDDGOD.git`).
- **Client Installation Path**: The client installation path on all target PCs is strictly fixed to `C:\ZeusAgent\`.

## 2. System Identifiers & Windows Policies
- **English-Only System Names**: Windows Firewall rules, Defender exclusions, Task Scheduler jobs, process names, and service names must be 100% English alphanumeric (e.g., `ZeusAgent`, `ZeusAgent_Port8000`).
- **Windows Defender Exclusions**: Automatically set `C:\ZeusAgent` as excluded directory via `Add-MpPreference -ExclusionPath "C:\ZeusAgent"`.

## 3. Encoding Standards
- **Python Source & File I/O**: All Python scripts must explicitly use UTF-8 (`open(path, "r", encoding="utf-8")`).
- **Windows Batch Files**: Batch scripts (`.bat`) targeting Windows CMD must be encoded in `CP949` with `CRLF` line endings.
- **Network / Socket Communication**: WebSockets and HTTP APIs must exchange UTF-8 encoded JSON payloads (`json.dumps(..., ensure_ascii=False).encode("utf-8")`).
- **Configuration & Rule Files**: All configuration (`.ini`, `.json`) and documentation (`.md`) files must be saved in UTF-8 without BOM.

## 4. Packaging & Deployment Architecture
- **Client Deployment Location**: All client installation scripts and binaries reside in `C:\HDDGOD\deploy\ClientDeploy\`.
- **Single Installer Script**: Use ONLY `1_설치하기.bat`. Do not create or run `install.bat`.
- **Standalone Binary**: `deploy/ClientDeploy/core/ZeusAgent.exe` with accompanying `config.ini`, `version.txt`, and `netflix.ico`.

## 5. User Communication
- Always communicate with the user politely, accurately, and concisely in Korean.

## 6. Per-PC Settings & Display DPI Adaptation (Crucial)
- **PC별 환경 다양성 전제**: 각 PC마다 해상도, 디스플레이 배율(DPI 100%, 125%, 150%), 그래픽 및 윈도우 환경 설정값이 다를 수 있음을 필히 감안하여 개발 및 디버깅을 진행한다.
- **고정 수치 지양 & 동적 자동 감지**: 버튼 크기, 창 크기, 마우스 좌표를 고정된 상수로 하드코딩하지 않고, `GetDpiForSystem()` / `GetSystemMetrics()` 등으로 각 PC의 배율 및 해상도를 자동 감지하여 동적으로 스케일링하거나 PC별로 다르게 분기 적용한다.
- **Win32 메시지 주입 우선**: 좌표 왜곡 방지를 위해 `WM_SETTEXT (0x000C)`(텍스트 직접 주입), `BM_CLICK (0x00F5)`(버튼 직접 클릭) 등 Win32 메시지 레벨 처리를 최우선한다.

## 7. PICA Counter Screen Reference & Alignment (Mandatory)
- **피카 카운터 관리프로그램 화면 기준 대조**: 좌석 상태(사용중, 잠김/대기, 오프라인) 판별 및 디버깅 시 반드시 카운터 PC의 피카 관리프로그램 실제 화면을 캡처/참조하여 제우스 대시보드와 100% 일치하도록 검증한다.
- **손님 이용 좌석 절대 불간섭**: 피카 화면상 손님이 이용 중인 좌석(예: PC-01 등)은 원격 재부팅, 에이전트 강제 업데이트, 화면 제어 등 어떠한 조작도 절대 수행하지 않는다.
