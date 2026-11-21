from unittest.mock import patch

import pytest

from equalizer import GREEN, YELLOW, RED, color_for, make_heights
from project import get_stations, play, validate_csv, validate_url


def test_validate_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file = tmp_path / "stations.csv"

    # A missing file should be recreated with BBC.
    validate_csv()
    stations = get_stations()
    assert len(stations) == 1
    assert stations[0]["station"] == "BBC"

    # Bad headers and unreadable text should also restore the default.
    for contents in [b"name,link\nRadio,https://example.com/live\n", b"\xff\xfe"]:
        file.write_bytes(contents)
        validate_csv()
        assert get_stations() == stations

    file.write_text(
        "station,url\n"
        "  Radio One  ,  https://example.com/live  \n"
        ",https://example.com/unnamed\n"
        "No URL,\n",
        encoding="utf-8",
    )
    validate_csv()
    assert get_stations() == [
        {"station": "Radio One", "url": "https://example.com/live"}
    ]


def test_validate_url():
    assert validate_url("https://example.com/live") is True
    assert validate_url("http://example.com/radio.mp3") is True
    assert validate_url("") is False
    assert validate_url("example.com/live") is False
    assert validate_url("https://") is False
    assert validate_url("https://bad host.com/live") is False
    assert validate_url("https://[broken/live") is False


def test_get_stations(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file = tmp_path / "stations.csv"
    file.write_text(
        "station,url\n"
        "Radio One,https://example.com/one\n"
        "Radio Two,http://example.com/two\n",
        encoding="utf-8",
    )
    assert get_stations() == [
        {"station": "Radio One", "url": "https://example.com/one"},
        {"station": "Radio Two", "url": "http://example.com/two"},
    ]

    file.write_text("station,url\n", encoding="utf-8")
    assert get_stations() == []


def test_color_for():
    assert color_for(1, 9) == GREEN
    assert color_for(3, 9) == GREEN
    assert color_for(4, 9) == YELLOW
    assert color_for(6, 9) == YELLOW
    assert color_for(7, 9) == RED
    assert color_for(9, 9) == RED


def test_make_heights():
    assert make_heights([]) == [0] * 16
    assert make_heights([0, 0]) == [0] * 16
    assert make_heights([0] * 2205) == [0] * 16
    assert make_heights([0] * 2205, count=4) == [0] * 4


def test_play(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("project.time.sleep", lambda seconds: None)
    monkeypatch.setattr("project.os.system", lambda command: 0)
    monkeypatch.setattr("project.sys.argv", ["project.py"])
    file = tmp_path / "stations.csv"
    file.write_text(
        "station,url\nRadio One,https://example.com/live\n", encoding="utf-8"
    )

    # Replace playback so the test never connects to a station.
    with patch("project.equalizer.main") as player:
        for option in ["abc", "0", "-1", "2"]:
            play(option)
            assert capsys.readouterr().out == "Invalid option\n"
        player.assert_not_called()

        play("1")
        player.assert_called_once_with("https://example.com/live")

    monkeypatch.setattr("project.sys.argv", ["project.py", "-d"])
    with patch("project.subprocess.run", side_effect=KeyboardInterrupt):
        assert play("1") is None

    # Missing mpv and a missing CSV currently raise FileNotFoundError.
    with patch("project.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            play("1")

    file.unlink()
    with pytest.raises(FileNotFoundError):
        play("1")
