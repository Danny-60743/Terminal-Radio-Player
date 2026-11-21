import os
from itertools import cycle
import selectors
import subprocess
import sys
import tempfile
import time

import numpy as np

BARS = 16
MAX_HEIGHT = 16
SAMPLE_RATE = 44100
CHUNK_SAMPLES = 2205  # 50 ms of mono audio.
CHUNK_BYTES = CHUNK_SAMPLES * 2
DISPLAY_FLOOR_DB = -60.0

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def make_heights(samples, count=BARS, max_height=MAX_HEIGHT):
    """Turn normalized audio samples (-1 to 1) into bass-to-treble heights."""
    samples = np.asarray(samples, dtype=np.float64)
    if len(samples) < 3:
        return [0] * count

    # Taper the chunk's edges to reduce leakage into neighbouring frequencies.
    window = np.hanning(len(samples))
    spectrum = np.fft.rfft((samples - samples.mean()) * window)
    frequencies = np.fft.rfftfreq(len(samples), d=1 / SAMPLE_RATE)

    # Correct for the window and for the omitted negative frequencies.
    power = np.abs(spectrum) ** 2 / (len(samples) * np.sum(window ** 2))
    power[1:-1] *= 2
    if len(samples) % 2:
        power[-1] *= 2

    band_edges = np.geomspace(40, 16000, count + 1)
    heights = []
    for low, high in zip(band_edges[:-1], band_edges[1:]):
        in_band = (frequencies >= low) & (frequencies < high)
        band_power = float(np.sum(power[in_band]))
        # Use the same fixed decibel scale as the experiment.
        level_db = 10 * np.log10(max(band_power, 1e-12))
        fraction = np.clip((level_db - DISPLAY_FLOOR_DB) / -DISPLAY_FLOOR_DB, 0, 1)
        heights.append(round(float(fraction) * max_height))
    return heights


def color_for(level, max_height):
    # bottom third green, middle third yellow, top third red
    if level > max_height * 2 / 3:
        return RED
    if level > max_height / 3:
        return YELLOW
    return GREEN


def make_frame(heights, max_height):
    # Build the picture row by row, from the top row down.
    rows = []
    for level in range(max_height, 0, -1):
        row = ""
        for h in heights:
            # a bar reaches this row only if it is tall enough
            row += "\u2588\u2588 " if h >= level else "   "
        # one color per row, reset before the newline so it can't leak
        rows.append(color_for(level, max_height) + row + RESET)
    return "\n".join(rows)


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def show_connecting(symbol):
    print(
        f"\033[H\033[2K{symbol} Connecting...\n"
        "\033[2KCtrl+C to return to the menu\033[J",
        end="", flush=True,
    )


def main(url):
    """Decode one stream and send the same audio to mpv and the display."""
    decoder = player = None
    failure = None
    with tempfile.TemporaryFile(mode="w+t") as decoder_errors, \
            tempfile.TemporaryFile(mode="w+t") as player_errors:
        try:
            spinner = cycle(("◐", "◓", "◑", "◒"))
            connecting = True
            print("\033[2J\033[?25l", end="", flush=True)
            show_connecting(next(spinner))
            next_spin = time.monotonic() + 0.1
            player = subprocess.Popen([
                "mpv", "--no-config", "--no-terminal", "--no-video",
                "--audio-display=no", "--cache=no", "--demuxer-readahead-secs=0",
                "--demuxer=rawaudio", f"--demuxer-rawaudio-rate={SAMPLE_RATE}",
                "--demuxer-rawaudio-channels=mono", "--demuxer-rawaudio-format=s16le",
                "-",
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=player_errors)
            decoder = subprocess.Popen([
                "ffmpeg", "-nostdin", "-v", "error", "-re",
                "-rw_timeout", "5000000", "-i", url,
                "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
                "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1",
            ], stdout=subprocess.PIPE, stderr=decoder_errors, bufsize=0)

            with selectors.DefaultSelector() as selector:
                selector.register(decoder.stdout, selectors.EVENT_READ)
                pending = bytearray()
                while True:
                    if player.poll() is not None:
                        raise RuntimeError("The audio player stopped")
                    if connecting and time.monotonic() >= next_spin:
                        show_connecting(next(spinner))
                        next_spin = time.monotonic() + 0.1
                    if not selector.select(timeout=0.1):
                        continue
                    data = os.read(decoder.stdout.fileno(), CHUNK_BYTES - len(pending))
                    ended = not data
                    if ended:
                        decoder.wait(timeout=3)
                        if decoder.returncode:
                            raise RuntimeError("Could not decode this station")
                        if not pending:
                            break
                    else:
                        pending.extend(data)
                        if len(pending) < CHUNK_BYTES:
                            continue

                    chunk = bytes(pending)
                    pending.clear()
                    player.stdin.write(chunk)
                    player.stdin.flush()
                    samples = np.frombuffer(chunk, dtype="<i2").astype(np.float64) / 32768.0
                    frame = make_frame(make_heights(samples), MAX_HEIGHT)
                    labels = f"{'Bass (40 Hz)':<30}Treble (16 kHz)"
                    lines = ["RADIO", frame, labels, "Ctrl+C to return to the menu"]
                    output = "\n".join(
                        "\033[2K" + line for line in "\n".join(lines).splitlines())
                    print("\033[H" + output + "\033[J", end="", flush=True)
                    connecting = False
                    if ended:
                        break

            # On a natural end, let mpv finish the audio already in its buffer.
            player.stdin.close()
            player.wait(timeout=5)
            if player.returncode:
                raise RuntimeError("The audio player could not finish playback")
        except KeyboardInterrupt:
            pass
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            failure = str(error)
        finally:
            stop_process(decoder)
            stop_process(player)
            if decoder is not None and decoder.stdout is not None:
                decoder.stdout.close()
            if player is not None and player.stdin is not None:
                try:
                    player.stdin.close()
                except BrokenPipeError:
                    pass
            print("\033[?25h" + RESET + "\n", flush=True)

        if failure:
            print(f"Playback error: {failure}")
            for label, log in [("FFmpeg", decoder_errors), ("mpv", player_errors)]:
                log.seek(0)
                details = log.read().strip()
                if details:
                    print(f"{label}: {details[-1000:]}")
            time.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python equalizer.py STREAM_URL")
    main(sys.argv[1])
