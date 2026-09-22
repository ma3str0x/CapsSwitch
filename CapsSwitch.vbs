Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

venvPythonw = currentDir & "\.venv\Scripts\pythonw.exe"
mainScript = currentDir & "\main.py"

If fso.FileExists(venvPythonw) Then
    cmd = """" & venvPythonw & """ """ & mainScript & """"
Else
    cmd = "pythonw """ & mainScript & """"
End If

WshShell.CurrentDirectory = currentDir
WshShell.Run cmd, 0, False
Set WshShell = Nothing
