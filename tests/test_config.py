"""Tests for configuration handling."""

import tempfile
from pathlib import Path

import pytest

from merge_into_series.config import Config, _normalize_to_words, _words_match_subsequence


def test_quoted_name_with_comma_parses_correctly(tmp_path):
    """A name field wrapped in double-quotes is parsed correctly even when it contains commas."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        'ROOT: /Media/TV\n'
        '"Maps:_Power,_Plunder_and_Possession",'
        ' Maps - Power, Plunder and Possession (2010) {tvdb-157961},'
        ' https://www.thetvdb.com/series/maps-power-plunder-and-possession/allseasons/official\n'
    )
    config = Config(str(conf))
    s = config.get_series_config('Maps:_Power,_Plunder_and_Possession')
    assert s is not None
    assert s['name'] == 'Maps:_Power,_Plunder_and_Possession'
    assert 'Plunder and Possession' in s['target_path']


def test_legacy_name_with_comma_uses_comma_space_split(tmp_path):
    """Old entries where the name has commas (no quoting) parse correctly because
    names use underscores so the first ', ' is always the name/path delimiter."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        'ROOT: /Media/TV\n'
        'Maps:_Power,_Plunder_and_Possession,'
        ' Maps - Power, Plunder and Possession (2010) {tvdb-157961},'
        ' https://www.thetvdb.com/series/maps-power-plunder-and-possession/allseasons/official\n'
    )
    config = Config(str(conf))
    s = config.get_series_config('Maps:_Power,_Plunder_and_Possession')
    assert s is not None
    assert s['target_path'] == '/Media/TV/Maps - Power, Plunder and Possession (2010) {tvdb-157961}'


def test_add_series_strips_commas_from_name(tmp_path):
    """Commas in the name are stripped so the config line stays valid CSV."""
    conf = tmp_path / "test.conf"
    config = Config(str(conf))
    config.add_series(
        "Maps:_Power,_Plunder_and_Possession",
        "Maps - Power, Plunder and Possession (2010) {tvdb-157961}",
        "https://www.thetvdb.com/series/maps-power-plunder-and-possession/allseasons/official",
    )
    text = conf.read_text()
    first_line = text.strip().split('\n')[0]
    # Name should have comma stripped, path should still be intact
    assert first_line.startswith('Maps:_Power_Plunder_and_Possession,')
    # Re-parsing should find the entry
    config2 = Config(str(conf))
    s = config2.get_series_config('Maps:_Power_Plunder_and_Possession')
    assert s is not None
    assert 'Plunder and Possession' in s['target_path']


def test_colon_in_directory_name_is_sanitized(tmp_path):
    """Colons in the series directory name are replaced with ' -' to avoid Plex/filesystem issues."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        "ROOT: /Media/TV\n"
        "Empire, Empire of the Seas: How the Navy Forged the Modern World (2010) {tvdb-135411},"
        " https://www.thetvdb.com/series/empire/allseasons/official\n"
    )
    config = Config(str(conf))
    s = config.get_series_config('Empire')
    assert s is not None
    assert ':' not in s['target_path']
    assert 'Empire of the Seas - How the Navy Forged the Modern World' in s['target_path']


def test_add_series_sanitizes_colon_in_path(tmp_path):
    """add_series writes the sanitized (colon-free) directory name to the config file."""
    conf = tmp_path / "test.conf"
    config = Config(str(conf))
    config.add_series(
        "Empire",
        "Empire of the Seas: How the Navy Forged the Modern World (2010) {tvdb-135411}",
        "https://www.thetvdb.com/series/empire/allseasons/official",
    )
    text = conf.read_text()
    assert 'Empire of the Seas - How' in text  # colon replaced with ' -' in directory name
    assert 'Empire of the Seas:' not in text   # original colon form absent


def test_comma_in_directory_name(tmp_path):
    """Directory names containing commas (e.g. 'Maps: Power, Plunder...') parse correctly,
    and colons in the name are sanitized to ' -'."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        "ROOT: /Media/TV\n"
        "Maps, Maps: Power, Plunder and Possession (2010) {tvdb-157961},"
        " https://www.thetvdb.com/series/maps-power-plunder-and-possession/allseasons/official\n"
    )
    config = Config(str(conf))
    s = config.get_series_config('Maps')
    assert s is not None
    assert s['target_path'] == '/Media/TV/Maps - Power, Plunder and Possession (2010) {tvdb-157961}'
    assert s['tvdb_url'] == 'https://www.thetvdb.com/series/maps-power-plunder-and-possession/allseasons/official'


