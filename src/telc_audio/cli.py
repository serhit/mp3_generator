import argparse
import sys
from pathlib import Path

from .generator import build_topic_sync, embed_cover
from .parser import ScenarioError, parse_scenario


def validate(path: Path) -> None:
    topic = parse_scenario(path)
    print(f"OK: {path} ({len(topic.blocks)} audio blocks)")


def build(
    path: Path,
    cover_path: Path,
    output_dir: Path | None = None,
) -> None:
    topic = parse_scenario(path)
    outputs = build_topic_sync(topic, cover_path, output_dir)
    print(f"Built: {path}")
    for output in outputs:
        print(f"  {output}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telc-audio")
    commands = parser.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("scenario", type=Path)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("scenario", type=Path)
    build_parser.add_argument("--output-dir", type=Path)
    build_parser.add_argument("--cover", type=Path, required=True)
    build_all_parser = commands.add_parser("build-all")
    build_all_parser.add_argument("root", type=Path)
    build_all_parser.add_argument("--cover", type=Path, required=True)
    cover_parser = commands.add_parser("embed-cover")
    cover_parser.add_argument("target", type=Path)
    cover_parser.add_argument("--cover", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            validate(args.scenario)
        elif args.command == "build":
            build(args.scenario, args.cover, args.output_dir)
        elif args.command == "build-all":
            scenarios = sorted(
                path for path in args.root.rglob("*.md") if "_prototype" not in path.parts
            )
            if not scenarios:
                raise ScenarioError(f"No Markdown scenarios found under {args.root}")
            for scenario in scenarios:
                build(scenario, args.cover)
            print(f"Built {len(scenarios)} scenarios")
        else:
            if args.target.is_file():
                mp3_files = [args.target]
            else:
                mp3_files = sorted(
                    path
                    for path in args.target.rglob("*.mp3")
                    if "_prototype" not in path.parts
                )
            if not mp3_files:
                raise RuntimeError(f"No MP3 files found under {args.target}")
            for mp3_file in mp3_files:
                embed_cover(mp3_file, args.cover)
                print(f"Embedded cover: {mp3_file}")
            print(f"Updated {len(mp3_files)} MP3 files")
    except (OSError, RuntimeError, ScenarioError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
