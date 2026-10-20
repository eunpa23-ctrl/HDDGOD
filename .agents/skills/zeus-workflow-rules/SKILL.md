---
name: zeus-workflow-rules
description: HDDGOD 제우스 프로젝트 표준 워크플로우 규칙 - 토큰 최적화, 버전 원자적 동기화, 넷플릭스 바로가기 보존, 업데이트 완전 분리 실행
---

# HDDGOD 제우스 워크플로우 표준 규칙 (Zeus Workflow Rules)

## 1. Git 푸시 및 토큰 최소화 원칙 (Minimal Token Usage)
- **정밀 수정 원칙**: 전체 파일을 다시 쓰거나 대량 복사하지 않고, 변경이 필요한 부분만 최소 단위로 수정(diff 최소화).
- **Git Staging 선택성**: `git add -A` 대신 변경된 소스 파일만 명시적으로 스테이징하여 불필요한 빌드 임시 파일 커밋 방지.
- **원격 동기화**: `\\192.168.0.100\HDDGOD`와 GitHub 원격 저장소(`https://github.com/eunpa23-ctrl/HDDGOD.git`)에 동일 커밋 동기화.

## 2. 버전 정보 원자적 동기화 (Atomic Version Alignment)
버전이 변경될 때(예: `3.8.x`), 아래 모든 위치가 반드시 **동시에 일괄 변경**되어야 한다:
1. `deploy/ClientDeploy/version.txt`
2. `deploy/ClientDeploy/core/version.txt`
3. 클라이언트 로컬 배포 테스트 시 `c:\ZeusAgent\version.txt`
4. 서버 대시보드 API 반환값 확인 (`/api/version`, `/api/settings`)

## 3. 넷플릭스 바탕화면 바로가기 업데이트 보존 정책
- **기존 아이콘 덮어쓰기 원칙**: 바탕화면에 이미 `넷플릭스.lnk`가 존재하면 새로 난립시키지 않고 해당 파일에 덮어쓰기(Overwrite).
- **읽기 전용 해제 후 재적용**: `attrib -r`로 해제 후 속성 갱신, 완료 후 `attrib +r`로 피카 등 타 프로그램 변조 차단.
- **업데이트 실행 시 중복 생성 금지**: 에이전트 업데이트 직후에는 바로가기가 이미 존재하면 생성/조작을 건너뛰고, 완전히 없을 때만 최초 생성.

## 4. 무인 자동 업데이트 완전 분리 프로세스 정책
- **프로세스 스폰 플래그**: `DETACHED_PROCESS(0x8)` 사용 금지 (cmd.exe 콘솔 서브시스템 부재로 즉사함).
- **표준 무창 분리 실행**: `CREATE_NO_WINDOW(0x08000000) | CREATE_NEW_PROCESS_GROUP(0x00000200)` 사용.
- **버퍼 플러시 보장**: `update.bat` 작성 시 `f.flush()` 및 `os.fsync(f.fileno())` 필수 호출.
- **종료 및 교체 확인**: `update.bat` 내부에서 `tasklist`로 기존 프로세스 완전 사망 확인 루프(`:KILL_LOOP`) 필수.
- **재실행 메커니즘**: 작업 스케줄러(`schtasks /run /tn "ZeusClientAgent"`)를 우선 호출하여 대화형 윈도우 세션과 트레이 UI 정상 복구.

## 5. PC별 환경 차이(셋팅값) 확인 및 개별 분기 정책 (Per-PC Environment & DPI Adaptation)
- **PC별 환경 다양성 인식**: 각 PC마다 디스플레이 해상도, DPI 배율(100%, 125%, 150%), 모니터 비율, 윈도우 환경설정이 다를 수 있음을 항상 전제한다.
- **동적 감지 및 분기 적용**: 코딩/디버깅 시 고정 픽셀(너비/높이)이나 고정 마우스 좌표에 의존하지 않고, Windows API(`GetDpiForSystem()`, `GetSystemMetrics()`)로 실시간 배율을 감지하여 동적 스케일링하거나 PC별 셋팅값에 맞춰 최적 설정을 다르게 적용한다.
- **Win32 메시지 직결 우선**: 마우스 좌표 오차를 원천 배제하기 위해 `WM_SETTEXT (0x000C)`, `BM_CLICK (0x00F5)` 등의 메모리/메시지 직결 주입 방식을 최우선 활용한다.

## 6. 피카(PICA) 관리프로그램 화면 기준 대조 및 제우스 상태 일치 원칙 (PICA Counter Screen Alignment)
- **피카 화면 최우선 기준**: 좌석 상태(사용중, 대기잠금, 오프라인) 판단 및 디버깅 시 반드시 카운터 PC의 피카 관리프로그램 실제 화면을 캡처/참고하여 제우스 프로그램의 상태와 정확히 맞추어 검증한다.
- **상태 100% 일치 보장**: 피카 화면에 대기(잠금)로 표시된 좌석은 제우스 대시보드에서도 정확히 `잠김(대기)`으로 표시되고, 손님 이용/관리자 로그인 좌석만 `사용중(잠금해제)`으로 표시되도록 정밀 판정한다.
- **손님 이용 중 PC 절대 불간섭 (CRITICAL)**: 피카 카운터 화면에서 손님이 이용 중인 PC(예: PC-01 등)는 원격 재부팅, 에이전트 강제 업데이트, 프로세스 조작 등 일체의 간섭을 엄격히 금지한다.

## 7. Windows GUI 프로세스 기동 및 무인 제어 표준 규칙 (황금 프롬프트 규칙 / Mandatory)
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