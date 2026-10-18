' 시선 안전관제 — Windows 더블클릭 실행 (검은 콘솔 없음)
' Windows에서 시선 데스크톱을 바로 실행 (설치 없이).
Option Explicit

Dim sh, fso, root, script, pyw, cmd, i, p

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
script = root & "\dashboard_desktop.py"

If Not fso.FileExists(script) Then
  MsgBox "dashboard_desktop.py 를 찾지 못했습니다." & vbCrLf & _
         "이 vbs는 프로젝트 루트(dashboard_desktop.py 옆)에 두세요." & vbCrLf & root, _
         vbCritical, "시선"
  WScript.Quit 1
End If

pyw = FindPythonW(fso, sh)
If pyw = "" Then
  MsgBox "Python 을 찾지 못했습니다." & vbCrLf & _
         "Python 3.10+ 설치 후 pip install gradio pandas 를 해 주세요." & vbCrLf & _
         "권장: Anaconda safety 환경", vbCritical, "시선"
  WScript.Quit 1
End If

sh.CurrentDirectory = root
cmd = """" & pyw & """ """ & script & """"
sh.Run cmd, 0, False
WScript.Quit 0

Function FindPythonW(fso, sh)
  Dim envHome, envLocal, envUser, paths, i, p
  envHome = sh.ExpandEnvironmentStrings("%USERPROFILE%")
  envLocal = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%")
  envUser = sh.ExpandEnvironmentStrings("%USERPROFILE%")

  paths = Array( _
    envUser & "\anaconda3\envs\safety\pythonw.exe", _
    envUser & "\miniconda3\envs\safety\pythonw.exe", _
    envUser & "\Anaconda3\envs\safety\pythonw.exe", _
    "C:\ProgramData\anaconda3\envs\safety\pythonw.exe", _
    "C:\anaconda3\envs\safety\pythonw.exe", _
    envLocal & "\Programs\Python\Python312\pythonw.exe", _
    envLocal & "\Programs\Python\Python311\pythonw.exe", _
    envLocal & "\Programs\Python\Python310\pythonw.exe", _
    envHome & "\AppData\Local\Programs\Python\Python312\pythonw.exe", _
    envHome & "\AppData\Local\Programs\Python\Python311\pythonw.exe", _
    envHome & "\AppData\Local\Programs\Python\Python310\pythonw.exe" _
  )

  For i = 0 To UBound(paths)
    p = paths(i)
    If fso.FileExists(p) Then
      FindPythonW = p
      Exit Function
    End If
  Next

  Dim folder, sub
  folder = envLocal & "\Python"
  If fso.FolderExists(folder) Then
    For Each sub In fso.GetFolder(folder).SubFolders
      p = sub.Path & "\pythonw.exe"
      If fso.FileExists(p) Then
        FindPythonW = p
        Exit Function
      End If
    Next
  End If

  On Error Resume Next
  p = sh.ExpandEnvironmentStrings("%PATH%")
  On Error GoTo 0
  FindPythonW = WhichOnPath(fso, p, "pythonw.exe")
  If FindPythonW = "" Then FindPythonW = WhichOnPath(fso, p, "python.exe")
End Function

Function WhichOnPath(fso, pathEnv, exeName)
  Dim parts, i, cand
  WhichOnPath = ""
  parts = Split(pathEnv, ";")
  For i = 0 To UBound(parts)
    If Trim(parts(i)) <> "" Then
      cand = fso.BuildPath(Trim(parts(i)), exeName)
      If fso.FileExists(cand) Then
        WhichOnPath = cand
        Exit Function
      End If
    End If
  Next
End Function
