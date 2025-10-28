#!/usr/bin/env python3

from argparse import ArgumentParser
from dataclasses import dataclass
from mutagen.easyid3 import EasyID3
from pathlib import Path

import random

@dataclass
class AlbumMetadata:
    artist: str
    album: str
    tracklist: list[str]

MAX_NUMBER_OF_MISSES = 2

@dataclass
class Match:
    start: int
    length: int
    misses: tuple[int,...] = tuple()

    def __eq__(self, other):
        return self.start == other.start and self.length == other.length

USER_DEF_MATCH = Match(-1, -1)
NO_MATCH = Match(0, 0)

@dataclass
class PathTitleMatch:
    path: Path
    match: Match
    title: str = ""

    def __bool__(self):
        '''Object is True if title is given, else False'''
        return len(self.title) != 0

class MetadataUseParentDirectoryType:
    pass

class MetadataRemoveTagType:
    pass

@dataclass
class MetadataOpt:
    value: str | MetadataUseParentDirectoryType | MetadataRemoveTagType | None

    def __str__(self) -> str:
        if self.value is None:
            return "<not set>"
        elif isinstance(self.value, MetadataUseParentDirectoryType):
            return "<name of parent directory>"
        elif isinstance(self.value, MetadataRemoveTagType):
            return "<remove tag>"
        else:
            return self.value

    def __bool__(self) -> bool:
        return self.value is not None

USE_PARENT_DIRECTORY = MetadataOpt(MetadataUseParentDirectoryType())
REMOVE_TAG = MetadataOpt(MetadataRemoveTagType())

class AlbumMetadataError(Exception):
    pass

class UserQuit(Exception):
    pass

class UserCancel(Exception):
    pass

class UserDone(Exception):
    pass

# tags that are currently implemented through options
SUPPORTED_TAGS = (
        'artist',
        'albumartist',
        'album',
        # future plans
        #'year',
        )

TAG_PRINTABLE_NAMES = {
        'artist': 'Artist',
        'albumartist': 'Album Artist',
        'album': 'Album',
        }

def removeBOM(line: str) -> str:
    ''' Remove BOM at beginning of file'''
    lineBytes = [ord(c) for c in line[:5]]
    if lineBytes[0] == 0xfeff:
        return line[1:]
    return line

def readMetadataFile(path: Path) -> dict[str,list[str]]:
    '''Read metadata into table entries'''
    data = {'': []}
    currentHeader = ''

    def processLine(line: str) -> tuple[str,str|None]:
        entry = line.rstrip()
        header = entry[1:-1] if entry.startswith('[') and entry.endswith(']') else None
        return entry,header

    with open(path, 'r', encoding = "utf-8") as file:
        for idx,line in enumerate(file.readlines()):
            line = removeBOM(line) if idx == 0 else line
            entry,header = processLine(line)
            if len(entry) == 0:
                continue

            if header is not None and header in data.keys():
                currentHeader = header
                continue

            if header is not None:
                currentHeader = header
                data[header] = []
                continue

            else:
                data[currentHeader].append(entry)

    return data

def resolveParentDirectory(path: Path) -> str:
    '''Determine parent directory name from path parts'''
    # parts: ... 'grandparent/', 'parent/', 'file.mp3'
    parts = path.absolute().parts
    assert len(parts) >= 2
    return parts[-2]

def resolveMetadataOptWithParent(opt: MetadataOpt, parent: str) -> str:
    '''Resolve option to its string value'''
    assert isinstance(opt.value, str) or isinstance(opt.value, MetadataUseParentDirectoryType)
    return parent if isinstance(opt.value, MetadataUseParentDirectoryType) else opt.value

def resolveOptionsWithParent(options: dict[str, MetadataOpt], parent: str) -> str:
    '''Resolve dictionary of options to their string values'''
    return {tag:resolveMetadataOptWithParent(value, parent) for tag,value in options.items()}

