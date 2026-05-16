# merge-into-series

A Python utility to merge downloaded TV episodes into organized series directories using TVDB metadata.

## Overview

`merge-into-series` helps you organize downloaded TV show episodes by automatically matching them with episode information from The TV Database (TVDB) and moving/copying them to appropriately structured directories for media servers like Plex.

This is particularly useful for long-running series like BBC's "Storyville" (1997-present) and "Arena" (1975-present) where episodes often don't follow standard sNNeNN naming conventions.

## Features

- **Fuzzy matching**: Intelligently matches filenames to episode titles, even with typos or formatting differences
- **Episode code detection**: Recognises `S01E01`, `01x01`, `02x03`, `1of6`, `ep1`, `part1` patterns and maps them directly to TVDB metadata
- **Companion file handling**: Subtitle and other sidecar files (`.srt`, `.sub`, `.idx`, …) are grouped with their video file and moved/copied together — no repeated matching questions per episode
- **Interactive confirmation**: Review matches before processing with options to manually correct or skip files
- **Flexible operations**: Choose between moving or copying files to preserve originals
- **Season organization**: Automatically creates season directories (e.g., "Season 01", "Season 2024")
- **Plex metadata**: Generates `.nfo` sidecar files so Plex displays episode titles, summaries, and air dates
- **Safe processing**: Dry-run mode and confirmation prompts prevent accidental operations
- **Configuration-based**: Simple text file configuration for series definitions

## Installation

### Recommended: Using pipx
```bash
# Install pipx if you don't have it
pip install --user pipx
pipx ensurepath

# Install merge-into-series
pipx install merge-into-series
```

### From PyPI
```bash
pip install merge-into-series
```

### From Source
```bash
git clone https://github.com/lorenzowood/merge-into-series.git
cd merge-into-series
pipx install .
```

**Why pipx?** It installs the tool in an isolated environment while making it globally available. This prevents conflicts with your system Python packages and is the recommended way to install CLI tools.

## Configuration

Create a configuration file at `~/.merge-into-series.conf` with the following format:

```
# Optional: set a shared root directory. Series paths that don't start with /
# are treated as subdirectories of ROOT.
ROOT: /Media/TV

# Series Name, Directory (relative to ROOT or absolute), TVDB URL
Storyville, Storyville (1997) {tvdb-82300}, https://thetvdb.com/series/storyville/allseasons/official
Arena, Arena (1975) {tvdb-80379}, https://thetvdb.com/series/arena/allseasons/official

# Absolute paths override ROOT:
Other_Show, /Different/Location/Other Show, https://thetvdb.com/series/other-show/allseasons/official
```

### Create Example Configuration
```bash
merge-into-series --create-config
```

### Add a Series
```bash
merge-into-series --add For_All_Mankind "For All Mankind (2019) {tvdb-356202}" "https://www.thetvdb.com/series/for-all-mankind/allseasons/official"
```

Adding a name that already exists (case-insensitive) prints a message and does nothing.

## Usage

### Basic Usage
```bash
merge-into-series <series_name> <source_pattern> [source_pattern ...]
```

### Examples

**Process files in a directory:**
```bash
cd "/Volumes/TV shows/Downloads"
merge-into-series storyville Storyville
```

**Process specific files with glob pattern:**
```bash
merge-into-series storyville "/path/to/downloads/Storyville*.mkv"
```

**Process multiple files directly (shell-expands the glob):**
```bash
merge-into-series upstart_crow Upstart_Crow_*
```

**Process a mix of files and directories:**
```bash
merge-into-series storyville /downloads/ep1.mkv /downloads/ep2.mkv /other/downloads/
```

**Dry run to see what would happen:**
```bash
merge-into-series --dry-run storyville Storyville
```

**Use a partial or differently-formatted series name (fuzzy match):**
```bash
merge-into-series mankind Storyville*.mkv
# Did you mean "For_All_Mankind"? [y/N]
```

**Skip all confirmation prompts (accept fuzzy match, pick first episode match, move files):**
```bash
merge-into-series -y mankind Storyville*.mkv
```

**Require an exact series name match, disabling fuzzy lookup:**
```bash
merge-into-series --strict For_All_Mankind Storyville*.mkv
```

**Retroactively generate missing NFO files for an existing library:**
```bash
merge-into-series --update-nfo=missing storyville
```

**Regenerate all NFO files, overwriting existing ones:**
```bash
merge-into-series --update-nfo=all storyville
```

### Command Options

