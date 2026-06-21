from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Utterance:
    text: str
    pause_ms: int
    count: bool = True
    points: set[int] = field(default_factory=set)
    block_id: str = ""


@dataclass
class AudioBlock:
    block_id: str
    kind: str
    rate: str
    voice: str
    utterances: list[Utterance]


@dataclass
class Topic:
    source: Path
    metadata: dict[str, object]
    blocks: list[AudioBlock]

    @property
    def output_name(self) -> str:
        return str(self.metadata["output"])

