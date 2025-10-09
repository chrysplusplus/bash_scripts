#! /bin/bash

xclip -o -selection clipboard -t text/html | pandoc -f html -t markdown_strict --column=80 | xclip -selection clipboard