- `--config, -c`: Path to configuration file (default: `~/.merge-into-series.conf`)
- `--dry-run, -n`: Show what would be done without actually doing it
- `--yes, -y`: Auto-confirm all prompts — accept fuzzy series match, pick first episode match, move files without asking
- `--strict`: Disable fuzzy series name matching; require an exact name from the config
- `--threshold, -t`: Fuzzy matching threshold 0-100 (default: 80)
- `--generate-nfo`: Generate `.nfo` metadata sidecar files alongside video files (default: true). Use `--generate-nfo=false` to disable.
- `--update-nfo=missing|all`: Scan the target directory and generate NFO files for already-merged episodes, without touching video files. `missing` adds NFOs only where absent; `all` overwrites existing ones too. Cannot be combined with `SOURCE_PATTERN`.
- `--overwrite, -o`: Overwrite existing files without prompting
- `--add NAME DIR URL`: Add a new series entry to the configuration file and exit
- `--create-config`: Create example configuration file and exit
- `--help`: Show help message

## Interactive Workflow Example

```
$ merge-into-series storyville Storyville
Found 7 files
Storyville - Praying for Armageddon ((dashfhd)).mkv -> S2024E06 Praying For Armageddon
Storyville - The Contestant ((dashfhd)).mkv -> S2025E11 The Contestant
Storyville - The Fire Within ((dashfhd)).mkv -> S2022E19 The Fire Within
Storyville - ERROR ERROR Speaks ((dashfhd)).mkv ->
1. S2005E20 Dr. Geobbels Speaks
2. S2025E09 The Jackal Speaks
3. Manual entry
4. Skip
Choice: 3
Manual entry:
Season (YYYY): 2025
Episode: 9
Title [The Jackal Speaks]:        ← press Enter to accept the TVDB title
...

Ready to process:
Storyville - Praying for Armageddon ((dashfhd)).mkv -> S2024E06 Praying For Armageddon
  + Storyville - Praying for Armageddon ((dashfhd)).idx
  + Storyville - Praying for Armageddon ((dashfhd)).sub
Storyville - The Contestant ((dashfhd)).mkv -> S2025E11 The Contestant
...

Process to target /Media/TV/Storyville (1997) {tvdb-82300} by
1. Moving
2. Copying
Choice: 1

Moving Storyville - Praying for Armageddon ((dashfhd)).mkv -> S2024E06 Praying For Armageddon
Moving Storyville - Praying for Armageddon ((dashfhd)).idx -> S2024E06 Praying For Armageddon
Moving Storyville - Praying for Armageddon ((dashfhd)).sub -> S2024E06 Praying For Armageddon
...
All operations completed successfully!
```

## How It Works

1. **Configuration Loading**: Reads series configuration from `~/.merge-into-series.conf`
2. **Episode Data Fetching**: Scrapes episode information from the configured TVDB URL
3. **File Discovery**: Finds video files matching the source pattern, grouping subtitle/companion files (`.srt`, `.sub`, `.idx`, etc.) with the video that shares their stem
4. **Episode Code Detection**: Checks for `S01E01`, `01x01`/`02x03`, `1of6`, `ep1`, `part1` patterns and resolves them directly against TVDB data (score 100) before fuzzy title matching
5. **Fuzzy Matching**: Uses intelligent text matching to pair filenames with episode titles
6. **Interactive Review**: Presents matches for user confirmation and allows manual corrections; each group of files (video + companions) is shown and matched once
7. **File Operations**: Moves or copies all files in a group to organized season directories with proper naming
8. **NFO Generation**: Writes a `.nfo` metadata sidecar alongside each video file for Plex (not duplicated for companion files)

## Supported File Formats

Video files with extensions: `.mp4`, `.mkv`, `.avi`, `.mov`, `.mpg`, `.mpeg`, `.m4v`, `.wmv`, `.ts`, `.mp2`, `.m2ts`, `.vob`, `.webm`

Any file sharing a stem with a recognised video file is treated as a companion (subtitles, index files, etc.) and moved/copied alongside it automatically.

## File Naming Convention

Files are renamed using the format: `S{YYYY}E{NN} {Episode Title}.{extension}`

Examples:
- `S2024E06 Praying for Armageddon.mkv`
- `S2025E11 The Contestant.mp4`

## Directory Structure

```
Target Directory/
├── Season 2022/
│   ├── S2022E01 Episode Title.mkv
│   ├── S2022E01 Episode Title.nfo
│   ├── S2022E19 The Fire Within.mkv
│   └── S2022E19 The Fire Within.nfo
├── Season 2024/
│   ├── S2024E06 Praying for Armageddon.mkv
│   ├── S2024E06 Praying for Armageddon.nfo
│   ├── S2024E06 Praying for Armageddon.idx  ← companion file
│   └── S2024E06 Praying for Armageddon.sub  ← companion file
└── Season 2025/
    ├── S2025E11 The Contestant.mkv
    └── S2025E11 The Contestant.nfo
```

### NFO Sidecar Files

Each video file is accompanied by a `.nfo` file containing episode metadata in a format Plex understands:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
  <title>Praying for Armageddon</title>
  <plot>A documentary following evangelical Christians...</plot>
  <aired>2024-03-15</aired>
  <season>2024</season>
  <episode>6</episode>
