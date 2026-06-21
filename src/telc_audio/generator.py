import asyncio
import json
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from mutagen.id3 import APIC, ID3, TALB, TIT2, TLAN, TPE1, SYLT, USLT

from .model import AudioBlock, Topic, Utterance


@dataclass
class TimedLine:
    text: str
    start_ms: int
    block_id: str


def require_lame() -> str:
    executable = shutil.which("lame")
    if not executable:
        raise RuntimeError("lame is required but was not found in PATH")
    return executable


def group_blocks(blocks: list[AudioBlock]) -> list[list[AudioBlock]]:
    groups: list[list[AudioBlock]] = []
    for block in blocks:
        if groups and (groups[-1][-1].voice, groups[-1][-1].rate) == (block.voice, block.rate):
            groups[-1].append(block)
        else:
            groups.append([block])
    return groups


async def synthesize_group(
    blocks: list[AudioBlock], mp3_path: Path, metadata_path: Path
) -> list[Utterance]:
    utterances = [utterance for block in blocks for utterance in block.utterances]
    speech = edge_tts.Communicate(
        " ".join(utterance.text for utterance in utterances),
        blocks[0].voice,
        rate=blocks[0].rate,
        boundary="SentenceBoundary",
    )
    await speech.save(str(mp3_path), str(metadata_path))
    return utterances


