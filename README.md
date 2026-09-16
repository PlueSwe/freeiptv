# PlueSwe Free IPTV

This repository builds one master M3U playlist from several publicly available IPTV playlists.

## Sources

- Free-TV
- Roku
- Pluto TV Sweden
- Samsung TV Plus
- IPTV-org Sweden

The GitHub Action rebuilds `master.m3u` automatically once per day and can also be started manually from the **Actions** tab.

## Playlist URL

After the first successful Action run:

`https://raw.githubusercontent.com/PlueSwe/freeiptv/main/master.m3u`

## Notes

This project only aggregates the supplied playlist URLs. It does not host or re-stream the underlying video streams.
Availability and licensing of individual channels are determined by their respective providers.
