import os
import time
import sys
import subprocess
import csv
from urllib.parse import urlsplit
import equalizer


def main():
    while True:
        os.system("clear")
        get_channel = get_menu()
        validate(get_channel)


def get_stations():
    stations = []
    with open("stations.csv") as file:
        reader = csv.DictReader(file)
        for row in reader:
            stations.append(row)

    return stations


def validate_csv():
    try:
        stations = []
        with open("stations.csv") as file:
            reader = csv.DictReader(file)
            valid = ["station", "url"]
            if reader.fieldnames != valid:
                raise KeyError
            for row in reader:
                stations.append(row)

        valid = []
        for i in stations:
            if i["station"] and i["url"]:
                station_name = i["station"].strip()
                station_url = i["url"].strip()
                if station_name and station_url:
                    valid.append(
                        {"station": station_name, "url": station_url})

        write(valid)
    except (FileNotFoundError, UnicodeDecodeError, KeyError):
        stations = [
            {"station": "BBC", "url": 'http://as-hls-ww-live.akamaized.net/pool_01505109/live/ww/bbc_radio_one/bbc_radio_one.isml/bbc_radio_one-audio%3d96000.norewind.m3u8'}]
        write(stations)


def write(stations):
    with open("stations.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["station", "url"])
        writer.writeheader()
        for details in stations:
            writer.writerow(details)


def get_menu():
    validate_csv()
    stations = get_stations()
    print(f"=" * 42)
    print("RADIO".center(42))
    print(f"=" * 42)
    for i, row in enumerate(stations, 1):
        print(f"{i}. {row['station'].upper()}")
    print("Press A to add a station")
    print("Press D to delete a station")
    print("Press q or exit to quit")
    choice = input("Choose: ").strip()

    return choice


def validate(option):
    if option.lower() == "a":
        add()

    elif option.lower() == "d":
        delete()

    elif option.lower() in ["exit", "q"]:
        os.system("clear")
        sys.exit()

    elif option.isdigit():
        play(option)

    else:
        print("Invalid input")
        time.sleep(0.5)


def validate_url(url):
    try:
        parts = urlsplit(url)
        if parts.scheme and parts.hostname:
            for i in parts.hostname:
                if i.isspace():
                    return False

            return True

        else:
            return False

    except ValueError:
        return False


def add():
    stations = get_stations()
    while True:
        try:
            os.system("clear")
            print("=" * 42)
            print("Add a station".center(42))
            print("=" * 42)
            station_name = input("Enter station name: ").strip()
            station_url = input("Enter station url: ").strip()
            if station_url.lower().startswith(("https://", "http://")):
                if station_name != "":
                    if validate_url(station_url) is True:
                        for i in stations:
                            if station_name.lower() == i["station"].lower():
                                print(f"{station_name} already exists")
                                time.sleep(1)
                                break

                        else:
                            stations.append(
                                {"station": station_name, "url": station_url})
                            write(stations)
                            break

                    else:
                        print("Invalid URL")
                        time.sleep(1)

                else:
                    print("Invalid station name")
                    time.sleep(1)
            else:
                print("Invalid URL")
                time.sleep(1)

        except KeyboardInterrupt:
            return


def delete():
    stations = get_stations()
    while True:
        os.system("clear")
        try:
            print("=" * 42)
            print("Remove a station".center(42))
            print("=" * 42)
            station_name = input("Enter Station name: ").strip().lower()
            if station_name != "":
                for i in stations:
                    if station_name == i['station'].lower():
                        confirm = input(
                            f"Are you sure you want to delete {station_name} (yes/no): ").strip().lower()
                        if confirm in ["y", "yes"]:
                            stations.remove(i)
                            write(stations)
                            return
                        else:
                            break

                else:
                    print("Station doesn't exist")
                    time.sleep(1)

            else:
                print("Invalid station name")
                time.sleep(1)

        except KeyboardInterrupt:
            break


def play(option):
    stations = get_stations()

    try:
        option = int(option) - 1
        if option < 0:
            print("Invalid option")
        else:
            debug_mode = len(sys.argv) == 2 and sys.argv[1] == "-d"
            try:
                listen = stations[option]
                if debug_mode:
                    try:
                        os.system("clear")
                        subprocess.run(
                            ["mpv", listen["url"]]
                        )

                    except KeyboardInterrupt:
                        return

                else:
                    equalizer.main(listen["url"])
                    time.sleep(0.5)

            except IndexError:
                print("Invalid option")
                time.sleep(1)

    except ValueError:
        print("Invalid option")
        time.sleep(1)


if __name__ == "__main__":
    main()
