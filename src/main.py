import argparse
from pathlib import Path

from geocode import geocode_file
from visualize import visualize_file


def main():
    parser = argparse.ArgumentParser(
        description="Geocode member addresses and/or visualize them on a map."
    )

    parser.add_argument(
        "input_file",
        help="Input Excel file path, for example data/members.xlsx",
    )

    parser.add_argument(
        "--mode",
        choices=["geocode", "visualize", "both"],
        default="both",
        help="Choose whether to geocode, visualize, or do both.",
    )

    parser.add_argument(
        "--geocoded-file",
        default=None,
        help="Path to save or read the geocoded Excel file.",
    )

    parser.add_argument(
        "--map-file",
        default=None,
        help="Path to save the HTML map file.",
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=35,
        help="Heatmap radius.",
    )

    parser.add_argument(
        "--blur",
        type=int,
        default=25,
        help="Heatmap blur.",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to wait between geocoding requests.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    default_geocoded = Path("output") / f"{input_path.stem}_geocoded.xlsx"
    default_map = Path("output") / f"{input_path.stem}_map.html"

    geocoded_file = Path(args.geocoded_file) if args.geocoded_file else default_geocoded
    map_file = Path(args.map_file) if args.map_file else default_map

    if args.mode == "geocode":
        geocode_file(
            input_file=input_path,
            output_file=geocoded_file,
            sleep_seconds=args.sleep,
        )

    elif args.mode == "visualize":
        visualize_file(
            input_file=input_path,
            output_file=map_file,
            radius=args.radius,
            blur=args.blur,
        )

    elif args.mode == "both":
        geocode_file(
            input_file=input_path,
            output_file=geocoded_file,
            sleep_seconds=args.sleep,
        )
        visualize_file(
            input_file=geocoded_file,
            output_file=map_file,
            radius=args.radius,
            blur=args.blur,
        )


if __name__ == "__main__":
    main()
