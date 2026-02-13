#!/usr/bin/env bash

# Exit Code
# 0 - OK
# 1 - File does not exist
# 2 - Usage error
# 3 - Could not create temp directory
# 4 - Rendering error

show_help() {
  printf "%s\n" "\
${0##*/} [-h|--help] [-l|--toc-links] [--no-toc] [--pdf pdf_file] file

Options:
    -h, --help      Display this message
    -l, --toc-links Render anchor links to toc after each header
    -r, --refresh   Render file but don't open; useful for updating the preview page without opening it in a new tab
    --no-toc        Omit the table of contents; errors if --toc-links is specified
    --pdf pdf_file  Render markdown to PDF instead of HTML
"
}

usage() {
  printf "%s\n" "Usage: $0 [options] file" >&2
}

toc_links=0
do_open=1
do_strip_toc=0
pdf_path=""
do_test=0

# parse options
while (( $# > 0 )); do
  case "$1" in
    -h|--help)
      show_help
      exit
      ;;
    -l|--toc-links)
      toc_links=1
      shift
      ;;
    -r|--refresh)
      do_open=0
      shift
      ;;
    --no-toc)
      do_strip_toc=1
      shift
      ;;
    --pdf)
      case "$2" in
        -*)
          printf -- "--pdf requires a filename\n" >&2
          usage
          exit 2
          ;;
        *)
          pdf_path="$2"
          shift 2
          ;;
      esac
      ;;
    --)
      shift
      break
      ;;
    -*)
      printf "%s\n" "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if (( $do_strip_toc && $toc_links )); then
  printf "The options --toc-link and --no-toc are incompatible\n" >&2
  usage
  exit 2
fi

file="$1"

if [[ -z "$file" ]]; then
  printf "No input file was specified\n"
  usage
  exit 2
fi

filepath=$(realpath "$file")

if [[ ! -e "$filepath" ]]; then
  printf "%s\n" "File does not exist: $filepath" >&2
  exit 1
fi

tmp_dir="${TMP_DIR:-/tmp/html/}"

if [[ ! -e "$tmp_dir" ]]; then
  mkdir "$tmp_dir"
  if [[ ! $? ]]; then
    printf "%s\n" "Could not create directory: $tmp_dir" >&2
    exit 3
  fi
fi

if [[ ! -d "$tmp_dir" ]]; then
  printf "%s\n" "Expected directory: $tmp_dir" >&2
  exit 1
fi

tmp_name="${filepath#/}"
tmp_name="${tmp_name%.md}"
tmp_name="${tmp_name////_}"
tmp_path="$tmp_dir$tmp_name.html"

title="${filepath##/}"
title="${title%.md}"

if (( $do_strip_toc )); then
  old_filepath="$filepath"
  filepath="$tmp_dir$tmp_name.strip_toc.md"
  awk 'BEGIN {flag=1} /^#/{flag=1} /^# Contents/{flag=0} flag' "$old_filepath" > "$filepath"
fi

if (( $toc_links )) && grep -q -E '^# Contents' "$filepath"; then
  old_filepath="$filepath"
  filepath="$tmp_dir$tmp_name.toc_links.md"
  sed '/^#/a \
    \
    [top](#contents)' "$old_filepath" > "$filepath"
fi

if [[ -n "$pdf_path" ]]; then
  grep -v -E '^:' "$filepath" | pandoc -o "$pdf_path"
  tmp_path="$pdf_path"
else
  grep -v -E '^:' "$filepath" | pandoc -o "$tmp_path" --variable=pagetitle:"$title"
fi

if [[ ! -e "$tmp_path" ]]; then
  printf "There was an error rendering the file\n" >& 2
  exit 4
fi

if (( $do_open )); then
  open "$tmp_path" &
fi

if [[ -e "$tmp_dir$tmp_name.strip_toc.md" ]]; then
  rm "$tmp_dir$tmp_name.strip_toc.md"
fi

if [[ -e "$tmp_dir$tmp_name.toc_links.md" ]]; then
  rm "$tmp_dir$tmp_name.toc_links.md"
fi
