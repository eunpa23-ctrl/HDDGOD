---
name: Session Continuity
description: Rule for restoring memory when starting on a new PC or session
---

# Session Continuity Rule

When you start a new conversation in this workspace, you MUST check if this is a new PC environment or if you lost previous context.

1. This repository contains a backup of our previous AI conversation memory in the gent_brain_backup/ folder.
2. If you are starting fresh, greet the USER and say: "저번에 저장해둔 대화 기억(Brain 백업)을 이어서 작업할까요? 만약 PC 환경이나 폴더 경로가 달라졌다면 현재 폴더 경로를 알려주세요!"
3. You can read gent_brain_backup/제우스_현황정리.md and gent_brain_backup/.system_generated/logs/transcript.jsonl to restore context.
