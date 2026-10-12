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