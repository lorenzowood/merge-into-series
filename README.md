# merge-into-series

A Python utility to merge downloaded TV episodes into organized series directories using TVDB metadata.

## Overview

`merge-into-series` helps you organize downloaded TV show episodes by automatically matching them with episode information from The TV Database (TVDB) and moving/copying them to appropriately structured directories for media servers like Plex.

This is particularly useful for long-running series like BBC's "Storyville" (1997-present) and "Arena" (1975-present) where episodes often don't follow standard sNNeNN naming conventions.

## Features

- **Fuzzy matching**: Intelligently matches filenames to episode titles, even with typos or formatting differences
- **Interactive confirmation**: Review matches before processing with options to manually correct or skip files
- **Flexible operations**: Choose between moving or copying files to preserve originals
- **Season organization**: Automatically creates season directories (e.g., "Season 01", "Season 2024")
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
# Series Name, Target Path, TVDB URL
# This assumes your TV shows are organized in /Media/TV/
# Adjust the paths below to match your setup.
Storyville, /Media/TV/Storyville (1997) {tvdb-82300}, https://thetvdb.com/series/storyville/allseasons/official
Arena, /Media/TV/Arena (1975) {tvdb-80379}, https://thetvdb.com/series/arena/allseasons/official
```

### Create Example Configuration
```bash
merge-into-series --create-config
```

## Usage

### Basic Usage
```bash
merge-into-series <series_name> <source_pattern>
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

**Dry run to see what would happen:**
```bash
merge-into-series --dry-run storyville Storyville
```

### Command Options

- `--config, -c`: Path to configuration file (default: `~/.merge-into-series.conf`)
- `--dry-run, -n`: Show what would be done without actually doing it
- `--threshold, -t`: Fuzzy matching threshold 0-100 (default: 80)
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
Choice: 2
...

Ready to process:
Storyville - Praying for Armageddon ((dashfhd)).mkv -> S2024E06 Praying For Armageddon
Storyville - The Contestant ((dashfhd)).mkv -> S2025E11 The Contestant
...

Process to target /Media/TV/Storyville (1997) {tvdb-82300} by
1. Moving
2. Copying
Choice: 1

Moving Storyville - Praying for Armageddon ((dashfhd)).mkv -> S2024E06 Praying For Armageddon
...
All operations completed successfully!
```

## How It Works

1. **Configuration Loading**: Reads series configuration from `~/.merge-into-series.conf`
2. **Episode Data Fetching**: Scrapes episode information from the configured TVDB URL
3. **File Discovery**: Finds all video files (`.mp4`, `.mkv`, `.avi`, etc.) matching the source pattern
4. **Fuzzy Matching**: Uses intelligent text matching to pair filenames with episode titles
5. **Interactive Review**: Presents matches for user confirmation and allows manual corrections
6. **File Operations**: Moves or copies files to organized season directories with proper naming

## Supported File Formats

Video files with extensions: `.mp4`, `.mkv`, `.avi`, `.mov`, `.mpg`, `.mpeg`, `.m4v`, `.wmv`

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
│   └── S2022E19 The Fire Within.mkv
├── Season 2024/
│   └── S2024E06 Praying for Armageddon.mkv
└── Season 2025/
    ├── S2025E01 Your Fat Friend.mkv
    ├── S2025E09 The Jackal Speaks.mkv
    ├── S2025E10 Wedding Night.mkv
    └── S2025E11 The Contestant.mkv
```

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

### v0.1.0
- Initial release
- TVDB scraping and episode matching
- Interactive file processing
- Move/copy operations
- Configuration file support
- Comprehensive test suite