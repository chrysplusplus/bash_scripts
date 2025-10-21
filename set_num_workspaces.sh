#!/usr/bin/env bash

# taken from dconf schema
MINIMUM=2   # this is my preference
MAXIMUM=36
GSETTINGS_SCHEMA=org.cinnamon.desktop.wm.preferences
GSETTINGS_KEY=num-workspaces

# prog args
INPUT=$1

# pattern checking
RE_PATTERN='^[+-]?[0-9]+$'
if ! [[ "$INPUT" =~ $RE_PATTERN ]]; then
  echo "error: not a number" >&2; exit 1
fi

CURRENT_NUM=$(gsettings get $GSETTINGS_SCHEMA $GSETTINGS_KEY)

# check for -/+
case $INPUT in
  -*)
    NEW_NUM=$(( CURRENT_NUM + INPUT ))
    ;;
  +*)
    NEW_NUM=$(( CURRENT_NUM + INPUT ))
    ;;
  *)
    NEW_NUM=$INPUT
    ;;
esac

# bounds checking
if [[ $NEW_NUM -lt $MINIMUM ]]; then
  echo "error: cannot be less than $MINIMUM" >&2; exit 1
elif [[ $NEW_NUM -gt $MAXIMUM ]]; then
  echo "error: cannot be more than $MAXIMUM" >&2; exit 1
fi

gsettings set $GSETTINGS_SCHEMA $GSETTINGS_KEY $NEW_NUM
