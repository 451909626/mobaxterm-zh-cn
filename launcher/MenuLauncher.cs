using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Reflection;

[assembly: AssemblyTitle("MobaXterm 中文菜单启动器")]
[assembly: AssemblyDescription("Local terminal-menu label localization; preserves menu command IDs and state")]
[assembly: AssemblyVersion("2.6.0.0")]
[assembly: AssemblyFileVersion("2.6.0.0")]

internal static class MenuLauncher {
    const string MainFile = "";
    const string MinimumVersion = "26.5";
    const uint ByPosition = 0x400, StringMask = 0x40, MenuPopupStart = 6;
    const uint MenuMessage = 0x1E1;
    static string Target;
    static readonly List<Label> Labels = new List<Label> {
        new Label(400,"Copy","复制"),
        new Label(368,"Copy All","复制全部"),
        new Label(832,"Copy formatted text (RTF)","复制带格式文本 (RTF)"),
        new Label(416,"Paste\tShift+INSERT","粘贴\tShift+INSERT"),
        new Label(624,"Find\tCtrl+Shift+F","查找\tCtrl+Shift+F"),
        new Label(uint.MaxValue,"Font settings","字体设置"),
        new Label(5648,"Use internal font \"MobaFont\"","使用内置字体 \"MobaFont\""),
        new Label(5680,"Use internal font \"MobaFira\"","使用内置字体 \"MobaFira\""),
        new Label(5664,"Use internal font \"MobaFanta\"","使用内置字体 \"MobaFanta\""),
        new Label(5632,"Display font ligatures","显示字体连字"),
        new Label(800,"Increase font size\tCtrl+MousewheelUp","增大字号\tCtrl+MousewheelUp"),
        new Label(816,"Decrease font size\tCtrl+MousewheelDown","减小字号\tCtrl+MousewheelDown"),
        new Label(864,"Reset font size to default\tCtrl+0","恢复默认字号\tCtrl+0"),
        new Label(uint.MaxValue,"Terminal display","终端显示"),
        new Label(112,"Reset terminal output","重置终端输出"),
        new Label(96,"Clear terminal scrollback","清空终端滚动缓冲区"),
        new Label(768,"Set terminal title","设置终端标题"),
        new Label(688,"Toggle terminal scrollbar","显示或隐藏终端滚动条"),
        new Label(384,"Fullscreen terminal\tF11","终端全屏\tF11"),
        new Label(4992,"Read-only terminal","只读终端"),
        new Label(uint.MaxValue,"Syntax highlighting","语法高亮"),
        new Label(4096,"Default","默认"),
        new Label(4112,"Error/Warning/Success keywords","错误/警告/成功关键字"),
        new Label(4128,"Unix shell script","Unix Shell 脚本"),
        new Label(4144,"Cisco (network configuration)","Cisco（网络配置）"),
        new Label(4160,"Perl syntax","Perl 语法"),
        new Label(4176,"SQL syntax","SQL 语法"),
        new Label(592,"Execute macro\tCtrl+SPACE","执行宏\tCtrl+SPACE"),
        new Label(608,"Record new macro","录制新宏"),
        new Label(5008,"Record terminal output to file","录制终端输出到文件"),
        new Label(640,"Save to file\tCtrl+Shift+S","保存到文件\tCtrl+Shift+S"),
        new Label(656,"Print\tCtrl+Shift+P","打印\tCtrl+Shift+P"),
        new Label(288,"Receive file using Z-modem","使用 Z-modem 接收文件"),
        new Label(304,"Send file using Z-modem","使用 Z-modem 发送文件"),
        new Label(80,"Change current terminal settings...","更改当前终端设置..."),
        new Label(16,"Event Log","事件日志")
    };
    sealed class Label {
        public uint Id; public string English, Chinese;
        public Label(uint id,string english,string chinese) { Id=id;English=english;Chinese=chinese; }
    }
    static HashSet<uint> Allowed = new HashSet<uint>();
    static List<IntPtr> Terminals = new List<IntPtr>();
    static List<IntPtr> MainWindows = new List<IntPtr>();
    static ApplicationContext Context;
    static System.Windows.Forms.Timer Timer;
    static WinEventProc HookCallback;
    static IntPtr Hook;
    static string AuditPath;
    static DateTime LastSeen, LastScan, LastAudit;
    static bool Seen;
    static int Changed, Errors, Popups;
    static List<object> LastPopup = new List<object>();

