# Zeus HDD Protector - Workspace Rules & Constraints

## 1. Single Project Root & Drive Rules (Crucial)
- **Primary Single Working Directory**: The ONLY valid project location is `C:\HDDGOD`. All edits, builds, runs, and git commands MUST execute in `C:\HDDGOD`.
- **Git Sync with GitHub**: All version control is strictly synchronized directly between local working PC (`C:\HDDGOD`) and GitHub remote `origin` (`https://github.com/eunpa23-ctrl/HDDGOD.git`).
- **Google Drive Policy**: Do NOT use Google Drive for automated/primary git syncing. However, accessing Google Drive (`G:\내 드라이브`, `G:\` 등) is fully permitted whenever necessary or requested by the user to retrieve reference materials, backups, or assets.
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

## 8. Windows GUI Process Execution & Unattended Control Rules (Golden Prompt Rules - Mandatory)
- **백그라운드 가상 세션 기동 절대 금지**:
  - GUI 프로그램(피카, 넷플릭스 등)을 실행할 때 기본 `subprocess.Popen`을 단독으로 사용하지 않는다. (Python `subprocess.STARTUPINFO`는 `lpDesktop` 속성을 지원하지 않아 `WinSta0\Default`에 전달되지 못하고 백그라운드 세션에 갇힘)
  - 반드시 `win32process.CreateProcess`를 사용하고 `si.lpDesktop = r"WinSta0\Default"`를 명시하여 실제 사용자 모니터 데스크톱 화면에 정상 표출되도록 기동한다.
- **마우스 좌표 클릭(pyautogui) 원천 배제**:
  - 해상도, DPI 배율, 윈도우 포커스, 한/영 키 상태에 취약한 마우스 좌표 클릭(`pyautogui`)에 의존하지 않는다.
  - 자식 Edit/Button 컨트롤을 탐색하여 Win32 메시지(`WM_SETTEXT`, `BM_CLICK`, `VK_RETURN`)를 메모리에 직접 주입하여 100% 무인 신뢰성을 보장한다.
- **방해 팝업 및 보조 창 사전/사후 자동 정리**:
  - 기동 전/후에 앞을 가리는 "이미 실행중(`LiveUp`)" 팝업이나, 기동 후 비동기로 열려 메인 화면을 가리는 "상품주문목록" 등의 보조 창을 감지하여 즉시 `WM_CLOSE`로 닫고, 메인 작업 창을 `SetForegroundWindow`로 최상위 전면에 올린다.
- **실제 화면 캡처 교차 검증(mss) 의무화**:
  - 프로세스 PID나 HWND의 단순 존재 여부만으로 성공을 단정 짓지 말고, 반드시 `ensure_desktop()` 후 `mss`로 실제 모니터 화면을 캡처하여 시각적으로 온전히 표출되었는지 직접 교차 검증한다.

## 9. 에이전트 행동 경계 표준 (Always / Ask First / Never - 사장님 절대 헌법)

### 🟢 Always (항상 준수할 것)
1. **성공 기준을 먼저 정하고 실행하라**: 작업 착수 전 객관적 실측 체크리스트를 정의하고, 완료 전 데이터 및 실제 화면 캡처로 직접 검증한다.
2. **시킨 것만 견고하게 코딩하라**: 200줄짜리 견고한 코드가 50줄로 날림 축소되지 않도록 예외 처리, 동기화 락, 로깅을 철저히 보존한다.
3. **안 되면 즉시 멈추고 조언을 구하라**: 오류 반복 시 혼자 무리하게 삽질하지 말고, 조기에 작업을 멈춘 뒤 현황을 보고하고 사장님께 조언과 정보를 요청한다.
4. **에이전트 추가를 적극 제시하라**: 복잡한 대규모 분석, 심층 리서치 또는 병렬 검증이 필요할 때 서브에이전트 추가 협업을 제안하여 업무 효율을 극대화한다.
5. **실제 화면 캡처 교차 검증 의무화**: GUI 작업 시 프로세스 존재 여부만 믿지 말고 실제 모니터 화면 캡처(`mss`)로 온전히 표출되었는지 확인한다.

### 🟡 Ask First (반드시 먼저 물어볼 것)
1. **짐작하지 말고 애매한 부분은 질문하라**: 요구사항이 모호하거나 여러 방법이 있을 때 자의적으로 판단하지 말고 즉시 사장님께 질문하여 의도를 명확히 확인한다.
2. **구조적 변경 및 주요 파일 삭제**: 대규모 아키텍처 변경, 새로운 외부 라이브러리 추가, 기존 파일 삭제가 필요할 때는 사장님의 사전 승인을 얻는다.

### 🔴 Never (절대 하지 말 것)
1. **짐작 코딩 절대 금지**: "이러면 되겠지"라는 추측 기반 코딩을 일체 하지 않는다.
2. **시키지 않은 코드 건들기 절대 금지**: 요청받지 않은 정상 모듈, 파일, 설정값을 임의로 수정하거나 리팩토링하지 않는다.
3. **손님 이용 중 좌석 간섭 절대 금지**: 피카 카운터상 손님 이용 중(`USING`) 좌석에는 원격 재부팅, 에이전트 강제 업데이트, 화면 제어를 일체 하지 않는다.
4. **기본 Git 동기화에 구글 드라이브 사용 금지**: 기본 깃 버전 관리는 오직 작업 PC(`C:\HDDGOD`)와 GitHub 간에 직접 수행한다. (단, 자료/백업 참조를 위한 구글 드라이브 접속은 허용)
5. **백그라운드 가상 세션 기동 및 마우스 좌표 의존 금지**: GUI 프로세스는 실제 데스크톱(`WinSta0\Default`)에 띄우고, 마우스 좌표 클릭 대신 Win32 컨트롤 메시지 주입을 우선한다.