</episodedetails>
```

This is particularly useful for long-running series where Plex cannot identify episodes from the season number alone (e.g. year-based seasons like S1964E04). Use `--generate-nfo=false` to skip NFO generation.

## Error Handling

- **Network Issues**: Gracefully handles TVDB connection problems
- **Missing Files**: Validates source files exist before processing
- **Permission Issues**: Checks target directory permissions
- **Duplicate Files**: Prompts before overwriting existing files
- **Malformed Configuration**: Reports configuration file errors

## Development

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=merge_into_series
```

### Code Style
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/
```

## Requirements

- Python 3.8+
- Internet connection (for TVDB data fetching)
- Dependencies: `requests`, `beautifulsoup4`, `fuzzywuzzy`, `python-levenshtein`, `click`

## Browser Extension

[merge-into-series-tvdb-plugin](https://github.com/lorenzowood/merge-into-series-tvdb-plugin) is a Chromium extension (Chrome / Brave) that adds a one-click `--add` command to every TheTVDB series page. Visit a series, click the generated command to copy it, then paste it in your terminal — no manual typing required.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### v0.1.23
- Fix specials actually not scraped even after v0.1.22: TVDB uses a `<small>` tag (not `<span>`) for the episode label on specials, and prefixes the code with "SPECIAL " (e.g. `SPECIAL 0x11`). The scraper now accepts any element with `class="episode-label"` and uses `re.search` instead of `re.match` for the `NxM` pattern so the prefix is ignored
- Fix `--update-nfo all` summary always showing "0 already present (skipped)": the `all` mode now reports "N new, M overwritten" instead of the misleading skipped count

### v0.1.22
- Fix specials (season 0) not being scraped or matched: TVDB labels them `0x10` rather than `S00E10`, and they may appear in `div.list-group-item` elements rather than `li`. The scraper now accepts both label formats and any element type with the `list-group-item` class

### v0.1.21
- Companion file handling: subtitle and sidecar files (`.srt`, `.sub`, `.idx`, etc.) sharing a stem with a video file are grouped with it and moved/copied together — the matching question is asked only once per group
- Episode code detection now handles `02x03`-style codes (leading zeros on season, case-insensitive `x`, single-digit episode numbers)
- Extended video format support: `.mp2`, `.m2ts`, `.vob`, `.webm` added
- Manual episode entry now shows the TVDB title as a default in square brackets (`Title [Heavy Metal]:`); press Enter to accept, or type to override. Replaces the previous readline-based pre-fill which was unreliable in some terminals
- Conflict detection is now extension-aware, preventing false clashes between video and companion files

### v0.1.20
- Use standard CSV quoting (`csv.reader`/`csv.writer`) so fields containing commas are wrapped in double-quotes; replaces the fragile comma-space heuristic

### v0.1.19
- Fix path parsed incorrectly when series name contains commas: split on `', '` (comma-space) rather than bare comma, since names use underscores and never contain `', '`

### v0.1.18
- Fix config parsing when the series name contains commas: commas are stripped from names on write (names are CLI identifiers), and quoted names (`"Name, with comma"`) are supported in the config for manual edits

### v0.1.17
- Sanitize colons in series directory names (replace with ` -`) to prevent filesystem/Plex display issues on macOS and exFAT volumes

### v0.1.16
- Fix config parsing failing when the directory name contains a comma (e.g. "Maps: Power, Plunder and Possession")

### v0.1.15
- Manual entry pre-fills the title prompt from TVDB metadata when the entered season/episode is known; edit or press Enter to accept

### v0.1.14
- Match files by episode code patterns (s01e01, 1x01, 1of2, ep1, part1) when no title is available; titles are pulled from TVDB metadata

### v0.1.13
- Replace `add` keyword with `--add NAME DIR URL` option (shows in `--help`, no PATH ambiguity)

### v0.1.12
- Fuzzy series name matching: supply a partial or differently-formatted name (`mankind`, `ForAllMankind`, `for-all-mankind`) and get a "Did you mean?" prompt
- `--strict` flag to require an exact series name match
- `-y` / `--yes` flag to auto-confirm all prompts (fuzzy match, episode selection, move)
- `ROOT:` directive in the config file to set a shared parent directory, so series paths can be relative
- `--add` option to append a new series entry from the command line

### v0.1.11
- Accept multiple source patterns (files, directories, or globs) as arguments.
  Shell-expanding globs like `Upstart_Crow_*` now work without quoting.
  Duplicate files from overlapping patterns are silently deduplicated.
- Document `--update-nfo` usage examples in README

### v0.1.9
- Fix `--update-nfo` failing to parse episode codes in filenames that start with a series name prefix (e.g. `Series - S01E01 - Title.mkv`)

### v0.1.8
- Add `--update-nfo=missing/all` to retroactively generate NFO files in an existing library

### v0.1.7
- Generate `.nfo` sidecar files for Plex episode metadata (title, summary, air date)
- Normalise TVDB date format to ISO 8601 in NFO output

### v0.1.0
- Initial release
- TVDB scraping and episode matching
- Interactive file processing
- Move/copy operations
- Configuration file support
- Comprehensive test suite