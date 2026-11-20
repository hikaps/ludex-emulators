from __future__ import annotations

import hashlib
import io

import pytest

from ludex_emulators.manifest import Emulator

PAYLOAD = b"x" * 4096


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("LUDEX_EMULATORS_HOME", str(tmp_path / "state"))
    return tmp_path / "state"


def make_emulator(version: str = "1.0.0", payload: bytes = PAYLOAD) -> Emulator:
    return Emulator(
        "demo", "Demo", version, "linux-x86_64", "appimage", "demo.AppImage",
        "https://example.com/demo.AppImage", len(payload), hashlib.sha256(payload).hexdigest(),
        ("-x", "{rom}"), "https://example.com/release",
    )


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, url: str = "https://example.com/demo.AppImage", length: int | None = None, fail_after: int | None = None):
        super().__init__(data)
        self._url, self.headers = url, ({} if length is None else {"Content-Length": str(length)})
        self._fail_after = fail_after
        self.read_total = 0

    def geturl(self) -> str:
        return self._url

    def read(self, n: int = -1) -> bytes:
        if self._fail_after is not None and self.read_total >= self._fail_after:
            raise OSError("boom")
        chunk = super().read(n)
        self.read_total += len(chunk)
        return chunk
