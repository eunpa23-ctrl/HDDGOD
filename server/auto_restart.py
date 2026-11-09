# -*- coding: utf-8 -*-
import sys, os, time, subprocess

def run():
    time.sleep(1.2)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(root_dir, 'run_server.py')
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([sys.executable, target], cwd=root_dir, creationflags=DETACHED_PROCESS, close_fds=True)

if __name__ == '__main__':
    run()