def test_root_directive_resolves_relative_paths(tmp_path):
    """ROOT: makes relative series paths absolute."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        "ROOT: /Media/TV\n"
        "Storyville, Storyville (1997) {tvdb-82300}, https://example.com/storyville\n"
    )
    config = Config(str(conf))
    s = config.get_series_config('Storyville')
    assert s is not None
    assert s['target_path'] == '/Media/TV/Storyville (1997) {tvdb-82300}'


def test_root_directive_case_insensitive(tmp_path):
    """root: and ROOT: and Root: all work."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        "root: /Media/TV\n"
        "Arena, Arena (1975), https://example.com/arena\n"
    )
    config = Config(str(conf))
    a = config.get_series_config('Arena')
    assert a['target_path'] == '/Media/TV/Arena (1975)'


def test_absolute_path_ignores_root(tmp_path):
    """A series with an absolute path is not joined to ROOT."""
    conf = tmp_path / "test.conf"
    conf.write_text(
        "ROOT: /Media/TV\n"
        "Special, /Other/Location/Special, https://example.com/special\n"
    )
    config = Config(str(conf))
    s = config.get_series_config('Special')
    assert s['target_path'] == '/Other/Location/Special'


def test_no_root_relative_path_kept_as_is(tmp_path):
    """Without ROOT, a relative path is stored as-is (existing behaviour)."""
    conf = tmp_path / "test.conf"
    conf.write_text("Storyville, relative/path, https://example.com/storyville\n")
    config = Config(str(conf))
    s = config.get_series_config('Storyville')
    assert s['target_path'] == 'relative/path'


def test_config_loading():
    """Test loading configuration from file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as f:
        f.write("""# Test config