def extractTagsToChange(options: dict[str, MetadataOpt]) -> dict[str, MetadataOpt]:
    '''Extract tags that specify values to change'''
    doesSpecifyValue = lambda opt: isinstance(opt.value, str) or \
            isinstance(opt.value, MetadataUseParentDirectoryType)
    return { tag: value for tag,value in options.items() if doesSpecifyValue(value) }

def extractTagsToRemove(options: dict[str, MetadataOpt]) -> list[str]:
    '''Extract tags to remove from options'''
    return [tag for tag in options.keys() if isinstance(options[tag].value, MetadataRemoveTagType)]

ARTIST_HEADER = 'artist'
ALBUM_HEADER = 'album'
TRACKLIST_HEADER = 'tracklist'

def parseAlbumDataTable(data: dict[str,list[str]]) -> AlbumMetadata:
    '''Construct AlbumMetadata from data table'''
    headerExists = lambda header: len(data.get(header, list())) > 0
    if not headerExists(ARTIST_HEADER):
        raise AlbumMetadataError(f"No {ARTIST_HEADER}")
    if not headerExists(ALBUM_HEADER):
        raise AlbumMetadataError(f"No {ALBUM_HEADER}")
    if not headerExists(TRACKLIST_HEADER):
        raise AlbumMetadataError(f"No {TRACKLIST_HEADER}")

    return AlbumMetadata(
            data[ARTIST_HEADER][0],
            data[ALBUM_HEADER][0],
            data[TRACKLIST_HEADER])

SKIPPABLE_CHARS = '()[]{}-_'

def isSkippableChar(ch: str) -> bool:
    '''Is character considered skippable'''
    return ch.isspace() or ch in SKIPPABLE_CHARS

def lowercaseSkippedString(string: str) -> str:
    '''Convert string to lowercase and skipped skippabled characters'''
    unskippable = lambda ch: not isSkippableChar(ch)
    return ''.join(filter(unskippable, string.lower()))

def makeSkippedStringMap(string: str) -> list[int]:
    '''Make a map for converting skipped string indices to original string indices'''
    return [idx for idx,ch in enumerate(string) if not isSkippableChar(ch)]

def findMismatchedCharIndices(a: str, b: str) -> list[int]:
    '''Find list of indices of mismatched characters in two equal-length strings'''
    assert len(a) == len(b)
    return [index for index,ch in enumerate(a) if ch != b[index]]

def matchStrings(string: str, pattern: str) -> Match:
    '''Yield longest match between string and pattern'''
    assert len(string) > 0
    assert len(pattern) > 0

    if len(pattern) > len(string):
        return NO_MATCH

    # using pattern as sliding window
    for offset in range(len(string) - len(pattern) + 1):
        windowedString = string[offset:offset + len(pattern)]
        mismatchedCharIdxs = findMismatchedCharIndices(windowedString, pattern)
        if len(mismatchedCharIdxs) <= MAX_NUMBER_OF_MISSES:
            correctedIdxs = tuple(idx + offset for idx in mismatchedCharIdxs)
            return Match(offset,len(pattern),correctedIdxs)

    return NO_MATCH

def identifyTrackFromFilePath(path: Path, tracklist: list[str]) -> tuple[str|None,Match]:
    '''Identify which track in the tracklist corresponds with the file'''
    bestTitleGuess: str|None = None
    bestMatch = NO_MATCH
    file = lowercaseSkippedString(path.stem)
    for title in tracklist:
        skippedTitle = lowercaseSkippedString(title)
        match = matchStrings(file, skippedTitle)
        if match == NO_MATCH:
            continue

        if match.length > bestMatch.length and len(match.misses) <= len(bestMatch.misses):
            bestTitleGuess = title
            bestMatch = match
            continue

        if len(match.misses) < len(bestMatch.misses):
            bestTitleGuess = title
            bestMatch = match
            continue

        if bestMatch == NO_MATCH:
            bestTitleGuess = title
            bestMatch = match
            continue

    return bestTitleGuess,bestMatch

