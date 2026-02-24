#!/usr/bin/env bash

if (( $# > 0 )); then
  pw=$1
else
  IFS= read -r -s -p 'Enter Nextcloud password: ' pw
  echo
fi

nextcloudcmd -u "bagwellchristopher@hotmail.co.uk" -p "$pw" ~/nextcloud2/ "https://use08.thegood.cloud"
