#!/usr/bin/env bash

# Quick script for creating m3u playlists for a directory of mp3 files

create_playlist() {
  printf "#EXTM3U\n"
  find "$dir" -type f -name '*.mp3' | sort
}

dir="$1"
if [[ -z "$dir" ]]; then
  printf "Error: directory required\n"
  exit 1
elif [[ ! -d "$dir" ]]; then
  printf "Error: input is not a directory\n"
  exit 1
fi

current_m3u="${dir%/}.m3u"
old_m3u="${dir%/}_old.m3u"

if [[ -a "$current_m3u" ]]; then
  echo "Renaming old playlist file"
  mv "$current_m3u" "$old_m3u"
  create_playlist > "$current_m3u"
  diff -y --suppress-common-lines "$old_m3u" "$current_m3u" | less
  echo "Removing old playlist file"
  rm "$old_m3u"
  exit 0
else
  echo "There is no old playlist file; cannot find diff"
  echo "Will create playlist anyway"
  create_playlist > "$current_m3u"
  exit 0
fi


