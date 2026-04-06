from pathlib import Path
from typing import Union
import time

import pandas as pd
from geopy.geocoders import Nominatim


def clean_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_full_address(row: pd.Series) -> str:
    parts = [
        clean_value(row.get("Address")),
        clean_value(row.get("City")),
        clean_value(row.get("State")),
        clean_value(row.get("ZipCode")),
    ]
    return ", ".join([part for part in parts if part])


def geocode_address(geolocator: Nominatim, address: str):
    if not address:
        return None, None

    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as exc:
        print(f"Failed to geocode '{address}': {exc}")

    return None, None


def geocode_file(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    sleep_seconds: float = 1.0,
):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(input_path)

    required_columns = ["Address", "City", "State", "ZipCode"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["FullAddress"] = df.apply(build_full_address, axis=1)

    if "Latitude" not in df.columns:
        df["Latitude"] = None
    if "Longitude" not in df.columns:
        df["Longitude"] = None

    geolocator = Nominatim(user_agent="member_address_mapper")

    missing_mask = df["Latitude"].isna() | df["Longitude"].isna()
    missing_rows = df[missing_mask]

    print(f"Found {len(df)} total rows")
    print(f"Need to geocode {len(missing_rows)} addresses")

    for idx, row in missing_rows.iterrows():
        address = row["FullAddress"]
        print(f"Geocoding row {idx + 1}: {address}")

        lat, lon = geocode_address(geolocator, address)
        df.at[idx, "Latitude"] = lat
        df.at[idx, "Longitude"] = lon

        time.sleep(sleep_seconds)

    df.to_excel(output_path, index=False)
    print(f"Geocoded file saved to: {output_path}")
