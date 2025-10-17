#!/usr/bin/env python3

from argparse import ArgumentParser
from dataclasses import dataclass
from mutagen.easyid3 import EasyID3
from pathlib import Path

@dataclass
class TrackMetadata:
    title: str
    artist: str
    album: str
    tracknumber: str

def readMetadata(path: Path) -> TrackMetadata:
    '''Read track metadata from file'''
    track = EasyID3(path)
    title = track["title"][0]
    artist = track["artist"][0]
    album = track["album"][0]
    tracknumber = track["tracknumber"][0]
    return TrackMetadata(title, artist, album, tracknumber)

# Porgram Arguments
argParser = ArgumentParser(prog = "printfmp3", description = "Print the metadata!")
argParser.add_argument("file", type = Path)
argParser.add_argument("-f", "--format", default = "{title}\n{artist}\n{album}")

def main():
    args = argParser.parse_args()
    metadata = readMetadata(args.file)

    print(args.format.format(**vars(metadata)))

if __name__ == "__main__":
    main()
