"""Build the independent menu launcher with an optional application icon."""
from pathlib import Path
import json
import os
import subprocess
import tempfile

from .release import LAUNCHER_NAME


def read_application_icons(executable):
    """Read the executable's native icon images and groups."""
    import pefile
    from .patcher import resources

    icon_types = {pefile.RESOURCE_TYPE["RT_ICON"], pefile.RESOURCE_TYPE["RT_GROUP_ICON"]}
    with pefile.PE(str(executable)) as source:
        if not hasattr(source, "DIRECTORY_ENTRY_RESOURCE"):
            raise ValueError("The icon source has no executable resources")
        icons = {key: data for key, data in resources(source).items() if key[0] in icon_types}
    if {key[0] for key in icons} != icon_types:
        raise ValueError("The icon source must contain both icon images and an icon group")
    return icons


def embed_application_icon(launcher, source_exe):
    """Copy the icon images and icon groups into a staged launcher."""
    from .patcher import update_resources

    update_resources(launcher, read_application_icons(source_exe))


def build_launcher(repo, output, executable_name=None, *, icon_from=None):
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
    destination = output / LAUNCHER_NAME
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
    catalog_path = generated / "terminal-menu.json"
    expected = json.loads((repo / "translations" / "terminal-menu.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="moba-launcher-") as temporary:
        candidate = Path(temporary) / LAUNCHER_NAME
        args = [str(compiler), "/nologo", "/target:winexe", "/platform:anycpu", "/optimize+",
                "/reference:System.Windows.Forms.dll", "/reference:System.Web.Extensions.dll",
                "/out:" + str(candidate), str(temporary_source)]
        subprocess.run(args, check=True, cwd=repo, capture_output=True, text=True)
        if icon_from is not None:
            embed_application_icon(candidate, icon_from)
        subprocess.run([str(candidate), "--catalog", str(catalog_path)], check=True, cwd=output)
        actual = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
        if actual != expected:
            raise ValueError("The compiled launcher catalog does not match the reviewed translations")
        with destination.open("xb") as compiled:
            compiled.write(candidate.read_bytes())
    return destination