def formatPartiallyMatchedString(string: str, match: Match, START: str, SKIP: str, END: str) -> str:
    '''Format partially matched string with highlight codes'''
    indexMap = makeSkippedStringMap(string)
    start = indexMap[match.start]
    end = indexMap[match.start + match.length - 1] + 1
    skips = [indexMap[idx] for idx in match.misses]

    # add format tokens in reverse order to preserve indices
    tokens = list(string)
    tokens.insert(end, END)
    for skip in reversed(skips):
        tokens.insert(skip + 1, START)
        tokens.insert(skip, SKIP)

    tokens.insert(start, START)
    return ''.join(tokens)

ESCAPE = "\x1b"
FG_DEFAULT = ESCAPE + "[39m"
FG_GREEN = ESCAPE + "[32m"
FG_RED = ESCAPE + "[31m"
FG_YELLOW = ESCAPE + "[33m"
FG_BLUE = ESCAPE + "[34m"
FG_MAGENTA = ESCAPE + "[35m"
FG_CYAN = ESCAPE + "[36m"

def displayPathTitleMatch(pathMatch: PathTitleMatch) -> None:
    '''Display path and matching title'''
    if pathMatch.match == USER_DEF_MATCH:
        START = FG_CYAN
        END = FG_DEFAULT
        print(f"{START}{pathMatch.path.name} -> {pathMatch.title}{END}")
        return

    if pathMatch:
        START = FG_CYAN
        SKIP = FG_RED
        END = FG_DEFAULT
        filename = formatPartiallyMatchedString(
                pathMatch.path.name, pathMatch.match, START = START, SKIP = SKIP, END = END)
        print(f"{filename} -> {START}{pathMatch.title}{END}")
        return

    START = FG_YELLOW
    END = FG_DEFAULT
    print(f"{START}'{pathMatch.path.name}' will remain unchanged{END}")
    return

def displayMatchSummary(pathTitleMatches: list[PathTitleMatch]) -> None:
    '''Display summary of which paths were matched to which titles'''
    for idx,change in enumerate(pathTitleMatches):
        print(f"{idx + 1} - ", end = '')
        displayPathTitleMatch(change)

def displayChangesToBe(options: dict[str,MetadataOpt]) -> None:
    '''Display changes to be made to the discovered files'''
    print("Using the following tag values:")
    for tag in SUPPORTED_TAGS:
        if options[tag]:
            print(f"  {TAG_PRINTABLE_NAMES[tag]}: {options[tag]}")
    print()

# signals
QUIT = 'q'
CANCEL = 's'
DONE = 'd'

QUIT_CANCEL = QUIT + CANCEL
QUIT_DONE = QUIT + DONE

QUIT_PROMPT_HINT = "'q' quits"
CANCEL_PROMPT_HINT = "return cancels"
DONE_PROMPT_HINT = "return finishes"

def addSignalHintsToPrompt(prompt: str, signal: str) -> str:
    '''Format prompt with signal hints'''
    hints = []
    if CANCEL in signal:
        hints.append(CANCEL_PROMPT_HINT)
    if DONE in signal:
        hints.append(DONE_PROMPT_HINT)
    if QUIT in signal:
        hints.append(QUIT_PROMPT_HINT)

    if len(hints) == 0:
        return prompt.format(hints = "")
    else:
        return prompt + f" ({', '.join(hints)}) "

def addPromptPadding(prompt: str) -> str:
    '''Add padding to the end of a prompt string'''
    return prompt + ' ' if prompt[-1] != ' ' else prompt

def promptBoundedInteger(prompt: str, bounds: tuple[int,int], signal: str) -> int:
    '''Prompt user for bounded integer input or quit'''
    lower,upper = bounds
    choice: int|None = None
    prompt = addSignalHintsToPrompt(prompt, signal)
    prompt = addPromptPadding(prompt)
    while choice is None:
        print(prompt, end = '')
        response = input()
        if response == '' and CANCEL in signal:
            raise UserCancel

        if response == '' and DONE in signal:
            raise UserDone

        if response.lower() == 'q' and QUIT in signal:
            raise UserQuit

        try:
            choice = int(response)
            if choice < lower or choice > upper:
                print("Selection is outside the available range")
                choice = None

        except ValueError:
            continue

    return choice

