#!/usr/bin/env bash

get_metadata() {
  echo $(playerctl -p "$1" metadata --format "{{artist}} - {{title}}")
}

# assuming mapfile
mapfile -t players < <( playerctl -l ) || exit 1
mapfile -t statuses < <( playerctl -a status ) || exit 1

# players that are currently "Playing" take priority
for index in "${!statuses[@]}"; do
  if [ "${statuses[$index]}" == "Playing" ]; then
    player="${players[$index]}"
    metadata=$(get_metadata "$player")
    prefix=""
    break
  fi
done

# if nothing is playing, then take the first player that is paused
if [[ ! "$metadata" ]]; then
  if [ "${statuses[0]}" == "Paused" ]; then
    player="${players[0]}"
    metadata=$(get_metadata "$player")
    prefix="(Paused) "
  fi
fi

echo "${prefix}${metadata}"