Storyville, /path/to/storyville, https://thetvdb.com/series/storyville/allseasons/official
Arena, /path/to/arena, https://thetvdb.com/series/arena/allseasons/official
# Comment line
Invalid Line Without Commas
""")
        config_path = f.name

    try:
        config = Config(config_path)

        # Test case-insensitive lookup
        storyville = config.get_series_config('storyville')
        assert storyville is not None
        assert storyville['name'] == 'Storyville'
        assert storyville['target_path'] == '/path/to/storyville'
        assert storyville['tvdb_url'] == 'https://thetvdb.com/series/storyville/allseasons/official'

        # Test case-insensitive lookup
        arena = config.get_series_config('ARENA')
        assert arena is not None
        assert arena['name'] == 'Arena'

        # Test non-existent series
        missing = config.get_series_config('nonexistent')
        assert missing is None

        # Test list all series
        all_series = config.list_series()
        assert 'storyville' in all_series
        assert 'arena' in all_series

    finally:
        Path(config_path).unlink()


def test_empty_config():
    """Test handling of empty or non-existent config file."""
    with tempfile.NamedTemporaryFile(delete=True) as f:
        non_existent_path = f.name + "_not_exists"

    config = Config(non_existent_path)
    assert config.get_series_config('anything') is None
    assert len(config.list_series()) == 0


FUZZY_CONF = """For_All_Mankind, /tv/for_all_mankind, https://example.com/for-all-mankind
Landman, /tv/landman, https://example.com/landman
The_Mighty_Boosh, /tv/boosh, https://example.com/boosh
Starfleet_Academy, /tv/starfleet, https://example.com/starfleet
Triffids, /tv/triffids, https://example.com/triffids
"""


@pytest.fixture
def fuzzy_config(tmp_path):
    p = tmp_path / "test.conf"
    p.write_text(FUZZY_CONF)
    return Config(str(p))


# --- unit tests for helpers ---

def test_normalize_underscore():
    assert _normalize_to_words("For_All_Mankind") == ["for", "all", "mankind"]


def test_normalize_hyphen():
    assert _normalize_to_words("for-all-mankind") == ["for", "all", "mankind"]


def test_normalize_camelcase():
    assert _normalize_to_words("ForAllMankind") == ["for", "all", "mankind"]


def test_normalize_spaces():
    assert _normalize_to_words("for all mankind") == ["for", "all", "mankind"]


def test_subsequence_exact():
    assert _words_match_subsequence(["for", "all", "mankind"], ["for", "all", "mankind"])


def test_subsequence_prefix():
    assert _words_match_subsequence(["triffid"], ["triffids"])


def test_subsequence_skip_middle():
    assert _words_match_subsequence(["for", "mankind"], ["for", "all", "mankind"])


def test_subsequence_order_enforced():
    assert not _words_match_subsequence(["mankind", "for"], ["for", "all", "mankind"])


def test_subsequence_no_match():
    assert not _words_match_subsequence(["mankind"], ["landman"])


# --- find_fuzzy_matches ---

def test_fuzzy_single_word_matches(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("mankind")
    assert len(matches) == 1
    assert matches[0]['name'] == 'For_All_Mankind'


def test_fuzzy_no_false_positive_landman(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("mankind")
    assert all(m['name'] != 'Landman' for m in matches)


def test_fuzzy_prefix_match(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("triffid")
    assert len(matches) == 1
    assert matches[0]['name'] == 'Triffids'


def test_fuzzy_camelcase_input(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("ForAllMankind")
    assert len(matches) == 1
    assert matches[0]['name'] == 'For_All_Mankind'


def test_fuzzy_hyphenated_input(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("for-all-mankind")
    assert len(matches) == 1
    assert matches[0]['name'] == 'For_All_Mankind'


def test_fuzzy_partial_skip(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("for mankind")
    assert len(matches) == 1
    assert matches[0]['name'] == 'For_All_Mankind'


def test_fuzzy_word_in_wrong_order(fuzzy_config):
    matches = fuzzy_config.find_fuzzy_matches("boosh mighty")
    assert len(matches) == 0


def test_fuzzy_no_match_returns_empty(fuzzy_config):
    assert fuzzy_config.find_fuzzy_matches("xyzzy") == []


def test_fuzzy_short_words_ignored(fuzzy_config):
    # "a" is < 3 chars, should not match everything
    matches = fuzzy_config.find_fuzzy_matches("a")
    assert matches == []


def test_add_series_appends_entry(tmp_path):
    conf = tmp_path / "test.conf"
    conf.write_text("Storyville, /tv/storyville, https://example.com/storyville\n")
    config = Config(str(conf))
    result = config.add_series("Arena", "/tv/arena", "https://example.com/arena")
    assert result is True
    assert config.get_series_config("Arena") is None  # not reloaded in same instance
    config2 = Config(str(conf))
    assert config2.get_series_config("Arena") is not None


def test_add_series_duplicate_rejected(tmp_path):
    conf = tmp_path / "test.conf"
    conf.write_text("Storyville, /tv/storyville, https://example.com/storyville\n")
    config = Config(str(conf))
    result = config.add_series("Storyville", "/tv/other", "https://example.com/other")
    assert result is False
    assert conf.read_text().count("Storyville") == 1


def test_add_series_duplicate_case_insensitive(tmp_path):
    conf = tmp_path / "test.conf"
    conf.write_text("Storyville, /tv/storyville, https://example.com/storyville\n")
    config = Config(str(conf))
    result = config.add_series("STORYVILLE", "/tv/other", "https://example.com/other")
    assert result is False


def test_add_series_no_trailing_newline(tmp_path):
    conf = tmp_path / "test.conf"
    conf.write_text("Storyville, /tv/storyville, https://example.com/storyville")  # no newline
    config = Config(str(conf))
    config.add_series("Arena", "/tv/arena", "https://example.com/arena")
    lines = [l for l in conf.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_create_example_config():
    """Test creating example configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.conf"
        config = Config(str(config_path))
        config.create_example_config()

        assert config_path.exists()
        content = config_path.read_text()
        assert 'Storyville' in content
        assert 'Arena' in content