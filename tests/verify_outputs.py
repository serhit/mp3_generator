import argparse
import re
from pathlib import Path

from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from telc_audio.generator import (
    DEFAULT_ALBUM_ARTIST,
    DEFAULT_COMMENT,
    DEFAULT_COMPOSER,
    DEFAULT_DISC_NUMBER,
    DEFAULT_DISC_TOTAL,
    DEFAULT_GENRE,
    DEFAULT_GROUPING,
    DEFAULT_YEAR,
    topic_track_number,
    topic_track_total,
)
from telc_audio.parser import parse_scenario


LRC_RE = re.compile(r"^\[(\d+):(\d+)\.(\d+)](.*)$")
REQUIRED_PREFIXES = (
    "TIT2",
    "TPE1",
    "TALB",
    "TLAN",
    "TPE2",
    "TCOM",
    "TIT1",
    "TCON",
    "TDRC",
    "TRCK",
    "TPOS",
    "TCMP",
    "COMM",
    "USLT",
    "SYLT",
)


def lrc_milliseconds(line: str) -> int | None:
    match = LRC_RE.match(line)
    if not match:
        return None
    return (
        int(match.group(1)) * 60_000
        + int(match.group(2)) * 1000
        + int(match.group(3)) * 10
    )


def verify(root: Path, cover_path: Path | None = None) -> None:
    scenarios = sorted(path for path in root.rglob("*.md") if "_prototype" not in path.parts)
    if len(scenarios) != 20:
        raise AssertionError(f"Expected 20 scenarios, found {len(scenarios)}")

    durations = []
    for scenario in scenarios:
        topic = parse_scenario(scenario)
        base = scenario.parent / topic.output_name
        mp3_path = base.with_suffix(".mp3")
        txt_path = base.with_suffix(".txt")
        lrc_path = base.with_suffix(".lrc")
        for path in (mp3_path, txt_path, lrc_path):
            if not path.is_file() or path.stat().st_size == 0:
                raise AssertionError(f"Missing or empty output: {path}")

        audio = MP3(mp3_path)
        if audio.info.length <= 0 or audio.info.bitrate != 128_000:
            raise AssertionError(f"Invalid audio properties: {mp3_path}")
        durations.append(audio.info.length)

        tags = ID3(mp3_path)
        for prefix in REQUIRED_PREFIXES:
            if not tags.getall(prefix):
                raise AssertionError(f"Missing {prefix} in {mp3_path}")
        expected = {
            "TPE2": DEFAULT_ALBUM_ARTIST,
            "TCOM": DEFAULT_COMPOSER,
            "TIT1": DEFAULT_GROUPING,
            "TCON": DEFAULT_GENRE,
            "TDRC": DEFAULT_YEAR,
            "TRCK": f"{topic_track_number(topic)}/{topic_track_total(topic)}",
            "TPOS": f"{DEFAULT_DISC_NUMBER}/{DEFAULT_DISC_TOTAL}",
            "TCMP": "0",
        }
        for frame, value in expected.items():
            actual = str(tags[frame])
            if actual != value:
                raise AssertionError(
                    f"Unexpected {frame} in {mp3_path}: {actual!r} != {value!r}"
                )
        comments = [text for frame in tags.getall("COMM") for text in frame.text]
        if DEFAULT_COMMENT not in comments:
            raise AssertionError(f"Missing Apple Music comment in {mp3_path}")
        if cover_path is not None:
            pictures = tags.getall("APIC")
            if len(pictures) != 1:
                raise AssertionError(f"Expected one APIC cover in {mp3_path}")
            if pictures[0].data != cover_path.read_bytes():
                raise AssertionError(f"APIC does not match cover file: {mp3_path}")
        transcript = txt_path.read_text(encoding="utf-8")
        if tags.getall("USLT")[0].text != transcript:
            raise AssertionError(f"USLT does not match TXT: {mp3_path}")

        spoken_lines = [
            utterance.text for block in topic.blocks for utterance in block.utterances
        ]
        sylt_lines = tags.getall("SYLT")[0].text
        if [text for text, _ in sylt_lines] != spoken_lines:
            raise AssertionError(f"SYLT does not match scenario: {mp3_path}")

        timestamps = [
            timestamp
            for line in lrc_path.read_text(encoding="utf-8").splitlines()
            if (timestamp := lrc_milliseconds(line)) is not None
        ]
        if len(timestamps) != len(spoken_lines):
            raise AssertionError(f"LRC line count mismatch: {lrc_path}")
        if timestamps != sorted(timestamps):
            raise AssertionError(f"LRC timestamps are not monotonic: {lrc_path}")
        if timestamps[-1] > audio.info.length * 1000:
            raise AssertionError(f"LRC timestamp exceeds audio duration: {lrc_path}")

    print(
        f"Verified {len(scenarios)} topics; duration range "
        f"{min(durations):.1f}-{max(durations):.1f} seconds"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--cover", type=Path)
    args = parser.parse_args()
    verify(args.root, args.cover)


if __name__ == "__main__":
    main()
