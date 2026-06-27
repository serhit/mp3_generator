# TELC A1 Audio Generator

Generate a continuous neural-voice MP3, an exam-style plain transcript, and
synchronized LRC lyrics from a structured Markdown scenario.

## Dependencies

The generator requires:

- **Python 3.12 or newer** for the CLI and TOML parsing.
- **Internet access during generation** because `edge-tts` calls Microsoft's
  online neural speech service.
- **LAME 3.100 or newer** available as the `lame` command on `PATH`. It decodes
  the TTS stream to WAV, then encodes the final audio as a 128 kbps MP3 after
  pauses have been inserted.
- A square JPEG or PNG cover. `--cover` is mandatory for `build` and
  `build-all`; the image is embedded as the ID3 front-cover `APIC` frame.

Python dependencies are declared only in `pyproject.toml` and are installed
automatically:

- `edge-tts==7.2.8` — neural German speech and sentence timing boundaries.
- `mutagen==1.47.0` — ID3 metadata, embedded artwork, USLT, and SYLT lyrics.

`lame` is a native executable, not a Python package, so it cannot be installed
from `pyproject.toml`.

## Install system dependencies

### macOS

Install [Homebrew](https://brew.sh/) if necessary, then run:

```bash
brew install python@3.12 lame
python3.12 --version
lame --version
```

The `lame` command is provided by the official
[Homebrew formula](https://formulae.brew.sh/formula/lame).

### Ubuntu or Debian

```bash
sudo apt update
sudo apt install python3 python3-venv lame
python3 --version
lame --version
```

Confirm that `python3 --version` is at least 3.12. Older operating-system
releases may need a newer Python from [python.org](https://www.python.org/downloads/)
or a Python version manager. `lame` is available through the distribution's
normal package repository.

### Windows 10 or 11

1. Install Python 3.12 or newer from
   [python.org](https://www.python.org/downloads/windows/). Enable **Add Python
   to PATH** during installation.
2. Install [Chocolatey](https://chocolatey.org/install) if it is not already
   available.
3. Open an elevated PowerShell window and run:

```powershell
choco install lame -y
py -3.12 --version
lame --version
```

The Windows command uses the moderator-approved
[Chocolatey LAME package](https://community.chocolatey.org/packages/lame).
Restart the terminal after installation if `lame` is not immediately found.

## Install the Python project

From the `telc-a1-audio-generator` directory:

### macOS, Linux, or Bash

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e .
.venv/bin/telc-audio --help
```

If the executable is named `python3` and is version 3.12 or newer, use
`python3` instead of `python3.12`.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -e .
.venv\Scripts\telc-audio.exe --help
```

Activation is optional because the examples call executables inside `.venv`
directly.

## Verify the installation

```bash
lame --version
.venv/bin/python --version
.venv/bin/telc-audio validate ../Deutsch\ A1\ TELC/01_Geburtstag/01_Geburtstag.md
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

On Windows, replace `.venv/bin/` with `.venv\Scripts\` and use PowerShell path
quoting.

Common setup failures:

- `lame is required but was not found in PATH`: install LAME, restart the
  terminal, and check `lame --version`.
- Python rejects the project version: check that the interpreter is 3.12+ and
  recreate `.venv` with that interpreter.
- TTS fails despite local tests passing: check internet access, DNS, firewall,
  or proxy settings for the Edge speech service.
- `--cover` is missing: create the cover before TTS and pass it explicitly to
  `build` or `build-all`.

## Commands

Create and verify the album cover before any TTS build. The cover is a required
parameter so every generated MP3 receives the same front-cover `APIC` frame.

```bash
telc-audio validate path/to/topic.md
telc-audio build path/to/topic.md --cover path/to/cover.jpg
telc-audio build-all "../Deutsch A1 TELC" --cover path/to/cover.jpg
telc-audio embed-cover "../Deutsch A1 TELC" --cover path/to/cover.jpg
```

Runnable Bash and PowerShell examples are available under `examples/`, including
scripts for individual topics and one-command generation of the whole folder.

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
Dein Vorname. {count=false}
:::
```

Supported line attributes:

- `pause="3s"` or `pause="300ms"`: override the block pause.
- `count=false`: exclude the line from answer word counting.
- `point=1` or `point="1,2"`: mark the TELC prompt points answered by the line.

The `answer` block must contain 35-45 counted words and cover points 1, 2, and
3. Sample signatures should use placeholders instead of a real learner name:
`Dein Vorname.` for informal letters and `Dein Vorname Familienname.` for
formal letters. `--cover` is required and embeds a JPEG or PNG as the
front-cover `APIC` frame. The generated MP3 includes title, artist, album,
language, APIC, USLT, and SYLT ID3 frames. TXT and USLT use the task, numbered
prompts, and final letter form; learner placeholders may appear there in
brackets such as `[Dein Vorname]`. LRC and SYLT remain synchronized with the
spoken lines and keep the natural spoken form without brackets. Apple Music and
Yandex Music do not guarantee display of embedded lyrics for personally
uploaded tracks; the `.txt` and `.lrc` files are kept as portable transcript
sources.
