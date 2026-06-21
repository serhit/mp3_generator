# TELC A1 Audio Generator

Generate a continuous neural-voice MP3, a plain transcript, and synchronized
LRC lyrics from a structured Markdown scenario.

## Setup

Python 3.12 and `lame` must be available.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Commands

Create and verify the album cover before any TTS build. The cover is a required
parameter so every generated MP3 receives the same front-cover `APIC` frame.

```bash
telc-audio validate path/to/topic.md
telc-audio build path/to/topic.md --cover path/to/cover.jpg
telc-audio build-all "../Deutsch A1 TELC" --cover path/to/cover.jpg
telc-audio embed-cover "../Deutsch A1 TELC" --cover path/to/cover.jpg
```

Runnable Bash and PowerShell examples are available under `examples/`.

## Scenario format

The file starts with TOML front matter. Audio blocks contain one spoken
sentence per line. Adjacent blocks with the same voice and rate are synthesized
in one request to preserve prosody.

```markdown
+++
title = "Aufgabe 01: Geburtstag"
artist = "Deutsch A1 TELC"
album = "TELC A1 Schreiben"
language = "de-DE"
lyrics_language = "deu"
voice = "de-DE-KatjaNeural"
output = "01_Geburtstag"
+++

:::audio id="answer" kind="answer" rate="+0%" default_pause="200ms"
Liebe Anna. {count=false}
Die Party beginnt um achtzehn Uhr. {point=1}
Viele Grüße. {count=false}
Sergey. {count=false}
:::
```

Supported line attributes:

- `pause="3s"` or `pause="300ms"`: override the block pause.
- `count=false`: exclude the line from answer word counting.
- `point=1` or `point="1,2"`: mark the TELC prompt points answered by the line.

The `answer` block must contain 35-45 counted words and cover points 1, 2, and
3. `--cover` is required and embeds a JPEG or PNG as the front-cover `APIC`
frame. The generated MP3 includes title, artist, album, language, APIC, USLT,
and SYLT ID3 frames. Apple Music and Yandex Music do not guarantee display of
embedded lyrics for personally uploaded tracks; the `.txt` and `.lrc` files
are kept as portable transcript sources.
