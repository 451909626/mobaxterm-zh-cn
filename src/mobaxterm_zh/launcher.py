"""Build the independent menu launcher without copying vendor icons or binaries."""
from pathlib import Path
import json
import os
import subprocess


def build_launcher(repo, output, executable_name=None):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if executable_name is not None:
        if (Path(executable_name).name != executable_name or "/" in executable_name
                or "\\" in executable_name or not executable_name.lower().endswith(".exe")):
            raise ValueError("The target must be an executable basename, not a path")
        if any(c in executable_name for c in '\r\n\0"<>:|?*'):
            raise ValueError("Invalid target filename")
    if os.name != "nt":
        raise RuntimeError("The menu launcher must be built on Windows")
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [windows / "Microsoft.NET" / name / "v4.0.30319" / "csc.exe"
                  for name in ("Framework64", "Framework")]
    compiler = next((p for p in candidates if p.is_file()), None)
    if compiler is None:
        raise RuntimeError("The .NET Framework C# compiler was not found")
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "MobaXterm.exe"
    if destination.exists():
        raise FileExistsError("Choose a new output directory; the existing launcher is preserved")
    source = (repo / "launcher" / "MenuLauncher.cs").read_text(encoding="utf-8")
    marker = 'const string MainFile = "";'
    if source.count(marker) != 1:
        raise ValueError("Unexpected launcher source template")
    source = source.replace(marker, 'const string MainFile = "' + (executable_name or "") + '";')
    generated = output / ".generated"
    generated.mkdir(exist_ok=True)
    temporary_source = generated / "MenuLauncher.cs"
    temporary_source.write_text(source, encoding="utf-8-sig")
    args = [str(compiler), "/nologo", "/target:winexe", "/platform:anycpu", "/optimize+",
            "/reference:System.Windows.Forms.dll", "/reference:System.Web.Extensions.dll",
            "/out:" + str(destination), str(temporary_source)]
    # No vendor icon, resource, original executable, or plugin is embedded.
    subprocess.run(args, check=True, cwd=repo, capture_output=True, text=True)
    catalog_path = generated / "terminal-menu.json"
    subprocess.run([str(destination), "--catalog", str(catalog_path)], check=True, cwd=output)
    actual = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    expected = json.loads((repo / "translations" / "terminal-menu.json").read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("The compiled launcher catalog does not match the reviewed translations")
    return destination
