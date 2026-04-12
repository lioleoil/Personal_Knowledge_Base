' Claude Agent Monitor — 콘솔 창 없이 조용히 실행
' 더블클릭 또는 wscript 실행 모두 지원
Dim WshShell, scriptDir
Set WshShell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
WshShell.Run "pythonw """ & scriptDir & "monitor.py""", 0, False
