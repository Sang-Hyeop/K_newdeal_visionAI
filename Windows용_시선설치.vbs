' Windows 공용 설치: 이 파일을 더블클릭 → 바탕화면에 「시선」바로가기 생성
' (어느 PC든 프로젝트 폴더만 있으면 동작. 특정 사용자 경로 없음)
Option Explicit

Dim sh, fso, root, ps1, rc

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = root & "\dashboard\packaging\windows\make_shortcut.ps1"

If Not fso.FileExists(root & "\dashboard_desktop.py") Then
  MsgBox "dashboard_desktop.py 가 없습니다." & vbCrLf & _
         "프로젝트 ZIP/폴더를 통째로 풀었는지 확인하세요.", vbCritical, "시선 설치"
  WScript.Quit 1
End If
If Not fso.FileExists(ps1) Then
  MsgBox "dashboard\packaging\windows\make_shortcut.ps1 을 찾지 못했습니다.", vbCritical, "시선 설치"
  WScript.Quit 1
End If

sh.CurrentDirectory = root
rc = sh.Run( _
  "powershell -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """", _
  0, True)

If rc <> 0 Then
  MsgBox "설치에 실패했습니다." & vbCrLf & _
         "PowerShell 실행이 막혀 있지 않은지 확인하세요.", vbCritical, "시선 설치"
  WScript.Quit 1
End If

MsgBox "설치가 끝났습니다.", vbInformation, "시선 설치"
