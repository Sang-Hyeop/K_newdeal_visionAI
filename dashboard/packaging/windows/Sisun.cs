// 선택용: 시선.vbs 를 감싸는 작은 exe 를 만들 때 사용합니다.
// 빌드 예: csc /nologo /target:winexe /out:Sisun.exe Sisun.cs
// exe 는 프로젝트 루트(시선.vbs / dashboard_desktop.py 옆)에 두고 실행하세요.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

static class Sisun
{
    [STAThread]
    static void Main()
    {
        string here = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

        // exe 가 dashboard\packaging\windows\ 에 있으면 세 단계 위로
        string[] roots =
        {
            here,
            Path.GetFullPath(Path.Combine(here, "..")),
            Path.GetFullPath(Path.Combine(here, "..", "..")),
            Path.GetFullPath(Path.Combine(here, "..", "..", "..")),
        };

        string vbs = null;
        string desktopPy = null;
        string root = null;
        foreach (string candidate in roots)
        {
            string v = Path.Combine(candidate, "시선.vbs");
            string p = Path.Combine(candidate, "dashboard_desktop.py");
            if (File.Exists(v) || File.Exists(p))
            {
                root = candidate;
                if (File.Exists(v)) vbs = v;
                if (File.Exists(p)) desktopPy = p;
                break;
            }
        }

        if (root == null)
        {
            MessageBox.Show(
                "시선.vbs 또는 dashboard_desktop.py 를 찾지 못했습니다.\n" +
                "Sisun.exe 를 프로젝트 루트에 두세요.",
                "시선",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        var psi = new ProcessStartInfo
        {
            WorkingDirectory = root,
            UseShellExecute = false,
            WindowStyle = ProcessWindowStyle.Hidden,
            CreateNoWindow = true,
        };

        if (vbs != null)
        {
            psi.FileName = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                "wscript.exe");
            psi.Arguments = "\"" + vbs + "\"";
        }
        else
        {
            string py = FindPythonW();
            if (string.IsNullOrEmpty(py))
            {
                MessageBox.Show(
                    "Python(pythonw) 을 찾지 못했습니다.",
                    "시선",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }
            psi.FileName = py;
            psi.Arguments = "\"" + desktopPy + "\"";
        }

        try
        {
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "시선", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    static string FindPythonW()
    {
        string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] cands =
        {
            Path.Combine(home, @"anaconda3\envs\safety\pythonw.exe"),
            Path.Combine(home, @"miniconda3\envs\safety\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python312\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python311\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python310\pythonw.exe"),
        };
        foreach (string c in cands)
        {
            if (File.Exists(c)) return c;
        }
        return null;
    }
}
