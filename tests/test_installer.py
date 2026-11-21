from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import urllib.request

import pytest

from conftest import PAYLOAD, FakeResponse, make_emulator
from ludex_emulators import installer
from ludex_emulators.installer import InstallError

PLATFORM = "linux-x86_64"


def _opener(response):
    calls = []

    def opener(url):
        calls.append(url)
        return response

    opener.calls = calls
    return opener


def _install(root, emu, response, **kw):
    return installer.install(root, emu, opener=_opener(response), platform=PLATFORM, report=lambda _m: None, **kw)


def test_happy_install(root):
    emu = make_emulator()
    path = _install(root, emu, FakeResponse(PAYLOAD))
    assert path == root / "emulators" / "demo" / "1.0.0" / "demo.AppImage"
    assert path.read_bytes() == PAYLOAD and path.stat().st_mode & 0o777 == 0o755
    assert not list(root.rglob("*.part")) and not (root / "emulators" / "demo.failed").exists()
    assert installer.installed_version(root, emu) == "1.0.0"


def test_reinstall_downloads_nothing(root):
    emu = make_emulator()
    _install(root, emu, FakeResponse(PAYLOAD))
    opener = _opener(FakeResponse(PAYLOAD))
    installer.install(root, emu, opener=opener, platform=PLATFORM)
    assert opener.calls == []


@pytest.mark.parametrize("response,code", [
    (FakeResponse(b"y" * 4096), "checksum_mismatch"),
    (FakeResponse(PAYLOAD[:100]), "size_mismatch"),
    (FakeResponse(PAYLOAD + b"z" * 10), "size_mismatch"),
    (FakeResponse(PAYLOAD, length=999), "size_mismatch"),
    (FakeResponse(PAYLOAD, url="http://example.com/x"), "insecure_redirect"),
    (FakeResponse(PAYLOAD, fail_after=0), "download_failed"),
])
def test_failures_leave_nothing(root, response, code):
    emu = make_emulator()
    with pytest.raises(InstallError) as exc:
        _install(root, emu, response)
    assert exc.value.code == code
    assert not list(root.rglob("*.part"))
    assert installer.installed_version(root, emu) is None
    assert not (root / "emulators" / "demo" / "1.0.0").exists()
    assert installer.last_failure(root, emu) == code


def test_oversize_stream_stops_reading(root, monkeypatch):
    monkeypatch.setattr(installer, "_CHUNK", 1024)
    response = FakeResponse(b"x" * 1_000_000)
    with pytest.raises(InstallError):
        _install(root, make_emulator(), response)
    assert response.read_total < 10_000


def test_success_clears_previous_failure(root):
    emu = make_emulator()
    with pytest.raises(InstallError):
        _install(root, emu, FakeResponse(b"y" * 4096))
    _install(root, emu, FakeResponse(PAYLOAD))
    assert installer.last_failure(root, emu) is None


def test_redirect_to_http_is_refused():
    handler = installer._HttpsOnlyRedirect()
    req = urllib.request.Request("https://example.com/a")
    with pytest.raises(InstallError) as exc:
        handler.redirect_request(req, None, 302, "Found", {}, "http://example.com/b")
    assert exc.value.code == "insecure_redirect"


def test_held_lock_blocks_install(root):
    emu = make_emulator()
    (root / "emulators").mkdir(parents=True)
    fd = os.open(root / "emulators" / "demo.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        assert installer.is_installing(root, emu)
        with pytest.raises(InstallError) as exc:
            _install(root, emu, FakeResponse(PAYLOAD))
        assert exc.value.code == "install_running"
        with pytest.raises(InstallError):
            installer.remove(root, emu)
    finally:
        os.close(fd)
    assert not installer.is_installing(root, emu)


def test_unsupported_platform(root):
    with pytest.raises(InstallError) as exc:
        installer.install(root, make_emulator(), opener=_opener(FakeResponse(PAYLOAD)), platform="darwin-arm64")
    assert exc.value.code == "unsupported_platform"


def test_update_removes_old_version(root):
    _install(root, make_emulator("1.0.0"), FakeResponse(PAYLOAD))
    _install(root, make_emulator("1.10.0"), FakeResponse(PAYLOAD))
    assert sorted(p.name for p in (root / "emulators" / "demo").iterdir()) == ["1.10.0"]


def test_remove(root):
    emu = make_emulator()
    _install(root, emu, FakeResponse(PAYLOAD))
    assert installer.remove(root, emu) is True
    assert installer.installed_version(root, emu) is None
    assert installer.remove(root, emu) is False


def test_installer_imports_without_ludex():
    code = (
        "import sys; sys.modules['ludex'] = None\n"
        "import ludex_emulators.installer, ludex_emulators.manifest, ludex_emulators.paths, ludex_emulators.__main__\n"
        "try:\n    import ludex_emulators.plugin\nexcept ImportError:\n    print('plugin-needs-ludex')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "plugin-needs-ludex"
