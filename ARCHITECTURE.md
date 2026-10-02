# ⚡ 제우스 HDD PROTECTOR (Zeus HDD Protector)
## 24시간 무인 매장 PC 통합 관제 솔루션 - 전체 상세 설계서

> **최종 업데이트:** 2026-10-02 | **현재 버전:** v1.0.8 | **GitHub:** [eunpa23-ctrl/HDDGOD](https://github.com/eunpa23-ctrl/HDDGOD)

---

## 1. 환경 정보

| 항목 | 값 |
|------|-----|
| 운영체제 | Windows 10 Pro 64비트 |
| 카운터 PC (서버) | `192.168.0.100` |
| 손님 PC (클라이언트) | `192.168.0.91~` (최대 10대) |
| 클라이언트 설치 경로 | `C:\ZeusAgent\` |
| 프로젝트 경로 (개발) | `G:\내 드라이브\PROJECT\HDDGOD` |
| 서버 실행 경로 | `C:\Users\USER\Documents\HDDGOD` |
| 서버 동기화 방법 | `robocopy` (G드라이브 → C드라이브) |
| 개발 언어 | Python 3.14 |
| 빌드 도구 | PyInstaller 6.22 (단일 exe, `C:\ZeusAgent\temp` 압축 해제) |

---

## 2. 핵심 기능 목록

### 1) 🛡️ 디스크 순간복구 (UWF)
- Windows UWF(Unified Write Filter)로 C드라이브를 보호
- 재부팅 시 RAM 오버레이가 소멸 → 바이러스·파일 변조·설정 변경 즉시 원상복구
- **예외 보존 경로:** 팟플레이어 설정(`C:\Program Files\DAUM\PotPlayer`), 크롬 프로필(`%LOCALAPPDATA%\Google\Chrome\User Data`)

### 2) 🔌 전원 안전 관리
- 시작메뉴 **종료 버튼 숨김**, **다시시작만 표시**
- 물리 전원 버튼 → 절전 전환 (꺼짐 방지)
- 볼륨 100% 강제 고정, 모니터 절전 비활성화

### 3) ⚡ 하트비트 감시 & WOL 자동 켜기
- 3초 주기로 클라이언트 ↔ 서버 생존 신호 교환
- 10초 이상 무응답 → 비정상 꺼짐 판정 → MAC 주소로 WOL 매직 패킷 자동 발송

### 4) 🎬 넷플릭스 자동 로그인 (CDP 기반 2단계)
- 크롬을 CDP 디버깅 포트 9222로 실행
- **2단계 로그인 구조 자동 처리:**
  1. 이메일(`eunpa23@naver.com`) 입력 → 다음 버튼 클릭
  2. 비밀번호(`@Oep0325`) 입력 → 로그인 버튼 클릭
- `Input.insertText` CDP 원시 명령으로 실제 키보드 타이핑과 동일하게 처리

### 5) 📧 넷플릭스 OTP 4자리 자동 처리
- OTP 화면 감지 시 서버에 `OTP_REQUIRED` 신호 전송
- 서버 → 네이버 IMAP(`imap.naver.com:993`) 접속 (앱 비밀번호: `UDT766M1ZSCP`)
- 최대 35초간 2초마다 메일함 폴링 → 4자리 코드 자동 추출 → 손님 PC에 자동 타이핑
- 35초 초과 시 fallback: 카카오 알림톡 + 수동 입력 웹페이지

### 6) 🚨 자율 진단 텔레메트리
- 클라이언트가 비정상 종료 시 `crash.log` 자동 기록
- 서버 재접속 시 `crash.log`를 `ERROR_REPORT` 패킷으로 서버 전송
- 서버는 `server/error_reports.log`에 누적 기록

### 7) 🔄 원격 자동 업데이트 (OTA)
- 클라이언트 부팅 시 서버에 `/api/version` 조회
- 버전 다를 경우 `/api/download/update`에서 exe 다운로드 (HTTP 스트리밍)
- `update.bat` 생성 후 실행 → 자체 종료 → 새 버전으로 재시작
- 대시보드에서 "전체 에이전트 업데이트" 버튼으로 강제 업데이트 가능

### 8) 🎛️ 관리 대시보드
- 10대 PC 실시간 카드 (전원/UWF상태/넷플릭스상태/IP/버전)
- 일괄 제어: 전체 보호 켜기/끄기, 전체 재부팅, 전체 WOL, 전체 업데이트
- PC 대수 동적 추가/축소, MAC·IP 매핑 테이블 편집

### 9) 🖥️ 트레이 아이콘 UI
- 초록 방패(보호 중) / 주황 방패(유지보수) 실시간 표시
- 현재 버전 hover 표시 (예: `v1.0.8`)
- 관리자 비밀번호 인증 후 모드 전환

### 10) 📱 모바일 원격 제어 + Cloudflare Tunnel
- 스마트폰 브라우저에서 PC 화면 실시간 스트리밍 + 터치 제어
- `cloudflared`로 공유기 설정 없이 외부 HTTPS 접속

---

## 3. 파일 구조 (최신)

```text
HDDGOD/
├── ARCHITECTURE.md              ← 본 문서
├── ZeusAgent.spec               # PyInstaller 빌드 설정 (runtime_tmpdir=C:\ZeusAgent\temp)
├── run_client.py                # 클라이언트 부팅 엔트리포인트 (crash.log 수집 포함)
├── run_server.py                # 서버 부팅 엔트리포인트
├── server_supervisor.py         # 서버 자동 재시작 감시 데몬
├── .gitignore                   # build/, dist/, exe, log, cache 제외
│
├── client/
│   ├── client_agent.py          # 메인 루프 (OTA, 텔레메트리, WebSocket, 넷플릭스 감시)
│   ├── client_tray.py           # 트레이 아이콘 (버전 표시 포함)
│   ├── netflix_bot.py           # 넷플릭스 CDP 자동화 (2단계 로그인 + OTP 타이핑)
│   ├── uwf_controller.py        # UWF 순간복구 제어
│   ├── power_policy.py          # 전원 정책 (종료 숨김, 볼륨, WOL)
│   ├── windows_optimizer.py     # MS 방해화면 차단, 자동로그인 설정
│   ├── screen_streamer.py       # 화면 캡처 & 원격 입력 처리
│   ├── desktop_guard.py         # 바탕화면 아이콘·배경화면 복구
│   └── launch_netflix.py        # 넷플릭스 독립 실행 진입점
│
├── server/
│   ├── server_core.py           # FastAPI + WebSocket 서버 (ERROR_REPORT 수신기 포함)
│   ├── mail_otp_extractor.py    # 네이버 IMAP OTP 자동 추출 (2초 폴링, 35초 타임아웃)
│   ├── wol_watchdog.py          # 하트비트 감시 & WOL 자동 발송
│   ├── kakao_notifier.py        # 카카오 알림톡 OTP fallback
│   ├── remote_relay.py          # 화면 스트리밍 중계기
│   ├── tunnel_manager.py        # Cloudflare Tunnel 관리
│   ├── pc_mapping.json          # PC 좌석·MAC·IP 매핑 저장
│   └── templates/
│       ├── dashboard.html       # PC/모바일 반응형 관제 대시보드
│       ├── mobile_dashboard.html
│       ├── remote_view.html     # 원격 제어 스트리밍 화면
│       └── otp_input.html       # OTP 수동 입력 fallback 페이지
│
├── common/
│   ├── config.py                # 공통 설정 (계정, IP, 포트 - fallback값 포함)
│   ├── protocol.py              # 패킷 타입 정의 (ERROR_REPORT 포함)
│   └── auto_installer.py        # 오프라인 패키지 자동 설치
│
├── deploy/
│   └── ClientDeploy/            # 네트워크 공유폴더 (\\192.168.0.100\deploy)
│       ├── 1_설치하기.bat        # 원클릭 설치 (CP949, 기존 프로세스 강제종료 후 복사)
│       ├── 2_정밀검수.bat        # 설치 후 자가진단
│       └── core/
│           ├── ZeusAgent.exe    # 최신 빌드 (.gitignore 제외)
│           ├── version.txt      # 현재 버전 (서버가 /api/version으로 제공)
│           └── config.ini       # 계정·서버IP 설정 (.gitignore 제외)
│
├── packages/                    # 오프라인 설치용 .whl/.tar.gz 패키지
└── tools/                       # 레지스트리·배치 유지보수 스크립트
```

---

## 4. WebSocket 패킷 타입 (protocol.py)

| 패킷 | 방향 | 설명 |
|------|------|------|
| `HEARTBEAT` | 클라이언트→서버 | 3초 주기 생존신호 + 상태보고 |
| `COMMAND` | 서버→클라이언트 | 재부팅/업데이트/UWF제어 등 원격 명령 |
| `OTP_REQUIRED` | 클라이언트→서버 | 넷플릭스 OTP 화면 감지 알림 |
| `OTP_SUBMIT` | 서버→클라이언트 | 4자리 인증코드 전달 |
| `SCREEN_FRAME` | 클라이언트→서버 | 화면 스트리밍 프레임 |
| `REMOTE_INPUT` | 서버→클라이언트 | 원격 마우스/키보드 입력 |
| `ERROR_REPORT` | 클라이언트→서버 | crash.log 자동 전송 (텔레메트리) |

---

## 5. 빌드 & 배포 절차

```powershell
# 1. 버전 번프
Set-Content deploy\ClientDeploy\core\version.txt "1.0.X"

# 2. 빌드
pyinstaller --noconfirm ZeusAgent.spec

# 3. 배포 폴더 복사
copy dist\ZeusAgent.exe deploy\ClientDeploy\core\

# 4. 서버 동기화 (G드라이브 → C드라이브)
robocopy "G:\내 드라이브\PROJECT\HDDGOD" "C:\Users\USER\Documents\HDDGOD" /MIR /XD .git __pycache__ venv build dist

# 5. GitHub push
git add .
git commit -m "vX.X.X - 변경 내용"
git push origin master
```
