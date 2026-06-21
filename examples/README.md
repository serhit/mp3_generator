# Examples

This directory contains one informal and one formal TELC A1 scenario. Each
topic directory intentionally contains only the editable Markdown source and
the generated MP3. The shared cover is passed to the CLI before TTS and embedded
as the ID3 front-cover `APIC` frame.

## Bash

Generate the two topics individually:

```bash
./examples/build-examples.sh
```

Generate every structured Markdown scenario under `examples/` in one command:

```bash
./examples/build-all-examples.sh
```

## PowerShell

Generate the two topics individually:

```powershell
.\examples\build-examples.ps1
```

Generate the entire examples folder at once:

```powershell
.\examples\build-all-examples.ps1
```

Create the project virtual environment and install the package first. `lame`
must also be available on `PATH`.
