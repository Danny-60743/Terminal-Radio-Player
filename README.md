# Terminal Radio

Video demo: [Watch here] https://youtu.be/vMqpdGkit6U?si=-30zzhPkmlb3CtgQ

## Description

Terminal Radio is a Python program for listening to online radio stations from the terminal. Users can save their favourite stations, choose a station to play, and remove stations they no longer want.

During playback, an equalizer displays bars that respond to the audio, showing activity from bass to treble. Station names and stream URLs are stored in `stations.csv`, so saved stations remain available between sessions.

## Features

- Play online radio streams.
- Add and delete saved stations.
- Store station names and URLs in a CSV file.
- Recreate a missing `stations.csv` with a default station.
- Clean up whitespace and remove station entries with missing names or URLs.
- Display an audio equalizer that reactes to the audio.
- Use debug mode to see mpv's playback output for debugging.

## Requirements

- Python 3
- mpv
- FFmpeg
- Python packages listed in `requirements.txt`: NumPy for the equalizer and pytest for testing.

Open a terminal in the project folder and install the Python packages:

```sh
python -m pip install -r requirements.txt
```

Install mpv and FFmpeg using the instructions for your operating system. Both commands must be available in your terminal. You can check this with:

```sh
mpv --version
ffmpeg -version
```

If you use VS Code, you can run these commands in its integrated terminal.

## Usage

Run the program from the project folder:

```sh
python project.py
```

Choose a station by entering its number.

- Enter `A` to add a station, then provide its name and an HTTP or HTTPS stream URL.
- Enter `D` to delete a station, then provide its name and confirm the deletion.
- Enter `Q` or `exit` to quit.
- Press `Ctrl+C` during playback to return to the menu.

Use a direct audio stream URL when adding a station. A station's normal website address may not point to playable audio.

To run in debug mode:

```sh
python project.py -d
```

Debug mode plays the selected stream directly through mpv and shows its output instead of displaying the equalizer. This can help identify playback problems.

An internet connection is required to play stations. Playback also depends on the station's stream being available.

## Project Files

- `project.py`: Handles the menu, station management, CSV and URL validation, and playback selection.
- `equalizer.py`: Uses FFmpeg to decode audio, NumPy to calculate frequency levels, and mpv to play audio while displaying the equalizer.
- `stations.csv`: Stores saved station names and stream URLs under the `station,url` header. The program creates it if it is missing.
- `test_project.py`: Contains tests for CSV recovery and cleanup, URL validation, station loading, equalizer functions, and playback handling.
- `requirements.txt`: Lists the Python packages needed for the project and its tests.

## Testing

Run the tests from the project folder:

```sh
python -m pytest -v test_project.py
```

The CSV tests use temporary folders to protect saved stations. The playback test simulates playback rather than connecting to live streams or launching audio programs.

## Design Decisions