PROMPT_SELECT_NEW_TRACK = "Select the new track number:"
PROMPT_SELECT_TRACK_CHANGE = "Enter number of any selection you want to change:"

def promptTrackSelect(tracklist: list[str]) -> str|None:
    '''Prompt user to select track from tracklist'''
    print("0 - <skip this file>")
    for idx,track in enumerate(tracklist):
        print(f"{idx + 1} - {track}")

    print()
    choice = promptBoundedInteger(PROMPT_SELECT_NEW_TRACK, bounds = (0,len(tracklist)), signal = QUIT_CANCEL)
    if choice == 0:
        return None
    else:
        return tracklist[choice - 1]

def promptChanges(pathTitleMatches: list[PathTitleMatch], tracklist: list[str]) -> list[PathTitleMatch]:
    '''Prompt user for additional changes'''
    while True:
        try:
            displayMatchSummary(pathTitleMatches)
            print()
            choice = promptBoundedInteger(PROMPT_SELECT_TRACK_CHANGE, bounds=(1,len(pathTitleMatches)), signal = QUIT_DONE)

            ptm = pathTitleMatches[choice - 1]
            displayPathTitleMatch(ptm)

            newTitle = promptTrackSelect(tracklist)
            ptm.title = newTitle if newTitle is not None else ''
            ptm.match = USER_DEF_MATCH
            displayPathTitleMatch(ptm)
            print()

        except UserCancel:
            print("Cancelled new track selection")
            continue

        except UserDone:
            return pathTitleMatches

def findTracknumber(title: str, album: AlbumMetadata) -> str:
    '''Determine tracknumber from title'''
    assert title in album.tracklist
    return str(album.tracklist.index(title) + 1)

def resolveTrackMetadataFromMatch(
        match: PathTitleMatch, album: AlbumMetadata) -> dict[str,str]:
    '''Determine track metadata tag value from a definite title match'''
    assert match
    return {
            'title': match.title,
            'tracknumber': findTracknumber(match.title, album),
            }

def resolveAlbumMetadata(
        album: AlbumMetadata, options: dict[str, MetadataOpt]) -> dict[str, MetadataOpt]:
    '''Determine options for album tags'''
    retval = {tag: value for tag,value in options.items()}
    if not retval['artist']:
        retval['artist'] = MetadataOpt(album.artist)
    if not retval['albumartist']:
        retval['albumartist'] = MetadataOpt(album.artist)
    if not retval['album']:
        retval['album'] = MetadataOpt(album.album)
    return retval

def writeMetadata(
        path: Path, metadata: dict[str,str], tagsToRemove: list[str]) -> bool:
    '''Write metadata to file if different from specified values

    Return True if file was changed, otherwise False'''
    audio = EasyID3(path)
    doWrite = False
    for tag, tagValue in metadata.items():
        # tag values stored in indexed list in file
        currentTagValue = audio[tag][0] if tag in audio else None
        if tagValue == currentTagValue:
            continue

        audio[tag] = tagValue
        doWrite = True

    for tag in tagsToRemove:
        if tag not in audio:
            continue

        del audio[tag]
        doWrite = True

    if doWrite:
        audio.save()

    return doWrite

def readMetadata(path: Path) -> dict[str,str|None]:
    '''Read track metadata into dictionary, missing keys are None'''
    tags = ('title', 'tracknumber', *SUPPORTED_TAGS)
    audio = EasyID3(path)
    return {tag: audio[tag][0] if tag in audio else None for tag in tags}

def getPrintableTags(path: Path) -> dict[str,str]:
    '''Return a dictionary of printable metadata tags + path and fullpath'''
    metadata = readMetadata(path)
    stringCorrectedMetadata = {
            tag: value if value is not None else ''
            for tag,value in metadata.items()}

    extras = {
            'path': str(path),
            'fullpath': str(path.absolute()),
            }

    return { **stringCorrectedMetadata, **extras }

