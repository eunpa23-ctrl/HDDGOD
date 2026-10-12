# 🤝 [HDDGOD / 제우스] 세션 인수인계 및 프로젝트 현황 요약 (Session Handover)

> **생성 시각**: 2026-10-12 08:17:32  
> **현재 프로젝트 기준 경로**: C:\HDDGOD  
> **GitHub 원격 저장소**: https://github.com/eunpa23-ctrl/HDDGOD.git (origin/master)

---

## 1. 프로젝트 개요 및 현재 구조
* **목적**: PC방 다수 클라이언트 PC를 중앙에서 관제/보호하는 '제우스 HDD PROTECTOR' 시스템
* **메인 작업 위치**: C:\HDDGOD (C드라이브 루트로 이전 및 찌꺼기 파일 일괄 청소 완료)
* **주요 구성 요소**:
  - server/ : FastAPI + WebSocket 기반 카운터 관제 서버 (ZeusServer, 포트 8000)
    - 대시보드 (/), 모바일 관제 (/mobile), WebSocket 실시간 브로드캐스트
  - client/ : 클라이언트 백그라운드 에이전트 서비스 (ZeusAgent, 단일 실행 파일 v3.8.1)
    - UWF 순간복구 제어, 넷플릭스 자동화, 피카라이브 와치독, 전원/화면 원격 제어
  - deploy/ClientDeploy/ : 클라이언트 배포 패키지 (core/ZeusAgent.exe 24.9MB, 1_설치하기.bat 등)
  - .agents/ : Antigravity 전용 빌드 스킬 (uild-zeus)
  - NEW_PC_ANTIGRAVITY_SETUP_GUIDE.md : 새 PC 환경 구축 및 테스트 가이드

---

## 2. 최근 완료된 핵심 작업 내역

### ① 순간복구(UWF) 보호 모드 중 원격 업데이트 3중 안전 체계
* **문제점**: 순간복구 보호 모드(PROTECTED)에서는 업데이트를 받아도 재부팅 시 이전 버전으로 롤백됨.
* **해결책**:
  1. **UI 스마트 안내**: 대시보드/모바일에서 보호 모드 PC 업데이트 클릭 시, 롤백 경고와 함께 [유지보수 모드로 전환 후 재부팅] 안내 모달 표시 및 원클릭 전환(DISABLE_UWF).
  2. **에이전트 2중 방어**: 보호 모드 상태에서 원격 강제 업데이트 수신 시, RAM 가상 영역에 쓰지 않고 스스로 eboot_to_maintenance()를 호출하여 유지보수 모드로 자동 전환.
  3. **디스크 영구 설치 및 봉인**: 유지보수 모드 부팅 후 새 파일(v3.8.1)을 물리 디스크에 영구 설치 -> 대시보드에서 [🛡️ 세팅저장&보호] 버튼 클릭으로 최신 버전을 새 원본으로 고정.

### ② 배포 및 업데이트 전 과정 안전 딜레이 & 타임아웃 강화
* **부팅 시 네트워크 안정화**: 부팅 직후 DHCP/LAN 지연을 고려해 버전 조회 최대 4회 재시도 (각 2초 간격, 총 8초 유예).
* **동시 다운로드 분산**: 다중 PC 일제 요청 방지용 미세 분산(지터 0~1.5초) 및 서버 순차 스태거(0.3초).
* **다운로드 신뢰성**: 30초 타임아웃 및 일시적 오류 시 최대 3회 재시도 (각 2초 간격).
* **프로세스 교체 (update.bat)**: 	askkill 전후 각 2초 대기, 파일 락 해제 재시도 최대 20회(20초) 확장.
* **UWF 재부팅 안정화**: 윈도우 OS의 레지스트리/디스크 플러시 시간을 위해 shutdown /r /t 3 /f (3초 유예) 적용.

### ③ 단일 독립 실행 파일 빌드 및 배포
* 외부 DLL(_internal) 의존성 없이 단독 실행 가능한 **ZeusAgent.exe (24.9MB, v3.8.1)** 빌드 및 deploy/ClientDeploy/core/ 배치 완료.

### ④ 프로젝트 폴더 이전 및 청소
* 임시 테스트 스크립트(	est*), 오류 이미지(error*), 빌드 캐시(uild/) 24개 항목 삭제.
* 프로젝트 위치를 C:\HDDGOD로 확정하고 Antigravity 스킬 및 설정 동기화.

---

## 3. 새 대화 시작 시 바로 진행할 수 있는 작업
1. **GitHub 커밋 & 푸시**:
   - C:\HDDGOD에서 최신 수정 사항 및 가이드 문서를 GitHub 원격 저장소로 커밋/푸시:
     git add . && git commit -m "Feat: Complete UWF safe update, delay optimizations, and C:\HDDGOD migration" && git push origin master
2. **새 PC 테스트**:
   - 새 PC에서 NEW_PC_ANTIGRAVITY_SETUP_GUIDE.md를 참고하여 git clone 후 로컬/클라이언트 테스트 진행.