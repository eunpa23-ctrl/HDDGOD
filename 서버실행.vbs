Set objShell = CreateObject("WScript.Shell")
strPath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
objShell.CurrentDirectory = strPath
objShell.Run "python server_supervisor.py", 0, False