    [StructLayout(LayoutKind.Sequential)] struct MENUITEMINFO {
        public uint cbSize,fMask,fType,fState,wID;
        public IntPtr hSubMenu,hbmpChecked,hbmpUnchecked;
        public UIntPtr dwItemData;
        public IntPtr dwTypeData;
        public uint cch;
        public IntPtr hbmpItem;
    }
    delegate bool EnumProc(IntPtr hwnd,IntPtr arg);
    delegate void WinEventProc(IntPtr hook,uint ev,IntPtr hwnd,int obj,int child,uint thread,uint time);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc proc,IntPtr arg);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr hwnd,EnumProc proc,IntPtr arg);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr hwnd,StringBuilder text,int size);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
    [DllImport("kernel32.dll")] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder path,ref uint size);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("user32.dll")] static extern IntPtr GetSystemMenu(IntPtr hwnd,bool revert);
    [DllImport("user32.dll")] static extern int GetMenuItemCount(IntPtr menu);
    [DllImport("user32.dll")] static extern IntPtr GetSubMenu(IntPtr menu,int position);
    [DllImport("user32.dll")] static extern uint GetMenuItemID(IntPtr menu,int position);
    [DllImport("user32.dll")] static extern uint GetMenuState(IntPtr menu,uint position,uint flags);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetMenuString(IntPtr menu,uint position,StringBuilder text,int size,uint flags);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool SetMenuItemInfo(IntPtr menu,uint position,bool byPosition,ref MENUITEMINFO info);
    [DllImport("user32.dll")] static extern IntPtr SetWinEventHook(uint min,uint max,IntPtr module,WinEventProc proc,uint pid,uint thread,uint flags);
    [DllImport("user32.dll")] static extern bool UnhookWinEvent(IntPtr hook);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr SendMessageTimeout(IntPtr hwnd,uint msg,IntPtr wp,IntPtr lp,uint flags,uint timeout,out UIntPtr result);
    [DllImport("user32.dll")] static extern bool RedrawWindow(IntPtr hwnd,IntPtr rect,IntPtr region,uint flags);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hwnd,int command);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr hwnd);

    static string ClassOf(IntPtr hwnd) { var b=new StringBuilder(256);GetClassName(hwnd,b,b.Capacity);return b.ToString(); }
    static uint PidOf(IntPtr hwnd) { uint id;GetWindowThreadProcessId(hwnd,out id);return id; }
    static string PathOf(uint pid) {
        IntPtr p=OpenProcess(0x1000,false,pid);if(p==IntPtr.Zero)return "";
        try { var b=new StringBuilder(32768);uint size=(uint)b.Capacity;return QueryFullProcessImageName(p,0,b,ref size)?b.ToString():""; }
        finally { CloseHandle(p); }
    }
    static string MenuText(IntPtr menu,uint pos) { var b=new StringBuilder(1024);GetMenuString(menu,pos,b,b.Capacity,ByPosition);return b.ToString(); }

    static Version ValidateTarget(string path) {
        if(!File.Exists(path))throw new FileNotFoundException("请将启动器与 MobaXterm 程序放在同一目录。");
        var info=FileVersionInfo.GetVersionInfo(path);
        if(!String.Equals(info.ProductName,"MobaXterm",StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("目标文件的产品信息不是 MobaXterm。");
        var version=new Version(info.FileMajorPart,info.FileMinorPart,info.FileBuildPart,info.FilePrivatePart);
        if(version<new Version(MinimumVersion))
            throw new InvalidOperationException("终端菜单启动器仅面向 MobaXterm "+MinimumVersion+" 及以后版本。");
        return version;
    }
    static string ResolveTarget(string name) {
        string directory=AppDomain.CurrentDomain.BaseDirectory;
        if(!String.IsNullOrEmpty(name)) {
            if(Path.GetFileName(name)!=name || name.IndexOfAny(Path.GetInvalidFileNameChars())>=0 ||
               !name.EndsWith(".exe",StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("请指定同目录的 EXE 文件名。");
            string path=Path.GetFullPath(Path.Combine(directory,name));ValidateTarget(path);return path;
        }
        var candidates=new List<string>();
        foreach(string path in Directory.GetFiles(directory,"MobaXterm*.exe")) {
            try { ValidateTarget(path);candidates.Add(path); }
            catch(InvalidOperationException) { }
            catch(ArgumentException) { }
        }
        if(candidates.Count==0)
            throw new FileNotFoundException("本目录未找到 MobaXterm "+MinimumVersion+" 或更新版本。请将启动器放到便携版程序旁边。");
        if(candidates.Count>1)
            throw new InvalidOperationException("本目录有多个可用的 MobaXterm 程序。请用 --exe 文件名 指定要启动的程序，或仅保留一个目标程序。");
        return Path.GetFullPath(candidates[0]);
    }

    static void RefreshTargets() {
        var roots=new List<IntPtr>();var allowed=new HashSet<uint>();var terminals=new List<IntPtr>();
        EnumWindows(delegate(IntPtr hwnd,IntPtr arg) {
            if(ClassOf(hwnd)!="TMobaXtermForm")return true;
            uint pid=PidOf(hwnd);
            if(!String.Equals(PathOf(pid),Target,StringComparison.OrdinalIgnoreCase))return true;
            roots.Add(hwnd);allowed.Add(pid);
            EnumChildWindows(hwnd,delegate(IntPtr child,IntPtr unused) {
                if(ClassOf(child)=="CMoTTY") { terminals.Add(child);allowed.Add(PidOf(child)); }
                return true;
            },IntPtr.Zero);
            return true;
        },IntPtr.Zero);
        MainWindows=roots;Allowed=allowed;Terminals=terminals;
        if(roots.Count>0) { Seen=true;LastSeen=DateTime.UtcNow; }
    }

    static void WalkMenu(IntPtr menu,int depth,HashSet<IntPtr> visited) {
        if(menu==IntPtr.Zero || depth>8 || !visited.Add(menu))return;
        int count=GetMenuItemCount(menu);if(count<0 || count>200)return;
        for(uint i=0;i<count;i++) {
            string text=MenuText(menu,i);uint id=GetMenuItemID(menu,(int)i);
            foreach(Label label in Labels) {
                if(label.Id!=id || label.English!=text)continue;
                uint state=GetMenuState(menu,i,ByPosition);IntPtr sub=GetSubMenu(menu,(int)i);
                IntPtr str=Marshal.StringToHGlobalUni(label.Chinese);
                try {
                    MENUITEMINFO info=new MENUITEMINFO();info.cbSize=(uint)Marshal.SizeOf(typeof(MENUITEMINFO));
                    info.fMask=StringMask;info.dwTypeData=str;info.cch=(uint)label.Chinese.Length;
                    // MIIM_STRING changes only the caption: never ID, state, item data or submenu.
                    if(SetMenuItemInfo(menu,i,true,ref info)) {
                        Changed++;
                        if(GetMenuItemID(menu,(int)i)!=id || GetSubMenu(menu,(int)i)!=sub)Errors++;
                        // States may legitimately change concurrently in the host. Do not write them.
                    } else Errors++;
                } finally { Marshal.FreeHGlobal(str); }
                break;
            }
            WalkMenu(GetSubMenu(menu,(int)i),depth+1,visited);
        }
    }
    static void TranslateSystemMenus() {
        foreach(IntPtr term in Terminals)WalkMenu(GetSystemMenu(term,false),0,new HashSet<IntPtr>());
    }
    static void ScanPopups() {
        EnumWindows(delegate(IntPtr hwnd,IntPtr arg) {
            if(ClassOf(hwnd)!="#32768" || !Allowed.Contains(PidOf(hwnd)))return true;
            UIntPtr result;
            if(SendMessageTimeout(hwnd,MenuMessage,IntPtr.Zero,IntPtr.Zero,2,100,out result)==IntPtr.Zero)return true;
            IntPtr menu=new IntPtr(unchecked((long)result.ToUInt64()));
            if(menu==IntPtr.Zero)return true;
            int before=Changed;WalkMenu(menu,0,new HashSet<IntPtr>());
            if(Changed!=before)RedrawWindow(hwnd,IntPtr.Zero,IntPtr.Zero,0x101);
            LastPopup=Snapshot(menu);
            return true;
        },IntPtr.Zero);
    }
    static List<object> Snapshot(IntPtr menu) {
        var rows=new List<object>();int count=GetMenuItemCount(menu);
        for(uint i=0;i<count && i<200;i++)rows.Add(new { position=i,id=GetMenuItemID(menu,(int)i),text=MenuText(menu,i),state=GetMenuState(menu,i,ByPosition) });
        return rows;
    }
    static void WriteAudit() {
        if(String.IsNullOrEmpty(AuditPath))return;
        try {
            var state=new { release="R2.5",date=DateTime.Now.ToString("o"),target=Target,
                main_windows=MainWindows.Count,terminal_windows=Terminals.Count,
                catalog_labels=Labels.Count,labels_changed=Changed,errors=Errors,
                popup_events=Popups,last_popup=LastPopup,
                scope="Menu strings only; no terminal input, clipboard access or file-transfer actions" };
            File.WriteAllText(AuditPath,new JavaScriptSerializer().Serialize(state),new UTF8Encoding(false));
        } catch { }
    }
    static void Tick(object sender,EventArgs args) {
        RefreshTargets();
        if((DateTime.UtcNow-LastScan).TotalSeconds>=2) { TranslateSystemMenus();LastScan=DateTime.UtcNow; }
        ScanPopups();
        if((DateTime.UtcNow-LastAudit).TotalSeconds>=1) { WriteAudit();LastAudit=DateTime.UtcNow; }
        if((Seen && MainWindows.Count==0 && (DateTime.UtcNow-LastSeen).TotalSeconds>2) ||
           (!Seen && (DateTime.UtcNow-LastSeen).TotalSeconds>30))Context.ExitThread();
    }
    [STAThread] static int Main(string[] args) {
        string inspection=null;
        try {
            uint attach=0;string catalog=null;string targetName=MainFile;
            for(int i=0;i<args.Length;i++) {
                if(args[i]=="--audit" && i+1<args.Length)AuditPath=Path.GetFullPath(args[++i]);
                else if(args[i]=="--attach" && i+1<args.Length)attach=uint.Parse(args[++i]);
                else if(args[i]=="--catalog" && i+1<args.Length)catalog=Path.GetFullPath(args[++i]);
                else if(args[i]=="--inspect" && i+1<args.Length)inspection=Path.GetFullPath(args[++i]);
                else if(args[i]=="--exe" && i+1<args.Length)targetName=args[++i];
                else throw new ArgumentException("无法识别的启动选项。");
            }
            if(catalog!=null) {
                var rows=new List<object>();foreach(Label label in Labels)rows.Add(new {id=label.Id,english=label.English,chinese=label.Chinese});
                File.WriteAllText(catalog,new JavaScriptSerializer().Serialize(rows),new UTF8Encoding(false));return 0;
            }
            Target=ResolveTarget(targetName);
            if(inspection!=null) {
                var report=new { ok=true,main_file=Path.GetFileName(Target),detected_version=ValidateTarget(Target).ToString(),
                    minimum_version=MinimumVersion,selection=String.IsNullOrEmpty(targetName)?"auto":"explicit",catalog_labels=Labels.Count };
                File.WriteAllText(inspection,new JavaScriptSerializer().Serialize(report),new UTF8Encoding(false));return 0;
            }
            if(attach!=0 && !String.Equals(PathOf(attach),Target,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("指定窗口不属于本目录的汉化版。");
            string token;using(var hash=SHA256.Create())token=BitConverter.ToString(hash.ComputeHash(Encoding.Unicode.GetBytes(Target.ToUpperInvariant()))).Replace("-","").Substring(0,24);
            bool created;using(var mutex=new Mutex(true,"Local\\MobaMenuHan_"+token,out created)) {
                RefreshTargets();
                if(!created) {
                    if(MainWindows.Count>0) {
                        foreach(IntPtr hwnd in MainWindows) { if(IsIconic(hwnd))ShowWindow(hwnd,9);SetForegroundWindow(hwnd); }
                        return 0;
                    }
                    // Allow an immediate restart while the previous monitor is exiting.
                    bool acquired;
                    try { acquired=mutex.WaitOne(4000); }
                    catch(AbandonedMutexException) { acquired=true; }
                    if(!acquired)return 0;
                }
                if(MainWindows.Count==0 && attach==0) {
                    var start=new ProcessStartInfo(Target,"-i \""+Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"MobaXterm.ini")+"\"");
                    start.WorkingDirectory=AppDomain.CurrentDomain.BaseDirectory;start.UseShellExecute=false;
                    Process.Start(start);
                }
                LastSeen=DateTime.UtcNow;Context=new ApplicationContext();
                HookCallback=delegate(IntPtr hook,uint ev,IntPtr hwnd,int obj,int child,uint thread,uint time) {
                    if(hwnd==IntPtr.Zero || !Allowed.Contains(PidOf(hwnd)))return;
                    Popups++;TranslateSystemMenus();ScanPopups();WriteAudit();
                };
                Hook=SetWinEventHook(MenuPopupStart,MenuPopupStart,IntPtr.Zero,HookCallback,0,0,2);
                if(Hook==IntPtr.Zero)throw new InvalidOperationException("菜单汉化暂时无法启动，请重新运行启动器。");
                Timer=new System.Windows.Forms.Timer();Timer.Interval=500;Timer.Tick+=Tick;Timer.Start();
                Tick(null,EventArgs.Empty);Application.Run(Context);
                Timer.Stop();UnhookWinEvent(Hook);WriteAudit();mutex.ReleaseMutex();
            }
            return 0;
        } catch(Exception ex) {
            if(inspection!=null) {
                File.WriteAllText(inspection,new JavaScriptSerializer().Serialize(new {ok=false,error=ex.Message}),new UTF8Encoding(false));
            } else MessageBox.Show(ex.Message,"汉化版启动提示",MessageBoxButtons.OK,MessageBoxIcon.Information);
            return 1;
        }
    }
}
