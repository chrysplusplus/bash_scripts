#!/usr/bin/env bash

ON="'true::false'"
OFF="'false::false'"

current_state=$(gsettings get org.nemo.desktop desktop-layout)

case "$current_state" in
  "$ON")
    new_state="$OFF"
    ;;
  "$OFF")
    new_state="$ON"
    ;;
  *)
    new_state="$current_state"
    ;;
esac

gsettings set org.nemo.desktop desktop-layout "$new_state"
