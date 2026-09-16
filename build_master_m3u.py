#!/usr/bin/env python3
"""Build a single deduplicated M3U playlist from the configured free IPTV sources."""

from pathlib import Path
import re
import urllib.request

SOURCES = [
    ("Free-TV", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
    ("Roku", "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/roku_all.m3u"),
    ("Pluto TV SE", "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_se.m3u"),
    ("Samsung TV Plus", "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/samsungtvplus_all.m3u"),
    ("IPTV-org Sweden", "https://iptv-org.github.io/iptv/countries/se.m3u"),
]

OUTPUT = Path("master.m3u")
TIMEOUT = 45


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PlueSwe-freeiptv/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def attr(line: str, name: str) -> str:
    match = re.search(rf'{re.escape(name)}="([^"]*)"', line, re.I)
    return match.group(1).strip() if match else ""


def normalize(value: str) -> str:
    return re.sub(r"\W+", "", value.lower(), flags=re.UNICODE)


def parse_m3u(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    entries = []

    for i, line in enumerate(lines[:-1]):
        if line.startswith("#EXTINF") and not lines[i + 1].startswith("#"):
            entries.append((line, lines[i + 1]))

    return entries


def main():
    all_entries = []
    stats = []

    for source_name, url in SOURCES:
        try:
            entries = parse_m3u(fetch(url))
            stats.append((source_name, len(entries), "OK"))
            all_entries.extend(entries)
        except Exception as exc:
            stats.append((source_name, 0, f"ERROR: {exc}"))

    seen_urls = set()
    seen_ids = set()
    seen_names = set()
    unique = []

    for info, url in all_entries:
        if url in seen_urls:
            continue

        tvg_id = attr(info, "tvg-id")
        group = attr(info, "group-title")
        name = info.rsplit(",", 1)[-1].strip()

        if tvg_id:
            key = normalize(tvg_id)
            if key in seen_ids:
                continue
            seen_ids.add(key)
        else:
            key = (normalize(name), normalize(group))
            if key in seen_names:
                continue
            seen_names.add(key)

        seen_urls.add(url)
        unique.append((info, url))

    # Prefer an existing #EXTM3U header, including EPG attributes if supplied.
    header = "#EXTM3U"
    for info_source, url in SOURCES:
        try:
            first_line = fetch(url).splitlines()[0].strip()
            if first_line.startswith("#EXTM3U"):
                header = first_line
                break
        except Exception:
            pass

    with OUTPUT.open("w", encoding="utf-8", newline="\n") as output:
        output.write(header + "\n")
        for info, url in unique:
            output.write(info + "\n")
            output.write(url + "\n")

    print(f"Created {OUTPUT}: {len(unique):,} unique channels")
    for name, count, status in stats:
        print(f"{name}: {count:,} entries [{status}]")


if __name__ == "__main__":
    main()
