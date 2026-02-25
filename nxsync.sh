#!/usr/bin/env bash

if [[ -z "$CHS_MACHINE" ]]; then
  printf "This utility is not implemented for your machine\n"
  exit 1
fi

IFS= read -r -s -p 'Enter Nextcloud password: ' pw
echo

nextcloudcmd -u "bagwellchristopher@hotmail.co.uk" -p "$pw" ~/nextcloud2/ "https://use08.thegood.cloud"
