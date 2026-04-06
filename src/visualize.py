from pathlib import Path
from typing import Union

import pandas as pd
import folium
from folium.plugins import HeatMap


def clean_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_popup_text(row: pd.Series) -> str:
    first_name = clean_value(row.get("First Name"))
    last_name = clean_value(row.get("Last Name"))
    member_id = clean_value(row.get("Member ID"))
    group_name = clean_value(row.get("Group Name"))
    division = clean_value(row.get("Division"))
    email = clean_value(row.get("Email"))
    phone = clean_value(row.get("Primary Phone"))
    address = clean_value(row.get("Address"))
    city = clean_value(row.get("City"))
    state = clean_value(row.get("State"))
    zipcode = clean_value(row.get("ZipCode"))

    full_name = f"{first_name} {last_name}".strip()
    full_address = ", ".join([x for x in [address, city, state, zipcode] if x])

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
    if full_address:
        lines.append(f"<b>Address:</b> {full_address}")

    return "<br>".join(lines) if lines else "No details available"


def visualize_file(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    radius: int = 35,
    blur: int = 25,
    zoom_start: int = 10,
):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(input_path)

    required_columns = ["Latitude", "Longitude"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    mapped_df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    if mapped_df.empty:
        raise ValueError("No valid Latitude/Longitude rows found.")

    center_lat = mapped_df["Latitude"].mean()
    center_lon = mapped_df["Longitude"].mean()

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="CartoDB positron",
    )

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

    HeatMap(
        heat_data,
        radius=radius,
        blur=blur,
        min_opacity=0.35,
        max_zoom=13,
    ).add_to(heat_layer)

    marker_layer.add_to(fmap)
    heat_layer.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    fmap.save(output_path)
    print(f"Map saved to: {output_path}")
