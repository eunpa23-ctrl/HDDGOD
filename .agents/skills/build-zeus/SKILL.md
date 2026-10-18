---
name: build-zeus
description: HDDGOD 프로젝트의 클라이언트(ZeusAgent) 및 서버(ZeusServer)를 빌드하고 배포를 준비하는 표준 가이드입니다.
---

# Zeus 빌드 및 배포 워크플로우 (HDDGOD)

이 스킬은 HDDGOD 프로젝트에서 에이전트가 실행 파일(.exe)을 생성(빌드)하고 배포를 준비할 때 지켜야 할 일련의 절차를 정의합니다. 사용자가 "제우스 빌드해줘" 또는 "서버/클라이언트 말아줘"라고 요청할 때 이 스킬을 활용하세요.

## 1. 사전 환경 점검
1. 패키지 확인: `requirements.txt` 또는 `0_라이브러리_자동설치.bat`를 참고하여 빌드에 필요한 모듈(예: `pyinstaller`)이 제대로 설치되어 있는지 확인합니다.
2. 잔여 파일 정리: 깔끔한 빌드를 위해 기존의 `build/` 폴더와 `dist/` 폴더 내의 과거 결과물을 백업하거나 삭제할지 사용자에게 먼저 물어봅니다.

## 2. 서버 및 클라이언트 빌드
프로젝트 루트 경로에서 아래의 명령어를 순차적으로 실행하여 빌드를 진행합니다.

*   **서버 빌드 (ZeusServer)**
    ```powershell
    pyinstaller ZeusServer.spec --clean
    ```
*   **클라이언트 빌드 (ZeusAgent)**
    ```powershell
    pyinstaller ZeusAgent.spec --clean
    ```

## 3. 빌드 검증 및 배포 준비
1. 빌드가 완료되면 `dist/` 폴더로 이동하여 `ZeusServer.exe`와 `ZeusAgent.exe` 파일이 정상적으로 생성되었는지 확인합니다.
2. 파일이 확인되면 사용자에게 빌드 성공 여부를 보고하고, 다음 단계(예: `deploy/` 폴더로 이동하거나 테스트 실행)를 진행할지 물어봅니다.