def thankyou() -> str:
    '''Say thank you'''
    THANKS = ["See you next time!",
              "Hellothankyouforwatching! Hellothankyouforwatching!",
              "Good-bye!",
              "Thanks for using my script!",
              "Until next time!",
              "See you soon!",
              ]

    return random.choice(THANKS)

DEFAULT_FORMAT_STRING = "{fullpath}:\n" \
        "\tTitle:        {title}\n" \
        "\tTrack Nr:     {tracknumber}\n" \
        "\tArtist:       {artist}\n" \
        "\tAlbum Artist: {albumartist}\n" \
        "\tAlbum:        {album}\n"

def printDirectoryMetadata(directory: Path, globPattern: str, formatString: str):
    '''Print metadata for .mp3 files in a directory'''
    audioPaths = sorted(directory.glob(globPattern))
    for path in audioPaths:
        print(formatString.format(**getPrintableTags(path)))

def applyMetadataFromAlbumFileInteractively(
        albumDataPath: Path,
        directory: Path,
        globPattern: str,
        options: dict[str, MetadataOpt]):
    '''Read metadata and tracklist from file and apply to files in directory
    interactively'''
    album: AlbumMetadata
    try:
        data = readMetadataFile(albumDataPath)
        album = parseAlbumDataTable(data)
        print(f"Read album metadata from {albumDataPath}")

    except AlbumMetadataError as err:
        print(f"Error: {err!s}")
        print("Fix error and run script again")
        return

    albumMetadataOptions = resolveAlbumMetadata(album, options)
    displayChangesToBe(albumMetadataOptions)
    tagsToRemove = extractTagsToRemove(albumMetadataOptions)
    tagsToChange = extractTagsToChange(albumMetadataOptions)

    audioPaths = directory.glob(globPattern)

    pathTitleMatches: list[PathTitleMatch] = []
    for path in audioPaths:
        title,match = identifyTrackFromFilePath(path, album.tracklist)
        pathTitleMatches.append(
                PathTitleMatch(path, match, title)
                if title is not None
                else PathTitleMatch(path, NO_MATCH))

    try:
        promptChanges(pathTitleMatches, album.tracklist)

    except UserQuit:
        print("Quitting...")
        print("No changes were made to the files.")
        return

    counter = 0
    for ptm in pathTitleMatches:
        if not ptm:
            continue

        parent = resolveParentDirectory(ptm.path)
        metadata = {
                **resolveTrackMetadataFromMatch(ptm, album),
                **resolveOptionsWithParent(tagsToChange, parent) }

        isFileChanged = writeMetadata(ptm.path, metadata, tagsToRemove)
        if isFileChanged:
            counter = counter + 1

    if counter == 0:
        print("No changes were made to the files")
    elif counter == 1:
        print("1 file was changed")
    else:
        print(f"{counter} files were changed")

    print(thankyou())

def applyMetadataToDirectory(
        directory: Path,
        globPattern: str,
        options: dict[str,MetadataOpt]):
    '''Apply metadata to .mp3 files in a directory'''
    if not any(options.values()):
        print("Nothing to do")
        return

    displayChangesToBe(options)
    tagsToRemove = extractTagsToRemove(options)
    tagsToChange = extractTagsToChange(options)

    counter = 0
    audioPaths = sorted(directory.glob(globPattern))
    for path in audioPaths:
        parent = resolveParentDirectory(path)
        metadata = {
                tag: resolveMetadataOptWithParent(value, parent)
                for tag,value in tagsToChange.items()}

        isFileChanged = writeMetadata(path, metadata, tagsToRemove)
        if isFileChanged:
            counter = counter + 1

    if counter == 0:
        print("No files were changed")
    elif counter == 1:
        print("1 file was changed")
    else:
        print(f"{counter} files were changed")

    print(thankyou())

PROG_NAME = "Album Metadatiser"
PROG_DESC = "Apply metadata to multiple .mp3 files from a single source."

