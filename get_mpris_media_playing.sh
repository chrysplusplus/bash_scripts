#!/bin/env bash

# assuming mapfile
mapfile -t players < <( playerctl -l )
mapfile -t statuses < <( playerctl -a status )

for index in ${!statuses[@]}; do
  if [ "${statuses[$index]}" == "Playing" ]; then
    metadata=$(playerctl -p "${players[$index]}" metadata --format "{{artist}} - {{title}}")
    break
  fi
done

echo "$metadata"
