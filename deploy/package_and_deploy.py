# -*- coding: utf-8 -*-
"""
ZeusAgent onedir 배포 패키징 및 동기화 스크립트
"""
import os
import shutil
import zipfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_AGENT = os.path.join(ROOT_DIR, "dist", "ZeusAgent")
CORE_DIR = os.path.join(ROOT_DIR, "deploy", "ClientDeploy", "core")

if not os.path.exists(DIST_AGENT):
    print(f"Error: {DIST_AGENT} not found.")
    exit(1)

# 1. 필수 설정 파일들을 dist/ZeusAgent/ 에 동기화
files_to_copy = ["config.ini", "netflix.ico", "version.txt"]
for f in files_to_copy:
    src = os.path.join(CORE_DIR, f)
    dst = os.path.join(DIST_AGENT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)

# 버전 읽기 및 기록
ver = "1.0.23"
ver_path = os.path.join(CORE_DIR, "version.txt")
if os.path.exists(ver_path):
    with open(ver_path, "r", encoding="utf-8") as vf:
        ver = vf.read().replace('\ufeff', '').strip()

with open(os.path.join(DIST_AGENT, "version.txt"), "w", encoding="utf-8") as vf:
    vf.write(ver)

# 2. ZeusAgent.zip 압축 파일 생성
zip_path = os.path.join(ROOT_DIR, "dist", "ZeusAgent.zip")
print(f"Creating ZeusAgent.zip (v{ver})...".encode("ascii", "replace").decode("ascii"))
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(DIST_AGENT):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, DIST_AGENT)
            zipf.write(full_path, rel_path)
print(f"Created {zip_path} ({os.path.getsize(zip_path):,} bytes)")

# 3. 배포 대상 위치 동기화
destinations = [
    os.path.join(ROOT_DIR, "deploy", "ClientDeploy"),
    os.path.join(ROOT_DIR, "dist", "deploy", "ClientDeploy"),
    r"G:\내 드라이브\PROJECT\HDDGOD\deploy\ClientDeploy"
]

for dest in destinations:
    try:
        os.makedirs(dest, exist_ok=True)
        # zip 복사
        shutil.copy2(zip_path, os.path.join(dest, "ZeusAgent.zip"))
        
        # 폴더 통째 복사
        target_agent_dir = os.path.join(dest, "ZeusAgent")
        if os.path.exists(target_agent_dir):
            shutil.rmtree(target_agent_dir)
        shutil.copytree(DIST_AGENT, target_agent_dir)
        
        # version.txt 복사
        shutil.copy2(os.path.join(DIST_AGENT, "version.txt"), os.path.join(dest, "version.txt"))
        print(f"Deployed to: {dest}")
    except Exception as e:
        print(f"Error deploying to {dest}: {e}")

print("Sync completed!")