PROG_INPUT_DESC = "input data file or input directory"
PROG_DIRECTORY_DESC = "directory to search when applying data file"
PROG_PRINT = "print the current metadata of .mp3 files in a directory"
PROG_RECURSE = "recurse through subdirectories"
PROG_FORMAT_STRING_DESC = "format string for print output"

PROG_ALBUM_DESC = "name of the album"
PROG_ALBUM_PARENT_DESC = "use name of parent directory as album title"
PROG_REMOVE_ALBUM_DESC = "remove album tag"

PROG_ALBUM_ARTIST_DESC = "name of the album artist"
PROG_ALBUM_ARTIST_PARENT_DESC = "use name of parent directory as album artist"
PROG_REMOVE_ALBUM_ARTIST_DESC = "remove album artist tag"

PROG_ARTIST_DESC = "name of the artist"
PROG_ARTIST_PARENT_DESC = "use name of parent directory as artist"
PROG_REMOVE_ARTIST_DESC = "remove artist tag"

def main():
    # Program Arguments
    argParser = ArgumentParser(prog = "Album Metadatiser", description = PROG_DESC)
    argParser.add_argument("input", type = Path, help = PROG_INPUT_DESC)
    argParser.add_argument("-d", "--directory",
                           type = Path,
                           default = Path("."),
                           help = PROG_DIRECTORY_DESC)
    argParser.add_argument("-f", "--format-string",
                           default = DEFAULT_FORMAT_STRING,
                           help = PROG_FORMAT_STRING_DESC)
    argParser.add_argument("-p", "--print", action = 'store_true', help = PROG_PRINT)
    argParser.add_argument("-r", "--recurse", action = 'store_true', help = PROG_RECURSE)

    grp_album = argParser.add_mutually_exclusive_group()
    grp_album.add_argument("--album", help = PROG_ALBUM_DESC)
    grp_album.add_argument("--album-from-parent",
                           action = 'store_true',
                           help = PROG_ALBUM_PARENT_DESC)
    grp_album.add_argument("--remove-album",
                           action = 'store_true',
                           help = PROG_REMOVE_ALBUM_DESC)

    grp_album_artist = argParser.add_mutually_exclusive_group()
    grp_album_artist.add_argument("--album-artist", help = PROG_ALBUM_ARTIST_DESC)
    grp_album_artist.add_argument("--album-artist-from-parent",
                                  action = 'store_true',
                                  help = PROG_ALBUM_ARTIST_PARENT_DESC)
    grp_album_artist.add_argument("--remove-album-artist",
                                  action = 'store_true',
                                  help = PROG_REMOVE_ALBUM_ARTIST_DESC)

    grp_artist = argParser.add_mutually_exclusive_group()
    grp_artist.add_argument("--artist", help = PROG_ARTIST_DESC)
    grp_artist.add_argument("--artist-from-parent",
                            action = 'store_true',
                            help = PROG_ARTIST_PARENT_DESC)
    grp_artist.add_argument("--remove-artist",
                            action = 'store_true',
                            help = PROG_REMOVE_ARTIST_DESC)

    # Determine which mode to run in
    args = argParser.parse_args()

    globPattern = "**/*.mp3" if args.recurse else "*.mp3"

    pickOptValue = lambda value, doUseParent, doRemoveTag: \
            USE_PARENT_DIRECTORY if doUseParent else \
            REMOVE_TAG if doRemoveTag else \
            MetadataOpt(value)

    options = {
            "album":       pickOptValue(args.album, args.album_from_parent, args.remove_album),
            "albumartist": pickOptValue(args.album_artist, args.album_artist_from_parent, args.remove_album_artist),
            "artist":      pickOptValue(args.artist, args.artist_from_parent, args.remove_artist),
            }

    if args.print:
        printDirectoryMetadata(args.input, globPattern, args.format_string)

    elif args.input.is_dir():
        applyMetadataToDirectory(args.input, globPattern, options)

    else:
        applyMetadataFromAlbumFileInteractively(args.input, args.directory, globPattern, options)

if __name__ == "__main__":
    main()

