import argparse
import sys
from pathlib import Path

from .generator import build_topic_sync, embed_cover, update_id3_metadata
from .parser import ScenarioError, parse_scenario


def discover_scenarios(root: Path) -> list[Path]:
    scenarios = []
    for path in root.rglob("*.md"):
        if "_prototype" in path.parts:
            continue
        try:
            with path.open(encoding="utf-8") as source:
                first_line = source.readline().strip()
        except OSError:
            continue
        if first_line == "+++":
            scenarios.append(path)
    return sorted(scenarios)


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


def retag_metadata(root: Path) -> None:
    scenarios = discover_scenarios(root)
    if not scenarios:
        raise ScenarioError(f"No Markdown scenarios found under {root}")
    updated = 0
    for scenario in scenarios:
        topic = parse_scenario(scenario)
        mp3_path = scenario.parent / f"{topic.output_name}.mp3"
        if not mp3_path.is_file():
            raise RuntimeError(f"Missing MP3 for {scenario}: {mp3_path}")
        update_id3_metadata(mp3_path, topic)
        updated += 1
        print(f"Updated metadata: {mp3_path}")
    print(f"Updated metadata for {updated} MP3 files")


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
    retag_parser = commands.add_parser("retag-metadata")
    retag_parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            validate(args.scenario)
        elif args.command == "build":
            build(args.scenario, args.cover, args.output_dir)
        elif args.command == "build-all":
            scenarios = discover_scenarios(args.root)
            if not scenarios:
                raise ScenarioError(f"No Markdown scenarios found under {args.root}")
            for scenario in scenarios:
                build(scenario, args.cover)
            print(f"Built {len(scenarios)} scenarios")
        elif args.command == "retag-metadata":
            retag_metadata(args.root)
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
