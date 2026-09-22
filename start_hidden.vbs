' Starts Findent in the background (no black window). Output goes to data\server.log
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c venv\Scripts\python.exe serve.py >> data\server.log 2>&1", 0, False
