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
