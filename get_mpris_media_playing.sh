#!/usr/bin/env bash

# TODO this script needs a bit of love, removing the getopts and just updating
# some of the coding techniques

# quiet mode is when the script only outputs that something is playing or
# paused, not what the media is called, which may be distracting
quiet_mode=0
quiet_flag_file="$HOME/.quiet_media"
if [[ -e "$quiet_flag_file" ]]; then
  quiet_mode=1
fi

# script arguments
declare -i LIMIT=-1

get_metadata() {
  echo $(playerctl -p "$1" metadata --format "{{artist}} - {{title}}")
}

usage() {
  echo "Usage: get_mpris_media_playing [options]

  Options:
    -h, --help:   Show the usage and exit
    -n, --limit:  Limit the length of the output string"
  exit 2
}

parsed_args=$(getopt -a -n get_mpris_media_playing -o hn: -l help,limit: -- "$@")
getopt_valid_args=$?
if [ $getopt_valid_args -ne 0 ]; then
  echo "Error: check input" >&2
  exit 1
fi

eval set -- "$parsed_args"
unset parsed_args
unset getopt_valid_args

while true; do
  case "$1" in
    '-h'|'--help')
      usage
      ;;
    '-n'|'--limit')
      LIMIT=$2
      shift 2
      continue
      ;;
    '--')
      shift
      break
      ;;
    *)
      echo "Unknown error" >&2
      exit 1
      ;;
  esac
done

# assuming mapfile
mapfile -t players < <( playerctl -l ) || exit 1
mapfile -t statuses < <( playerctl -a status ) || exit 1

# players that are currently "Playing" take priority
for index in "${!statuses[@]}"; do
  if [[ "${statuses[$index]}" == "Playing" ]]; then
    player="${players[$index]}"
    metadata=$(get_metadata "$player")
    prefix=""
    quiet_text="Media playing"
    break
  fi
done

# if nothing is playing, then take the first player that is paused
if [[ ! "$metadata" ]]; then
  if [ "${statuses[0]}" == "Paused" ]; then
    player="${players[0]}"
    metadata=$(get_metadata "$player")
    prefix="(Paused) "
    quiet_text="Media paused"
  fi
fi

if (( "$quiet_mode" )); then
  display="$quiet_text"
else
  display="${prefix}${metadata}"
fi

# handle limit argument
if [[ $LIMIT -lt 0 ]]; then
  echo "${prefix}${metadata}"
elif [[ $LIMIT -lt ${#display} ]]; then
  actual_limit=$(( $LIMIT - 1 ))
  echo "${display:0:$actual_limit}…"
else
  echo $display
fi
