using System.Diagnostics;
using System.IO;

class Sisun
{
    static void Main()
    {
        string here = @"C:\code\code\safety test";
        string vbs = Path.Combine(here, "sisun.vbs");
        Process.Start(new ProcessStartInfo
        {
            FileName = "wscript.exe",
            Arguments = "\"" + vbs + "\"",
            WorkingDirectory = here,
            UseShellExecute = false,
            WindowStyle = ProcessWindowStyle.Hidden
        });
    }
}
