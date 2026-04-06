import sys
import time
from pathlib import Path

import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim


OUTPUT_DIR = Path("output")
CACHE_FILE = OUTPUT_DIR / "geocode_cache.csv"


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


def build_popup_text(row: pd.Series) -> str:
    first_name = clean_value(row.get("First Name"))
    last_name = clean_value(row.get("Last Name"))
    member_id = clean_value(row.get("Member ID"))
    group_name = clean_value(row.get("Group Name"))
    division = clean_value(row.get("Division"))
    email = clean_value(row.get("Email"))
    phone = clean_value(row.get("Primary Phone"))
    address = clean_value(row.get("FullAddress"))

    full_name = f"{first_name} {last_name}".strip()

    lines = []
    if full_name:
        lines.append(f"<b>Name:</b> {full_name}")
    if member_id:
        lines.append(f"<b>Member ID:</b> {member_id}")
    if group_name:
        lines.append(f"<b>Group:</b> {group_name}")
    if division:
        lines.append(f"<b>Division:</b> {division}")
    if email:
        lines.append(f"<b>Email:</b> {email}")
    if phone:
        lines.append(f"<b>Phone:</b> {phone}")
    if address:
        lines.append(f"<b>Address:</b> {address}")

    return "<br>".join(lines) if lines else "No details available"


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


def load_cache(cache_file: Path) -> pd.DataFrame:
    if cache_file.exists():
        try:
            cache_df = pd.read_csv(cache_file)
            needed_cols = {"FullAddress", "Latitude", "Longitude"}
            if needed_cols.issubset(cache_df.columns):
                return cache_df
        except Exception as exc:
            print(f"Could not read cache file: {exc}")

    return pd.DataFrame(columns=["FullAddress", "Latitude", "Longitude"])


def save_cache(df: pd.DataFrame, cache_file: Path):
    cache_df = df[["FullAddress", "Latitude", "Longitude"]].drop_duplicates()
    cache_df.to_csv(cache_file, index=False)


def get_input_file() -> Path:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python members.py data/file_name.xlsx")

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        raise FileNotFoundError(f"Excel file not found: {input_path}")

    return input_path


def main():
    input_path = get_input_file()
    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / f"{input_path.stem}_map.html"

    df = pd.read_excel(input_path)

    required_columns = ["Address", "City", "State", "ZipCode"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["FullAddress"] = df.apply(build_full_address, axis=1)

    cache_df = load_cache(CACHE_FILE)
    df = df.merge(cache_df, on="FullAddress", how="left")

    if "Latitude" not in df.columns:
        df["Latitude"] = None
    if "Longitude" not in df.columns:
        df["Longitude"] = None

    geolocator = Nominatim(user_agent="member_address_mapper")

    missing_location_mask = df["Latitude"].isna() | df["Longitude"].isna()
    missing_rows = df[missing_location_mask]

    print(f"Found {len(df)} total rows")
    print(f"Need to geocode {len(missing_rows)} addresses")

    for idx, row in missing_rows.iterrows():
        address = row["FullAddress"]
        print(f"Geocoding row {idx + 1}: {address}")

        lat, lon = geocode_address(geolocator, address)
        df.at[idx, "Latitude"] = lat
        df.at[idx, "Longitude"] = lon

        time.sleep(1)

    save_cache(df, CACHE_FILE)

    mapped_df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    if mapped_df.empty:
        raise ValueError("No valid addresses were geocoded.")

    center_lat = mapped_df["Latitude"].mean()
    center_lon = mapped_df["Longitude"].mean()

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    marker_layer = folium.FeatureGroup(name="Pin Markers", show=True)
    heat_layer = folium.FeatureGroup(name="Heat Map", show=False)

    for _, row in mapped_df.iterrows():
        popup_html = build_popup_text(row)
        tooltip_name = f"{clean_value(row.get('First Name'))} {clean_value(row.get('Last Name'))}".strip()

        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=tooltip_name if tooltip_name else None,
        ).add_to(marker_layer)

    heat_data = mapped_df[["Latitude", "Longitude"]].values.tolist()
    HeatMap(heat_data, radius=15, blur=20).add_to(heat_layer)

    marker_layer.add_to(fmap)
    heat_layer.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    fmap.save(output_file)

    print(f"Map saved to: {output_file}")
    print(f"Geocode cache saved to: {CACHE_FILE}")
    print(f"Mapped {len(mapped_df)} addresses successfully")


if __name__ == "__main__":
    main()
