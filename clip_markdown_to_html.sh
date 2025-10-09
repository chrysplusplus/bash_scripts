#!/usr/bin/env bash

xclip -o -selection clipboard | pandoc -f markdown -t html | xclip -selection clipboard -t text/html
