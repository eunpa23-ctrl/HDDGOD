# Zeus HDD Protector - Workspace Rules & Constraints

## 1. Path & Drive Rules (Crucial)
- **Drive & Path Starting Point**: All local operations, scripts, and file paths MUST start from `C:\` or `D:\` with pure English paths (e.g., `C:\Users\USER\Documents\HDDGOD`, `C:\ZeusAgent`).
- **No Korean Characters in Paths**: NEVER use, reference, or copy to paths containing Korean characters (e.g., `G:\내 드라이브` or any Korean folder names).
- **Client Installation Path**: The client installation path on all target PCs is strictly fixed to `C:\ZeusAgent\`.

## 2. System Identifiers & Windows Policies
- **English-Only System Names**: Windows Firewall rules, Defender exclusions, Task Scheduler jobs, process names, and service names must be 100% English alphanumeric (e.g., `ZeusAgent`, `ZeusAgent_Port8000`). Never use Korean strings for OS-level rule names.
- **Windows Defender Exclusions**: Automatically set `C:\ZeusAgent` as excluded directory via `Add-MpPreference -ExclusionPath "C:\ZeusAgent"`.

## 3. Encoding Standards
- **Python Source & File I/O**: All Python scripts must explicitly use UTF-8 (`open(path, "r", encoding="utf-8")`).
- **Network / Socket Communication**: WebSockets and HTTP APIs must exchange UTF-8 encoded JSON payloads (`json.dumps(..., ensure_ascii=False).encode("utf-8")`).
- **Configuration & Rule Files**: All configuration (`.ini`, `.json`) and documentation (`.md`) files must be saved in UTF-8 without BOM.

## 4. Packaging & Deployment Architecture
- **Strictly `--onedir` Mode**: Client binaries must always be packaged in `--onedir` mode (`ZeusAgent/` directory containing `ZeusAgent.exe` and `_internal/`). NEVER revert to `--onefile` to prevent `%TEMP%` DLL unpack errors (`python314.dll`) and SmartScreen blocks.
- **Deploy Packaging**: Local deployment artifacts reside in `deploy/ClientDeploy/` (`ZeusAgent/` and `ZeusAgent.zip`).

## 5. Session Continuity & Memory Restoration
- **Primary Single Source of Truth**: The latest verified working status and architecture is recorded in `agent_brain_backup/제우스_최종성공_현황.md`.
- **Session Resumption**: When a new session or PC environment starts, check `agent_brain_backup/제우스_최종성공_현황.md` first to preserve continuity.

## 6. User Communication
- Always communicate with the user politely and concisely in Korean.