def read_boundaries(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def add_pauses(
    source_wav: Path,
    target_wav: Path,
    boundaries: list[dict],
    utterances: list[Utterance],
) -> tuple[list[TimedLine], int]:
    if len(boundaries) != len(utterances):
        raise RuntimeError(
            f"TTS returned {len(boundaries)} sentence boundaries for "
            f"{len(utterances)} utterances. Keep one sentence per audio line."
        )
    with wave.open(str(source_wav), "rb") as source:
        params = source.getparams()
        audio = source.readframes(source.getnframes())
    frame_size = params.sampwidth * params.nchannels
    total_frames = len(audio) // frame_size
    chunks: list[bytes] = []
    timings: list[TimedLine] = []
    previous_frame = 0
    inserted_frames = 0

    for boundary, utterance in zip(boundaries, utterances, strict=True):
        start_frame = round(boundary["offset"] * params.framerate / 10_000_000)
        end_ticks = boundary["offset"] + boundary["duration"]
        end_frame = min(round(end_ticks * params.framerate / 10_000_000), total_frames)
        if end_frame < previous_frame:
            raise RuntimeError("TTS sentence boundaries are not chronological")
        adjusted_start = start_frame + inserted_frames
        timings.append(
            TimedLine(
                utterance.text,
                round(adjusted_start * 1000 / params.framerate),
                utterance.block_id,
            )
        )
        chunks.append(audio[previous_frame * frame_size : end_frame * frame_size])
        pause_frames = round(params.framerate * utterance.pause_ms / 1000)
        chunks.append(b"\0" * pause_frames * frame_size)
        inserted_frames += pause_frames
        previous_frame = end_frame
    chunks.append(audio[previous_frame * frame_size :])

    with wave.open(str(target_wav), "wb") as target:
        target.setparams(params)
        for chunk in chunks:
            target.writeframes(chunk)
    duration_ms = round((total_frames + inserted_frames) * 1000 / params.framerate)
    return timings, duration_ms


def combine_wavs(paths: list[Path], target_path: Path) -> list[int]:
    params = None
    chunks: list[bytes] = []
    offsets_ms: list[int] = []
    accumulated_frames = 0
    for path in paths:
        with wave.open(str(path), "rb") as source:
            current = source.getparams()
            if params is None:
                params = current
            elif current[:3] + current[4:] != params[:3] + params[4:]:
                raise RuntimeError("Generated audio groups have incompatible formats")
            offsets_ms.append(round(accumulated_frames * 1000 / current.framerate))
            data = source.readframes(source.getnframes())
            chunks.append(data)
            accumulated_frames += len(data) // (current.sampwidth * current.nchannels)
    if params is None:
        raise RuntimeError("No audio was generated")
    with wave.open(str(target_path), "wb") as target:
        target.setparams(params)
        for chunk in chunks:
            target.writeframes(chunk)
    return offsets_ms


def transcript_text(topic: Topic) -> str:
    sections = []
    for block in topic.blocks:
        sections.append("\n".join(utterance.text for utterance in block.utterances))
    return "\n\n".join(sections) + "\n"


def lrc_timestamp(milliseconds: int) -> str:
    minutes, remainder = divmod(milliseconds, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{minutes:02d}:{seconds:02d}.{millis // 10:02d}"


def write_lrc(path: Path, topic: Topic, lines: list[TimedLine]) -> None:
    content = [
        f"[ti:{topic.metadata['title']}]",
        f"[ar:{topic.metadata['artist']}]",
        f"[al:{topic.metadata['album']}]",
        f"[language:{topic.metadata['language']}]",
    ]
    content.extend(f"[{lrc_timestamp(line.start_ms)}]{line.text}" for line in lines)
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def cover_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    raise RuntimeError(f"Cover must be a JPEG or PNG file: {path}")


def validate_cover(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError(f"Cover file is missing or empty: {path}")
    cover_mime_type(resolved)
    return resolved


def embed_cover(mp3_path: Path, cover_path: Path) -> None:
    cover = validate_cover(cover_path)
    tags = ID3(mp3_path)
    tags.delall("APIC")
    tags.add(
        APIC(
            encoding=1,
            mime=cover_mime_type(cover),
            type=3,
            desc="Cover",
            data=cover.read_bytes(),
        )
    )
    tags.save(mp3_path, v2_version=3)


def add_id3_tags(
    mp3_path: Path,
    topic: Topic,
    transcript: str,
    lines: list[TimedLine],
    cover_path: Path,
) -> None:
    tags = ID3()
    tags.add(TIT2(encoding=1, text=str(topic.metadata["title"])))
    tags.add(TPE1(encoding=1, text=str(topic.metadata["artist"])))
    tags.add(TALB(encoding=1, text=str(topic.metadata["album"])))
    tags.add(TLAN(encoding=1, text=str(topic.metadata["language"])))
    language = str(topic.metadata["lyrics_language"])
    tags.add(USLT(encoding=1, lang=language, desc="Transcript", text=transcript))
    tags.add(
        SYLT(
            encoding=1,
            lang=language,
            format=2,
            type=1,
            desc="Transcript",
            text=[(line.text, line.start_ms) for line in lines],
        )
    )
    cover = validate_cover(cover_path)
    tags.add(
        APIC(
            encoding=1,
            mime=cover_mime_type(cover),
            type=3,
            desc="Cover",
            data=cover.read_bytes(),
        )
    )
    tags.save(mp3_path, v2_version=3)


async def build_topic(
    topic: Topic,
    cover_path: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    lame = require_lame()
    destination = output_dir or topic.source.parent
    destination.mkdir(parents=True, exist_ok=True)
    base = destination / topic.output_name
    mp3_output = base.with_suffix(".mp3")
    txt_output = base.with_suffix(".txt")
    lrc_output = base.with_suffix(".lrc")

    with tempfile.TemporaryDirectory(prefix="telc-audio-") as temporary:
        temp = Path(temporary)
        group_wavs: list[Path] = []
        group_timings: list[list[TimedLine]] = []
        for index, blocks in enumerate(group_blocks(topic.blocks)):
            raw_mp3 = temp / f"group_{index}_raw.mp3"
            metadata = temp / f"group_{index}.jsonl"
            raw_wav = temp / f"group_{index}_raw.wav"
            paused_wav = temp / f"group_{index}_paused.wav"
            utterances = await synthesize_group(blocks, raw_mp3, metadata)
            subprocess.run(
                [lame, "--silent", "--decode", str(raw_mp3), str(raw_wav)],
                check=True,
            )
            timings, _ = add_pauses(
                raw_wav, paused_wav, read_boundaries(metadata), utterances
            )
            group_wavs.append(paused_wav)
            group_timings.append(timings)

        combined_wav = temp / "combined.wav"
        offsets = combine_wavs(group_wavs, combined_wav)
        all_timings = [
            TimedLine(line.text, line.start_ms + offset, line.block_id)
            for offset, timings in zip(offsets, group_timings, strict=True)
            for line in timings
        ]
        subprocess.run(
            [lame, "--silent", "-b", "128", str(combined_wav), str(mp3_output)],
            check=True,
        )

    transcript = transcript_text(topic)
    txt_output.write_text(transcript, encoding="utf-8")
    write_lrc(lrc_output, topic, all_timings)
    add_id3_tags(mp3_output, topic, transcript, all_timings, cover_path)
    return [mp3_output, txt_output, lrc_output]


def build_topic_sync(
    topic: Topic,
    cover_path: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    return asyncio.run(build_topic(topic, cover_path, output_dir))
