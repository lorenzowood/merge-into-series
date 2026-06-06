# TODO

Issues discovered while processing Star Trek: Voyager DVD rips (June 2026).

---

## 1. No abort during interactive phase

**Problem:** During the interactive episode-matching phase, CTRL+C does not abort cleanly. The user is stuck: they must skip through every remaining file to reach the final move/copy prompt, only then choosing not to proceed. This is slow and painful if you realise early that something is wrong (e.g. all episode numbers are off by one).

**Likely fix:** Trap SIGINT during the interactive loop. On receipt, show:

```
Abort? [y/N]
```

- `y` (or a second CTRL+C): exit cleanly without moving or copying anything.
- `n` (or Enter): resume exactly where the user was.

---

## 2. Support multiple episode list URLs per series

**Problem:** Each series entry in `~/.merge-into-series.conf` holds a single TVDB URL. When a collection uses a different episode ordering than that URL (e.g. files are DVD rips but the config points at the official broadcast order), matches are off and there is no easy fix short of manually editing the config.

The underlying issue is that some series have genuinely different orderings — official broadcast, DVD, absolute — and a file collection may follow any of them. Voyager is the confirmed case: on DVD, some two-part episodes were combined into one, shifting all subsequent episode numbers. Having only the broadcast URL meant every episode after the first combined pair was matched one slot wrong.

**Proposed fix:** Allow a series entry to carry multiple URLs:

```
Star_Trek:_Voyager,Star Trek -- Voyager (1995) {tvdb-74550},https://...allseasons/official,https://...allseasons/dvd
```

When matching, fetch episode metadata from *all* registered URLs and merge the candidate lists. Pick the best match across all orderings. If a file matches convincingly against the DVD list but not the official list, use the DVD result.

This would handle the Voyager case without requiring the user to know in advance which ordering their files follow.

**Impact on the browser extension:** Once this is supported, `merge-into-series-tvdb-plugin` should be updated to generate `--add` commands that include both the official and DVD URLs (where a DVD ordering exists on the TVDB page). See TODO.md in that project.
