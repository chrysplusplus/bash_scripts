#!/usr/bin/env bash

# assuming mapfile
mapfile -t players < <( playerctl -l ) || exit 1
mapfile -t statuses < <( playerctl -a status ) || exit 1

for index in ${!statuses[@]}; do
  if [ "${statuses[$index]}" == "Playing" ]; then
    metadata=$(playerctl -p "${players[$index]}" metadata --format "{{artist}} - {{title}}")
    break
  fi
done

echo "$metadata"
