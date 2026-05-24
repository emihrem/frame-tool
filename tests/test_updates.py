"""Tests for the GitHub release update check."""

import json
import urllib.error

import pytest

from frame_tool import updates
from frame_tool.updates import OPT_OUT_ENV, UpdateInfo, _parse_version, check_for_update


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _patch_urlopen(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> None:
    monkeypatch.setattr(updates.urllib.request, "urlopen", lambda *_a, **_k: _FakeResponse(payload))


def _patch_urlopen_to_raise(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise exc

    monkeypatch.setattr(updates.urllib.request, "urlopen", _boom)


class TestParseVersion:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("v0.3.0", (0, 3, 0)),
            ("0.3.0", (0, 3, 0)),
            ("V1.10.5", (1, 10, 5)),
            ("v2.0", (2, 0)),
        ],
    )
    def test_valid(self, raw: str, expected: tuple[int, ...]) -> None:
        assert _parse_version(raw) == expected

    @pytest.mark.parametrize("bad", ["", "v", "1.x.0", "v1.0-beta"])
    def test_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            _parse_version(bad)


class TestCheckForUpdate:
    def test_returns_info_when_newer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen(
            monkeypatch,
            {
                "tag_name": "v0.4.0",
                "html_url": "https://github.com/emihrem/frame-tool/releases/tag/v0.4.0",
                "name": "frame_tool v0.4.0",
            },
        )
        info = check_for_update(current_version="0.3.0")
        assert info == UpdateInfo(
            version="0.4.0",
            html_url="https://github.com/emihrem/frame-tool/releases/tag/v0.4.0",
            name="frame_tool v0.4.0",
        )

    def test_returns_none_when_same_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen(
            monkeypatch,
            {"tag_name": "v0.3.0", "html_url": "https://example.com"},
        )
        assert check_for_update(current_version="0.3.0") is None

    def test_returns_none_when_older(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen(
            monkeypatch,
            {"tag_name": "v0.1.0", "html_url": "https://example.com"},
        )
        assert check_for_update(current_version="0.3.0") is None

    def test_opt_out_short_circuits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(OPT_OUT_ENV, "1")
        # No need to patch urlopen — we should never hit it.
        called: list[bool] = []

        def _spy(*_a: object, **_k: object) -> None:
            called.append(True)
            raise AssertionError("urlopen should not be called when opted out")

        monkeypatch.setattr(updates.urllib.request, "urlopen", _spy)
        assert check_for_update(current_version="0.0.1") is None
        assert called == []

    def test_swallows_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen_to_raise(monkeypatch, urllib.error.URLError("offline"))
        assert check_for_update(current_version="0.3.0") is None

    def test_swallows_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen_to_raise(monkeypatch, TimeoutError())
        assert check_for_update(current_version="0.3.0") is None

    def test_swallows_bad_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)

        class _BadResponse:
            def read(self) -> bytes:
                return b"{not json"

            def __enter__(self) -> "_BadResponse":
                return self

            def __exit__(self, *_: object) -> None:
                return None

        monkeypatch.setattr(updates.urllib.request, "urlopen", lambda *_a, **_k: _BadResponse())
        assert check_for_update(current_version="0.3.0") is None

    def test_handles_missing_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen(monkeypatch, {"tag_name": "v9.9.9"})  # no html_url
        assert check_for_update(current_version="0.3.0") is None

    def test_handles_malformed_tag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(OPT_OUT_ENV, raising=False)
        _patch_urlopen(monkeypatch, {"tag_name": "release-q1-2026", "html_url": "https://x"})
        assert check_for_update(current_version="0.3.0") is None
