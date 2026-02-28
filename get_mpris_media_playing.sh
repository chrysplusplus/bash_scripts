#!/usr/bin/env bash

# quiet mode is when the script only outputs that something is playing or
# paused, not what the media is called, which may be distracting
quiet_mode=0
quiet_flag_file="$HOME/.quiet_media"
if [[ -e "$quiet_flag_file" ]]; then
  quiet_mode=1
fi

# script arguments
limit=-1

get_metadata() {
  echo $(playerctl -p "$1" metadata --format "{{artist}} - {{title}}")
}

usage() {
  echo "Usage: get_mpris_media_playing [options]

  Options:
    -h, --help:   Show the usage and exit
    -n, --limit:  Limit the length of the output string"
}

# parse options
while (( $# > 0 )); do
  case "$1" in
    -h|--help)
      usage
      exit 2
      ;;
    -n|--limit)
      limit=$2
      shift 2
      continue
      ;;
    '--')
      shift
      break
      ;;
    *)
      printf "%s\n" "Unknown option: $1" >2
      usage
      exit 2
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
if [[ $limit -lt 0 ]]; then
  echo "${prefix}${metadata}"
elif [[ $limit -lt ${#display} ]]; then
  actual_limit=$(( $limit - 1 ))
  echo "${display:0:$actual_limit}…"
else
  echo $display
fi
