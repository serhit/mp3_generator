import re
import shlex
import tomllib
from pathlib import Path

from .model import AudioBlock, Topic, Utterance


REQUIRED_METADATA = {
    "title",
    "artist",
    "album",
    "language",
    "lyrics_language",
    "voice",
    "output",
}
DIRECTIVE_RE = re.compile(r'^:::audio(?:\s+(.*))?$')
LINE_ATTRS_RE = re.compile(r"^(.*?)(?:\s+\{([^{}]+)\})?\s*$")
RATE_RE = re.compile(r"^[+-]\d+%$")
PAUSE_RE = re.compile(r"^(\d+(?:\.\d+)?)(ms|s)$")
WORD_RE = re.compile(r"\b[\wÄÖÜäöüß]+(?:-[\wÄÖÜäöüß]+)*\b", re.UNICODE)


class ScenarioError(ValueError):
    pass


def parse_attributes(raw: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError as error:
        raise ScenarioError(f"Invalid attributes: {raw}: {error}") from error
    for token in tokens:
        if "=" not in token:
            raise ScenarioError(f"Expected key=value attribute, got: {token}")
        key, value = token.split("=", 1)
        if not key or key in attributes:
            raise ScenarioError(f"Invalid or duplicate attribute: {key}")
        attributes[key] = value
    return attributes


def parse_pause(value: str) -> int:
    match = PAUSE_RE.fullmatch(value)
    if not match:
        raise ScenarioError(f"Invalid pause value: {value}")
    amount = float(match.group(1))
    milliseconds = round(amount if match.group(2) == "ms" else amount * 1000)
    if milliseconds < 0 or milliseconds > 30_000:
        raise ScenarioError(f"Pause must be between 0ms and 30s: {value}")
    return milliseconds


def parse_bool(value: str) -> bool:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise ScenarioError(f"Expected true or false, got: {value}")


def parse_front_matter(text: str) -> tuple[dict[str, object], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "+++":
        raise ScenarioError("Scenario must start with TOML front matter (+++)")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "+++")
    except StopIteration as error:
        raise ScenarioError("TOML front matter is not closed with +++") from error
    try:
        metadata = tomllib.loads("\n".join(lines[1:end]))
    except tomllib.TOMLDecodeError as error:
        raise ScenarioError(f"Invalid TOML front matter: {error}") from error
    missing = REQUIRED_METADATA - metadata.keys()
    if missing:
        raise ScenarioError(f"Missing metadata: {', '.join(sorted(missing))}")
    return metadata, lines[end + 1 :]


def parse_scenario(path: Path) -> Topic:
    metadata, lines = parse_front_matter(path.read_text(encoding="utf-8"))
    blocks: list[AudioBlock] = []
    block_ids: set[str] = set()
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        directive = DIRECTIVE_RE.fullmatch(stripped)
        if not directive:
            raise ScenarioError(f"Unexpected content outside audio block: {stripped}")

        attrs = parse_attributes(directive.group(1) or "")
        allowed = {"id", "kind", "rate", "default_pause", "voice"}
        unknown = set(attrs) - allowed
        if unknown:
            raise ScenarioError(f"Unknown block attributes: {', '.join(sorted(unknown))}")
        block_id = attrs.get("id", "")
        if not block_id or block_id in block_ids:
            raise ScenarioError(f"Block id must be non-empty and unique: {block_id}")
        block_ids.add(block_id)
        kind = attrs.get("kind", "narration")
        rate = attrs.get("rate", "+0%")
        if not RATE_RE.fullmatch(rate):
            raise ScenarioError(f"Invalid rate in block {block_id}: {rate}")
        voice = attrs.get("voice", str(metadata["voice"]))
        default_pause = parse_pause(attrs.get("default_pause", "200ms"))
        utterances: list[Utterance] = []

        while index < len(lines) and lines[index].strip() != ":::":
            raw_line = lines[index].strip()
            index += 1
            if not raw_line or raw_line.startswith("#"):
                continue
            match = LINE_ATTRS_RE.fullmatch(raw_line)
            assert match is not None
            text_value = match.group(1).strip()
            if not text_value:
                raise ScenarioError(f"Empty utterance in block {block_id}")
            line_attrs = parse_attributes(match.group(2) or "")
            unknown_line = set(line_attrs) - {"pause", "count", "point"}
            if unknown_line:
                raise ScenarioError(
                    f"Unknown line attributes in {block_id}: {', '.join(sorted(unknown_line))}"
                )
            pause_ms = parse_pause(line_attrs["pause"]) if "pause" in line_attrs else default_pause
            count = parse_bool(line_attrs.get("count", "true"))
            points: set[int] = set()
            if "point" in line_attrs:
                try:
                    points = {int(value) for value in line_attrs["point"].split(",")}
                except ValueError as error:
                    raise ScenarioError(f"Invalid point value in {block_id}") from error
                if not points <= {1, 2, 3}:
                    raise ScenarioError(f"Points must be 1, 2, or 3 in {block_id}")
            utterances.append(Utterance(text_value, pause_ms, count, points, block_id))

        if index >= len(lines):
            raise ScenarioError(f"Audio block {block_id} is not closed with :::")
        index += 1
        if not utterances:
            raise ScenarioError(f"Audio block {block_id} is empty")
        blocks.append(AudioBlock(block_id, kind, rate, voice, utterances))

    topic = Topic(path, metadata, blocks)
    validate_topic(topic)
    return topic


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def validate_topic(topic: Topic) -> None:
    if not topic.blocks:
        raise ScenarioError("Scenario has no audio blocks")
    answer_blocks = [block for block in topic.blocks if block.kind == "answer"]
    if len(answer_blocks) != 1:
        raise ScenarioError("Scenario must contain exactly one kind=answer block")
    if not any(block.kind == "repeat" for block in topic.blocks):
        raise ScenarioError("Scenario must contain a kind=repeat block")

    counted = [utterance for utterance in answer_blocks[0].utterances if utterance.count]
    word_count = sum(count_words(utterance.text) for utterance in counted)
    if not 35 <= word_count <= 45:
        raise ScenarioError(f"Answer must contain 35-45 counted words, got {word_count}")
    covered = set().union(*(utterance.points for utterance in counted))
    if covered != {1, 2, 3}:
        raise ScenarioError(f"Answer must cover points 1, 2, and 3, got {sorted(covered)}")

