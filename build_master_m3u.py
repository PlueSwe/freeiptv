#!/usr/bin/env python3
"""Build clean master and Sweden-only M3U playlists."""

from collections import defaultdict
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

MASTER_OUTPUT = Path("master.m3u")
SWEDEN_OUTPUT = Path("sweden.m3u")
TIMEOUT = 45

SOURCE_ORDER = {
    name: i for i, (name, _) in enumerate(SOURCES)
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PlueSwe-freeiptv/2.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def attr(line: str, name: str) -> str:
    match = re.search(
        rf'{re.escape(name)}="([^"]*)"',
        line,
        re.I,
    )
    return match.group(1).strip() if match else ""


def normalize(value: str) -> str:
    return re.sub(
        r"\W+",
        "",
        value.lower(),
        flags=re.UNICODE,
    )


def channel_name(info: str) -> str:
    return info.rsplit(",", 1)[-1].strip()


def parse_m3u(text: str):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    entries = []

    for i, line in enumerate(lines[:-1]):
        if (
            line.startswith("#EXTINF")
            and not lines[i + 1].startswith("#")
        ):
            entries.append((line, lines[i + 1]))

    return entries


def is_sweden(source_name: str, info: str) -> bool:

    # These sources are explicitly Sweden-specific.
    if source_name in {
        "Pluto TV SE",
        "IPTV-org Sweden",
    }:
        return True

    country = attr(info, "tvg-country").upper()

    if re.search(
        r"(^|[,;| ])SE($|[,;| ])",
        country,
    ):
        return True

    group = attr(info, "group-title").strip().lower()

    if group in {
        "sweden",
        "sverige",
        "swedish",
        "svenska",
        "svenska kanaler",
    }:
        return True

    tvg_id = attr(info, "tvg-id").lower()
    channel_id = attr(info, "channel-id").lower()

    if tvg_id.endswith("-se"):
        return True

    if channel_id.endswith("-se"):
        return True

    return False


def sweden_group(source_name: str, info: str) -> str:

    original = attr(info, "group-title").strip()

    if source_name == "Pluto TV SE":
        prefix = "🇸🇪 Sverige · Pluto TV"

    elif source_name == "Samsung TV Plus":
        prefix = "🇸🇪 Sverige · Samsung TV Plus"

    elif source_name == "Roku":
        prefix = "🇸🇪 Sverige · Roku"

    elif source_name == "Free-TV":
        prefix = "🇸🇪 Sverige · Free-TV"

    else:
        prefix = "🇸🇪 Sverige · IPTV-org"

    return f"{prefix} · {original or 'Övrigt'}"


def replace_group(info: str, group: str) -> str:

    if re.search(
        r'group-title="[^"]*"',
        info,
        re.I,
    ):
        return re.sub(
            r'group-title="[^"]*"',
            f'group-title="{group}"',
            info,
            count=1,
            flags=re.I,
        )

    return (
        info.rsplit(",", 1)[0]
        + f' group-title="{group}",'
        + channel_name(info)
    )


def international_group(info: str) -> str:
    return (
        attr(info, "group-title").strip()
        or "Other"
    )


def dedupe(entries):

    seen_urls = set()
    seen_channels = set()

    result = []

    for source_name, info, url in entries:

        # Exact stream duplicate.
        if url in seen_urls:
            continue

        name = normalize(channel_name(info))
        tvg_id = normalize(attr(info, "tvg-id"))
        country = normalize(attr(info, "tvg-country"))

        # Prefer tvg-id when available, otherwise channel name.
        channel_key = tvg_id or name

        # Deduplicate within the same source/country.
        key = (
            source_name,
            channel_key,
            country,
        )

        if key in seen_channels:
            continue

        seen_urls.add(url)
        seen_channels.add(key)

        result.append(
            (source_name, info, url)
        )

    return result


def write_playlist(path: Path, entries):

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output:

        output.write("#EXTM3U\n")

        for _, info, url in entries:
            output.write(info + "\n")
            output.write(url + "\n")


def main():

    raw_entries = []
    stats = []

    for source_name, url in SOURCES:

        try:
            entries = parse_m3u(
                fetch(url)
            )

            stats.append(
                (
                    source_name,
                    len(entries),
                    "OK",
                )
            )

            raw_entries.extend(
                (
                    source_name,
                    info,
                    stream,
                )
                for info, stream in entries
            )

        except Exception as exc:

            stats.append(
                (
                    source_name,
                    0,
                    f"ERROR: {exc}",
                )
            )

    unique = dedupe(raw_entries)

    sweden = []
    international = []

    source_counts = defaultdict(int)

    for source_name, info, url in unique:

        source_counts[source_name] += 1

        if is_sweden(source_name, info):

            info = replace_group(
                info,
                sweden_group(
                    source_name,
                    info,
                ),
            )

            sweden.append(
                (
                    source_name,
                    info,
                    url,
                )
            )

        else:

            international.append(
                (
                    source_name,
                    info,
                    url,
                )
            )

    # Sweden first.
    sweden.sort(
        key=lambda e: (
            SOURCE_ORDER[e[0]],
            channel_name(e[1]).lower(),
        )
    )

    # International channels grouped alphabetically.
    international.sort(
        key=lambda e: (
            international_group(e[1]).lower(),
            channel_name(e[1]).lower(),
            SOURCE_ORDER[e[0]],
        )
    )

    write_playlist(
        SWEDEN_OUTPUT,
        sweden,
    )

    write_playlist(
        MASTER_OUTPUT,
        sweden + international,
    )

    print(
        f"Created {SWEDEN_OUTPUT}: "
        f"{len(sweden):,} Swedish channels"
    )

    print(
        f"Created {MASTER_OUTPUT}: "
        f"{len(sweden) + len(international):,} total channels"
    )

    print()

    for name, count, status in stats:
        print(
            f"{name}: "
            f"{count:,} parsed [{status}]"
        )

    print()

    print(
        f"Sweden: {len(sweden):,}"
    )

    print(
        f"International: "
        f"{len(international):,}"
    )


if __name__ == "__main__":
    main()
