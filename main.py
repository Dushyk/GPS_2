import flet as ft
from flet import *
import flet.map as map
import math
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.ops import unary_union
import json
import uuid
import os
import socket
import threading
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

# Словник для роботи з даними вводу
data = {"type": "FeatureCollection", "features": []}
# Словник для збереження усієї геометрії
json_exp = {"type": "FeatureCollection", "features": []}

buffer_value = []
# Посилання на карти підложки
url1 = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
url2 = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
# HOT OSM http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png
# CartoDB Dark Matter https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png
# https://{s}.tile.thunderforest.com/cycle/{z}/{x}/{y}.png
# Openstreet https://tile.openstreetmap.org/{z}/{x}/{y}.png
# OpenTopoMap https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png
# CartoDB Positron https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png

# Константи
a = 6378137  # Semi-major axis in meters
f = 1 / 298.257223563  # Flattening
e2 = 2 * f - f ** 2  # Eccentricity squared
k0 = 0.9996  # Scale factor


def get_local_ip():
    # Метод створення ip локального серверу
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# Виклик методу для отримання ip локального серверу
LOCAL_IP = get_local_ip()

# Create FastAPI app
app = FastAPI()

# Directory for storing temp files
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)


# Define API endpoint for file download
@app.get("/download/geojson")
def download_geojson(json_exp: str = Query(...), file_name_input: str = Query("output")):
    # Метод для завантаження результатів у geojson
    file_name = file_name_input.strip() or "output"
    file_path = os.path.join(TEMP_DIR, f"{file_name}.geojson")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_exp)
    except Exception as e:
        return {"error": str(e)}

    return FileResponse(file_path, media_type="application/json", filename=f"{file_name}.geojson")


def start_server():
    # Метод створення локального серверу для завантаження файлу
    uvicorn.run(app, host="0.0.0.0", port=8000)


def main(page: ft.Page):
    page.title = "Форми"
    BG = "#79751D"
    FG = "#c7d3d6"
    main_controls_pages = []
    current_main_page_index = 0
    display_area = ft.Column(visible=False)
    ratio_text = ft.Text("0/0", size=16, weight=ft.FontWeight.BOLD)
    latitude_text = ft.Text(value="0")
    longitude_text = ft.Text(value="0")
    page.padding = 0
    current_url = url1
    tile_layer = map.TileLayer(url_template=current_url)

    page.window.resizable = True

    gl = ft.Geolocator(
        location_settings=ft.GeolocatorSettings(
            accuracy=ft.GeolocatorPositionAccuracy.BEST
        ),
        on_position_change=lambda e: None,
        on_error=lambda e: page.add(ft.Text(f"Error: {e.data}")),
    )
    page.overlay.append(gl)

    settings_dlg = lambda handler: ft.AlertDialog(
        adaptive=True,
        title=ft.Text("Opening Location Settings..."),
        content=ft.Text(
            "Вас буде направлено до налаштувань геолокації/додатка"
            "Будь-ласка надайте програмі доступ до геолокації."
        ),
        actions=[ft.TextButton(text="Take me there", on_click=handler)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    def on_resize(e):
        container.width = page.width
        container.height = page.height
        page_1.width = page.width
        page_1.height = page.height
        page_contents.width = page.width * 0.98
        buffer_name.width = page.width * 0.98
        enter_part_yes.width = page.width * 0.98
        pointinptf.width = page.width * 0.98
        formation_pages_controls.width = page.width * 0.98
        file_name_input.width = page.width * 0.98
        map_card.width = page.width * 0.98
        page.update()
        page_contents.update()

    page.on_resized = on_resize

    def showhideimputway(e):
        choice = e.control.value
        if choice == "yes_catalog":
            enter_part_yes.visible = True
            enter_part_yes_txt.visible = True
            # formation_pages_controls.visible = False
            display_area.visible = False
            page.update()
        if choice == "no_catalog":
            # formation_pages_controls.visible = True
            enter_part_yes.visible = False
            enter_part_yes_txt.visible = False
            display_area.visible = True
            page.update()

    def handle_checkbox_change(changed_checkbox, expantile_to_show, other_checkboxes_and_expantiles):
        if changed_checkbox.value:
            # Uncheck other checkboxes and hide their containers (if any)
            for checkbox, expantile in other_checkboxes_and_expantiles:
                checkbox.value = False
                if expantile:
                    expantile.visible = False
            # Show the corresponding container (if exists)
            if expantile_to_show:
                expantile_to_show.visible = True
        page.update()

    def clearfield(e):
        pointinptf.value = ""
        page.update()

    def add_point_to_dict(point_number, latitudev, longitudev):
        # Метод для запису додавання вершин геометрії з готового катологу у data і json_exp
        feature = {"type": "Feature", "geometry": {
            "type": "Point",
            "coordinates": [latitudev, longitudev]
        }, "properties": {"point_number": point_number}}
        data["features"].append(feature)
        json_exp["features"].append(feature)

    def process_input(e):
        # Метод який чистить тимчасовий словник і опрацьовує ввід у полі
        data["features"].clear()
        input_text = pointinptf.value
        for line in input_text.strip().split('\n'):
            parts = line.split()
            point_number = int(parts[0])
            latitudev = float(parts[1].replace(',', '.'))
            longitudev = float(parts[2].replace(',', '.'))
            add_point_to_dict(point_number, latitudev, longitudev)
        page.update()

    def add_point_data_to_map(e):
        # Метод, який будує точки з вводу і буфери навколо них
        process_input(e)
        to_utm_conversion_results = []
        for feature in data["features"]:
            if feature["geometry"]["type"] == "Point":
                coordinates = feature["geometry"]["coordinates"]
                latitude, longitude = coordinates
                point_number = feature["properties"]["point_number"]
                # Початок блоку перерахунку
                utm_result = calculate_to_utm(point_number, latitude, longitude)
                to_utm_conversion_results.append(utm_result)
                # Кінець блоку перерахунку
                points_layer.markers.append(
                    map.Marker(
                        content=Stack(
                            controls=[
                                Container(
                                    margin=-10,
                                    padding=-10,
                                    alignment=ft.alignment.center,
                                    bgcolor=ft.Colors.AMBER,
                                    border=border.all(color="black"),
                                    width=20,
                                    height=20,
                                    border_radius=10,
                                ),
                                Text(
                                    point_number,
                                    offset=ft.Offset(2, 0),
                                    weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.alignment.center,
                        ),
                        coordinates=map.MapLatitudeLongitude(latitude, longitude),
                    )
                )
        page.update()
        build_point_buffer(to_utm_conversion_results)
        return to_utm_conversion_results

    def get_polygon_coordinates(data):
        # Метод, який будує полігони з вводу
        polygon_coords = []
        geojson_coords = []
        for feature in data["features"]:
            if feature["geometry"]["type"] == "Point":
                coordinates = feature["geometry"]["coordinates"]
                latitude, longitude = coordinates
                polygon_coords.append(map.MapLatitudeLongitude(latitude, longitude))
                geojson_coords.append([longitude, latitude])

        polygon_global_id = f"{{{str(uuid.uuid4()).upper()}}}"

        if len(polygon_coords) >= 3:
            polygon_coords.append(polygon_coords[0])
            geojson_coords.append(geojson_coords[0])

            feature_obj = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": geojson_coords
                },
                "properties": {
                    "obj_group": "output",
                    "obj_name": buffer_name.value,
                    "buffer_value": "none",
                    "buffer_element": "none",
                    "buffer_type": "none",
                    "class": "polygons",
                    "global_id": polygon_global_id,
                    "parent_id": "default",
                }
            }

        json_exp["features"].append(feature_obj)

        for idx, (lon, lat) in enumerate(geojson_coords[:-1]):
            vertex_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": {
                    "obj_group": "input",
                    "obj_name": "ST" if idx == 0 else f"P{idx}",
                    "buffer_value": "none",
                    "buffer_element": "none",
                    "buffer_type": "none",
                    "class": "polygon_points",
                    "global_id": f"{{{str(uuid.uuid4()).upper()}}}",
                    "parent_id": polygon_global_id,
                }
            }
            json_exp["features"].append(vertex_feature)

        return polygon_coords

    def add_polygon_data_to_map(e):
        # Метод, який виводить розраховані полігони на карту
        process_input(e)
        polygon_coords = get_polygon_coordinates(data)

        if len(polygon_coords) >= 4:
            polygons_layer.polygons.append(
                map.PolygonMarker(
                    label=buffer_name.value,
                    label_text_style=ft.TextStyle(
                        color=ft.Colors.BLACK,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                    ),
                    color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE),
                    border_color="black",
                    border_stroke_width=2,
                    coordinates=polygon_coords,
                )
            )
        page.update()

    def get_polyline_coordinates(data):
        # Метод, який будує полілінії з вводу
        polyline_coords = []
        geojson_coords = []
        to_utm_conversion_results = []
        for feature in data["features"]:
            if feature["geometry"]["type"] == "Point":
                coordinates = feature["geometry"]["coordinates"]
                latitude, longitude = coordinates
                polyline_coords.append(map.MapLatitudeLongitude(latitude, longitude))
                geojson_coords.append([longitude, latitude])
                point_number = feature["properties"]["point_number"]
                # Початок блоку перерахунку
                utm_result = calculate_to_utm(point_number, latitude, longitude)
                to_utm_conversion_results.append(utm_result)

        polygon_global_id = f"{{{str(uuid.uuid4()).upper()}}}"

        feature_obj = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": geojson_coords
            },
            "properties": {
                "obj_group": "constructed",
                "obj_name": "none",
                "buffer_value": "none",
                "buffer_element": "none",
                "buffer_type": "none",
                "class": "default",
                "global_id": polygon_global_id,
                "parent_id": "default",
            }
        }
        json_exp["features"].append(feature_obj)

        return polyline_coords, to_utm_conversion_results

    def add_polyline_data_to_map(e):
        # Метод, який виводить розраховані полігони на карту та буфери навколо них
        process_input(e)
        polyline_coords, to_utm_conversion_results = get_polyline_coordinates(data)
        if len(polyline_coords) >= 2:
            polylines_layer.polylines.append(
                map.PolylineMarker(
                    border_stroke_width=3,
                    border_color=ft.Colors.RED,
                    color="red",
                    coordinates=polyline_coords,
                )
            )
        build_line_buffer(to_utm_conversion_results)
        page.update()

    def calculate_to_utm(point_number, latitude, longitude):
        # Перерахунок вводу градусних координат у UTM

        # Convert latitude and longitude to radians
        phi = math.radians(latitude)
        lam = math.radians(longitude)

        # Calculate the UTM zone
        zone = int((longitude + 180) / 6) + 1

        hemisphere = "N" if latitude >= 0 else "S"

        # Calculate central meridian of the zone
        lambda0 = math.radians((zone - 1) * 6 - 180 + 3)

        # Auxiliary values
        nu = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
        rho = a * (1 - e2) / (1 - e2 * math.sin(phi) ** 2) ** 1.5
        eta2 = nu / rho - 1

        # Meridional arc (B(phi))
        A = 1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256
        B = 3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024
        C = 15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024
        D = 35 * e2 ** 3 / 3072

        M = a * (A * phi - B * math.sin(2 * phi) + C * math.sin(4 * phi) - D * math.sin(6 * phi))

        # Transverse Mercator projection calculations
        delta_lambda = lam - lambda0
        T = math.tan(phi) ** 2
        C = eta2 * math.cos(phi) ** 2
        A = math.cos(phi) * delta_lambda

        # Easting (x)
        x = k0 * nu * (A + (1 - T + C) * A ** 3 / 6 +
                       (5 - 18 * T + T ** 2 + 72 * C - 58 * eta2) * A ** 5 / 120) + 500000

        # Northing (y)
        y = k0 * (M + nu * math.tan(phi) * (A ** 2 / 2 +
                                            (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 +
                                            (61 - 58 * T + T ** 2 + 600 * C - 330 * eta2) * A ** 6 / 720))

        # Adjust for southern hemisphere
        if latitude < 0:
            y += 10000000

        return [point_number, zone, hemisphere, x, y]

    def calculate_square_vertices(center_x, center_y, buffer_width):
        # Розрахунок координат вершин квадратного буферу навколо точки
        r = buffer_width
        square_coords = [
            (center_x - r, center_y - r),  # Bottom-left corner
            (center_x - r, center_y + r),  # Top-left corner
            (center_x + r, center_y + r),  # Top-right corner
            (center_x + r, center_y - r),  # Bottom-right corner
            (center_x - r, center_y - r)  # Close the square
        ]
        return square_coords

    def utm_to_wgs84(zone_number, lat_band, easting, northing):
        # Перерахунок UTM у WGS

        k0 = 0.9996
        E0 = 500000  # Easting of the central meridian
        N0 = 0  # Northing (false northing for northern hemisphere)

        # Calculate the meridian central longitude (λ0)
        lambda0 = math.radians((zone_number - 1) * 6 - 180 + 3)

        # Calculate the footpoint latitude
        M = (northing - N0) / k0  # Meridional arc
        mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))

        # Calculate the latitude and longitude
        e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
        J1 = (3 * e1 / 2 - 27 * e1 ** 3 / 32)
        J2 = (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32)
        J3 = (151 * e1 ** 3 / 96)
        J4 = (1097 * e1 ** 4 / 512)

        fp = mu + J1 * math.sin(2 * mu) + J2 * math.sin(4 * mu) + J3 * math.sin(6 * mu) + J4 * math.sin(8 * mu)
        sin_fp = math.sin(fp)
        cos_fp = math.cos(fp)
        tan_fp = math.tan(fp)

        # Calculate the radius of curvature
        e2_prime = e2 / (1 - e2)
        N = a / math.sqrt(1 - e2 * sin_fp ** 2)
        T = tan_fp ** 2
        C = e2_prime * cos_fp ** 2
        R = a * (1 - e2) / (1 - e2 * sin_fp ** 2) ** (3 / 2)
        D = (easting - E0) / (N * k0)

        lat = fp - (N * tan_fp / R) * (D ** 2 / 2 - (5 + 3 * T + 10 * C - 4 * C ** 2 - 9 * e2_prime) * D ** 4 / 24 + (
                    61 + 90 * T + 298 * C + 45 * T ** 2 - 252 * e2_prime) * D ** 6 / 720)
        lon = lambda0 + (D - (1 + 2 * T + C) * D ** 3 / 6 + (
                    5 - 2 * C + 28 * T - 3 * C ** 2 + 8 * e2_prime + 24 * T ** 2) * D ** 5 / 120) / cos_fp

        lat_deg = math.degrees(lat)
        lon_deg = math.degrees(lon)

        return lat_deg, lon_deg

    def process_points_pointbuff(to_utm_conversion_results, buffer_width):
        # Приймання ширини буфера та передача оброблених даних точкового буфера
        output = []
        for point in to_utm_conversion_results:
            point_number, zone, hemisphere, easting, northing = point
            square_coords = calculate_square_vertices(easting, northing, buffer_width)
            square_with_zone_hemisphere = [
                (zone, hemisphere, easting, northing) for easting, northing in square_coords
            ]
            output.append((point_number, square_with_zone_hemisphere))
        return output

    def build_point_buffer(to_utm_conversion_results):
        # Побудова точкового буфера, збереення в json_exp і відображення на карті
        list_tile = point_expantile.controls[0]
        buffer_width_field = list_tile.subtitle
        buffer_width = float(buffer_width_field.value)
        # Process points and calculate squares
        utm_buffering_coords = process_points_pointbuff(to_utm_conversion_results, buffer_width)
        wgs_buffers_coordinates = []
        for point_number, values in utm_buffering_coords:
            polygon_coords = []
            json_exp_polygon_coords = []
            for value in values:
                latitude, longitude = utm_to_wgs84(value[0], value[1], value[2], value[3])
                polygon_coords.append(map.MapLatitudeLongitude(latitude=latitude, longitude=longitude))
                json_exp_polygon_coords.append([longitude, latitude])

            polygon_global_id = f"{{{str(uuid.uuid4()).upper()}}}"

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": json_exp_polygon_coords,
                },
                "properties": {
                    "obj_group": "output",
                    "obj_name": buffer_name.value,
                    "buffer_value": "none",
                    "buffer_element": "none",
                    "buffer_type": "none",
                    "class": "polygons",
                    "global_id": polygon_global_id,
                    "parent_id": "default",
                }
            }
            json_exp["features"].append(feature)
            wgs_buffers_coordinates.append(polygon_coords)
            for idx, (lon, lat) in enumerate(json_exp_polygon_coords[:-1]):
                vertex_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                    "properties": {
                        "obj_group": "input",
                        "obj_name": "ST" if idx == 0 else f"P{idx}",
                        "buffer_value": "none",
                        "buffer_element": "none",
                        "buffer_type": "none",
                        "class": "polygon_points",
                        "global_id": f"{{{str(uuid.uuid4()).upper()}}}",
                        "parent_id": polygon_global_id,
                    }
                }
                json_exp["features"].append(vertex_feature)

        for polygon_coords in wgs_buffers_coordinates:
            if len(wgs_buffers_coordinates) >= 1:
                buffer_polygons_layer.polygons.append(
                    map.PolygonMarker(
                        label=buffer_name.value,
                        label_text_style=ft.TextStyle(
                            color=ft.Colors.BLACK,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                        ),
                        color=ft.Colors.with_opacity(0.3, ft.Colors.GREEN),
                        border_color="black",
                        border_stroke_width=2,
                        coordinates=polygon_coords,
                    )
                )

        page.update()

    def on_round_choice(e):
        # Вибір круглого буфера
        list_tile = line_expantile.controls[3]
        buffer_build_choice = list_tile.subtitle
        line_expantile.controls[3].visible = e.control.value == "Rounded buffer zone"
        line_expantile.update()

    def process_points_linebuff(to_utm_conversion_results, buffer_width, round_severity, buffer_build_choice):
        # Extract original (x, y) coordinates
        line_coords = [(point[3], point[4]) for point in to_utm_conversion_results]

        # Create the LineString
        line = LineString(line_coords)

        # Define buffer style
        if buffer_build_choice == "Rounded buffer zone":
            cap_style = "round"
            join_style = "round"
        elif buffer_build_choice == "Flat strip":
            cap_style = "flat"
            join_style = "mitre"
            round_severity = 0

        # Generate buffer polygon
        buffer = line.buffer(
            distance=buffer_width,
            quad_segs=round_severity / 2 if round_severity else 0,
            cap_style=cap_style,
            join_style=join_style,
        )

        # Adjust and reorder buffer coordinates
        buffer_coords = list(buffer.exterior.coords)
        reordered_coords = buffer_coords[-2:] + buffer_coords[:-2]
        reordered_coords.append(reordered_coords[0])
        buffer_polygon = Polygon(reordered_coords)

        # Assign UTM zones dynamically based on longitude
        buffer_with_zones = []
        for x, y in buffer_polygon.exterior.coords:
            # Convert UTM back to WGS84 to determine correct longitude
            lat, lon = utm_to_wgs84(to_utm_conversion_results[0][1], to_utm_conversion_results[0][2], x, y)

            # Determine correct UTM zone for this point
            zone = int((lon + 180) / 6) + 1
            print(zone)
            hemisphere = "N" if lat >= 0 else "S"

            buffer_with_zones.append((zone, hemisphere, x, y))

        return buffer_with_zones  # Returns [(zone, hemisphere, x, y)]

    def convert_buffer_to_wgs84(buffer_polygons, to_utm_conversion_results):
        zone, hemisphere = to_utm_conversion_results[0][1:3]
        all_coords = []
        print(buffer_polygons)

        for polygon in buffer_polygons:
            coords = [
                (zone, hemisphere, *utm_to_wgs84(zone, hemisphere, x, y))
                for x, y, *_ in polygon
            ]
            all_coords.append(coords)

        return all_coords

    def build_line_buffer(to_utm_conversion_results):
        buffer_width_list_tile = line_expantile.controls[0]
        buffer_width_field = buffer_width_list_tile.subtitle
        buffer_width = float(buffer_width_field.value)
        buffer_creator_list_tile = line_expantile.controls[1]
        buffer_creator_field = buffer_creator_list_tile.subtitle
        buffer_creator = buffer_creator_field.value
        buffer_choice_list_tile = line_expantile.controls[2]
        buffer_build_choice_field = buffer_choice_list_tile.subtitle
        buffer_build_choice = buffer_build_choice_field.value
        round_severity = 0  # Default to None
        if buffer_build_choice == "Rounded buffer zone":
            round_severity_list_tile = line_expantile.controls[3]
            round_severity_field = round_severity_list_tile.subtitle
            round_severity = int(round_severity_field.value)

        # buffer_polygon, zone_map = process_points_linebuff(to_utm_conversion_results, buffer_width, round_severity, buffer_build_choice)
        buffer_with_zones = process_points_linebuff(to_utm_conversion_results, buffer_width, round_severity,
                                                    buffer_build_choice)
        print(buffer_with_zones)
        # wgs_buffers_coordinates = convert_buffer_to_wgs84(buffer_polygon, zone_map, utm_to_wgs84)
        wgs_buffers_coordinates = convert_buffer_to_wgs84(buffer_with_zones, to_utm_conversion_results)

        polygon_global_id = f"{{{str(uuid.uuid4()).upper()}}}"

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[lon, lat] for _, _, lat, lon in wgs_buffers_coordinates]
            },
            "properties": {
                "obj_group": "output",
                "obj_name": buffer_name.value,
                "buffer_value": buffer_width,
                "buffer_element": buffer_creator,
                "buffer_type": buffer_build_choice,
                "class": "polygons",
                "global_id": polygon_global_id,
                "parent_id": "default",
            }
        }
        json_exp["features"].append(feature)

        for idx, (_, _, lat, lon) in enumerate(wgs_buffers_coordinates[:-1]):
            vertex_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": {
                    "obj_group": "input",
                    "obj_name": "ST" if idx == 0 else f"P{idx}",
                    "buffer_value": "none",
                    "buffer_element": "none",
                    "buffer_type": "none",
                    "class": "polygon_points",
                    "global_id": f"{{{str(uuid.uuid4()).upper()}}}",
                    "parent_id": polygon_global_id,
                }
            }
            json_exp["features"].append(vertex_feature)

        if len(wgs_buffers_coordinates) >= 3:
            buffer_polygons_layer.polygons.append(
                map.PolygonMarker(
                    label=buffer_name.value,
                    label_text_style=ft.TextStyle(
                        color=ft.Colors.BLACK,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                    ),
                    color=ft.Colors.with_opacity(0.3, ft.Colors.RED),
                    border_color="black",
                    border_stroke_width=2,
                    coordinates=[
                        map.MapLatitudeLongitude(latitude=lat, longitude=lon)
                        for _, _, lat, lon in wgs_buffers_coordinates
                    ],
                )
            )

    # Update the page to reflect changes
    page.update()

    def update_ratio_text():
        if main_controls_pages:
            ratio_text.value = f"{current_main_page_index + 1}/{len(main_controls_pages)}"
        else:
            ratio_text.value = "0/0"
        ratio_text.update()

    def update_display():
        """Оновлення відображення поточної `main_controls_page`"""
        display_area.controls.clear()
        if main_controls_pages:
            display_area.controls.append(main_controls_pages[current_main_page_index])
        else:
            display_area.controls.append(ft.Text("Немає сторінок", bgcolor="#e7f5ae"))
        display_area.update()
        update_ratio_text()

    async def handle_get_current_position(e):
        p = await gl.get_current_position_async()
        latitude_text.value = str(p.latitude)
        print(latitude_text.value)
        longitude_text.value = str(p.longitude)
        print(longitude_text.value)
        page.update()

    async def handle_open_app_settings(e):
        p = await gl.open_app_settings_async()
        page.close(app_settings_dlg)
        page.add(ft.Text(f"open_app_settings: {p}"))

    app_settings_dlg = settings_dlg(handle_open_app_settings)

    def create_content_column(page_number):
        utm_part = ft.ExpansionTile(
            title=ft.Text("UTM Coordinates", weight=ft.FontWeight.BOLD),
            affinity=ft.TileAffinity.LEADING,
            initially_expanded=True,
            collapsed_text_color="black",
            text_color="black",
            visible=False,
            controls_padding=padding.only(bottom=10),
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(value='Enter Zone Number'),
                                zone_num := ft.Dropdown(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                    options=[
                                        ft.dropdown.Option("34"),
                                        ft.dropdown.Option("35"),
                                        ft.dropdown.Option("36"),
                                        ft.dropdown.Option("37"),
                                    ],
                                ),
                                ft.Text(value='Enter UTM Easting (x)'),
                                eastingf := ft.TextField(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    min_lines=1,
                                    max_lines=5,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                ),
                            ]
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(value='Select Zone Letter'),
                                zone_letter := ft.Dropdown(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                    options=[
                                        ft.dropdown.Option("North"),
                                        ft.dropdown.Option("South"),
                                    ],
                                ),
                                ft.Text(value='Enter UTM Northing (y)'),
                                northingf := ft.TextField(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    min_lines=1,
                                    max_lines=5,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                ),
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            ]
        )

        wgs_part = ft.ExpansionTile(
            title=ft.Text("WGS-84 Coordinates",
                          weight=ft.FontWeight.BOLD),
            affinity=ft.TileAffinity.LEADING,
            initially_expanded=True,
            collapsed_text_color="black",
            text_color="black",
            visible=False,
            controls_padding=padding.only(bottom=10),
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(value='Longitude'),
                                longf := ft.TextField(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    min_lines=1,
                                    max_lines=5,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                ),
                            ]
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(value='Latitude'),
                                latif := ft.TextField(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    min_lines=1,
                                    max_lines=5,
                                    width=page.width * 0.35,
                                    height=40,
                                    text_size=15,
                                ),
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            ]
        )

        def catalog_showhideimputway(e):
            choice = e.control.value
            if choice == "gpswayinput":
                utm_part.visible = False
                wgs_part.visible = False
                page.update()
            if choice == "utmwayinput":
                utm_part.visible = True
                wgs_part.visible = False
                page.update()
            if choice == "wgswayinput":
                utm_part.visible = False
                wgs_part.visible = True
                page.update()

        point_type_value = "startpoint" if page_number == 1 else "turnpoint"
        text_field_value = "SP" if page_number == 1 else f"TP{page_number - 1}"

        return ft.ExpansionTile(
            title=ft.Text(f"Catalog Formation", weight=ft.FontWeight.BOLD),
            affinity=ft.TileAffinity.LEADING,
            initially_expanded=True,
            collapsed_text_color="black",
            bgcolor="#e7f5ae",
            text_color="black",
            controls=[
                ft.Row(
                    [
                        ft.RadioGroup(
                            value=point_type_value,
                            content=ft.Column(
                                [
                                    ft.Text(f"Vertex {page_number}", weight=ft.FontWeight.BOLD),
                                    ft.Text(value="Point type"),
                                    ft.Radio(value="startpoint", label="Start point"),
                                    ft.Radio(value="turnpoint", label="Turn point"),
                                ],
                                spacing=0,
                            ),
                        ),
                        ft.RadioGroup(
                            content=ft.Column(
                                [
                                    ft.Text(value="Add coordinates manually?"),
                                    ft.Radio(value="gpswayinput", label="No"),
                                    ft.Radio(value="utmwayinput", label="UTM way"),
                                    ft.Radio(value="wgswayinput", label="WGS-84 way"),
                                ],
                                spacing=0,
                            ),
                            on_change=catalog_showhideimputway
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                ft.Divider(height=0, thickness=1, color="black"),
                utm_part,
                wgs_part,
                ft.ExpansionTile(
                    title=ft.Text("Point ID",
                                  weight=ft.FontWeight.BOLD),
                    affinity=ft.TileAffinity.LEADING,
                    initially_expanded=True,
                    collapsed_text_color="black",
                    text_color="black",
                    controls=[
                        ft.Text(
                            value='Point ID',
                            text_align=ft.TextAlign.LEFT
                        ),
                        ft.TextField(
                            bgcolor="white",
                            border_color="black",
                            color="black",
                            content_padding=10,
                            min_lines=1,
                            max_lines=5,
                            width=page.width * 0.35,
                            height=40,
                            text_size=15,
                            value=text_field_value,
                        ),
                    ],
                    expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Column([
                    ft.Text(value='Location'),
                    ft.Text(value='By default, the GNSS receiver or by selecting mark on the map'),
                ]),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(Icons.LOCATION_SEARCHING, color="black"),
                            padding=padding.only(top=5, bottom=10),
                            on_click=handle_get_current_position
                        ),
                        ft.Container(
                            content=ft.Icon(
                                Icons.MAP_OUTLINED,
                                color="black"
                            ),
                            on_click=handle_open_app_settings,
                            padding=padding.only(top=5, bottom=10)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY
                ),
                ft.ExpansionTile(
                    title=ft.Text(
                        "Coordinates calculated automatically",
                        weight=ft.FontWeight.BOLD
                    ),
                    affinity=ft.TileAffinity.LEADING,
                    initially_expanded=False,
                    collapsed_text_color="black",
                    text_color="black",
                    controls=[
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Column(
                                            [
                                                ft.Text(value='UTM Zone'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.30,
                                                    height=40,
                                                    text_size=15,
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(value='UTM X(easting)'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.30,
                                                    height=40,
                                                    text_size=15,
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(value='UTM Y(northing)'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.30,
                                                    height=40,
                                                    text_size=15,
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_EVENLY
                                ),
                                ft.Row(
                                    [
                                        ft.Column(
                                            [
                                                ft.Text(value='GPS data accuracy (m)'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.30,
                                                    height=40,
                                                    text_size=15,
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(value='Latitude'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.27,
                                                    height=40,
                                                    text_size=15,
                                                    value=latitude_text.value
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(value='Longitude'),
                                                ft.TextField(
                                                    bgcolor="white",
                                                    border_color="black",
                                                    color="black",
                                                    content_padding=10,
                                                    min_lines=1,
                                                    max_lines=5,
                                                    width=page.width * 0.27,
                                                    height=40,
                                                    text_size=15,
                                                    value=longitude_text.value
                                                ),
                                            ],
                                            horizontal_alignment='center'
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_EVENLY
                                )
                            ]
                        ),
                    ]
                ),
            ]
        )

    def create_main_controls_page(main_page_number):
        """Створює `main_controls_page` з власним `content_column_pages`"""

        content_column_pages = [create_content_column(1)]
        current_content_index = 0
        content_display = ft.Column([content_column_pages[0]])
        content_ratio_text = ft.Text("1/1", size=14, weight=ft.FontWeight.BOLD)

        def update_content_display():
            """Оновлення відображення `content_column_pages`"""
            content_display.controls.clear()
            if content_column_pages:
                content_display.controls.append(content_column_pages[current_content_index])
            else:
                content_display.controls.append(ft.Text("Немає сторінок контенту"))
            content_display.update()
            update_content_ratio()

        def update_content_ratio():
            """Оновлення індикатора поточної субсторінки"""
            if content_column_pages:
                content_ratio_text.value = f"{current_content_index + 1}/{len(content_column_pages)}"
            else:
                content_ratio_text.value = "0/0"
            content_ratio_text.update()

        def add_content_page(e):
            """Додає нову `content_column` сторінку"""
            nonlocal current_content_index
            new_page_number = len(content_column_pages) + 1
            content_column_pages.append(create_content_column(new_page_number))
            current_content_index = len(content_column_pages) - 1
            update_content_display()

        def remove_content_page(e):
            """Видаляє поточну `content_column` сторінку і оновлює номери"""
            nonlocal current_content_index
            if content_column_pages:
                content_column_pages.pop(current_content_index)
                for i in range(len(content_column_pages)):  # Перенумерація
                    content_column_pages[i] = create_content_column(i + 1)
                current_content_index = max(0, current_content_index - 1)
                update_content_display()

        def prev_content_page(e):
            """Перемикає на попередню `content_column` сторінку"""
            nonlocal current_content_index
            if content_column_pages:
                current_content_index = (current_content_index - 1) % len(content_column_pages)
                update_content_display()

        def next_content_page(e):
            """Перемикає на наступну `content_column` сторінку"""
            nonlocal current_content_index
            if content_column_pages:
                current_content_index = (current_content_index + 1) % len(content_column_pages)
                update_content_display()

        return ft.Column(
            [
                ft.Container(
                    content=(
                        ft.Column(
                            controls=[
                                enter_part_yes_txt,
                                enter_part_yes,
                                content_display,
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.Icons.ARROW_BACK,
                                            on_click=prev_content_page,
                                            icon_color="black",
                                            tooltip="Попередня сторінка"
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            on_click=remove_content_page,
                                            icon_color="black",
                                            tooltip="Видалити сторінку контенту"
                                        ),
                                        ft.Container(
                                            content=content_ratio_text,
                                            padding=padding.only(top=10, bottom=10),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.ADD,
                                            on_click=add_content_page,
                                            icon_color="black",
                                            tooltip="Додати сторінку контенту"
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.ARROW_FORWARD,
                                            on_click=next_content_page,
                                            icon_color="black",
                                            tooltip="Наступна сторінка"
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                                ),
                            ]
                        )
                    ),
                    bgcolor="#e7f5ae"
                )
            ]
        )

    def add_main_page(e):
        """Додає нову `main_controls_page`"""
        nonlocal current_main_page_index
        new_page = create_main_controls_page(len(main_controls_pages) + 1)
        main_controls_pages.append(new_page)
        current_main_page_index = len(main_controls_pages) - 1
        update_display()

    def remove_main_page(e):
        """Видаляє поточну `main_controls_page` і оновлює номери"""
        nonlocal current_main_page_index
        if main_controls_pages:
            main_controls_pages.pop(current_main_page_index)
            for i in range(len(main_controls_pages)):  # Перенумерація
                main_controls_pages[i] = create_main_controls_page(i + 1)
            current_main_page_index = max(0, current_main_page_index - 1)
            update_display()

    def next_main_page(e):
        """Перемикає на наступну `main_controls_page`"""
        nonlocal current_main_page_index
        if main_controls_pages:
            current_main_page_index = (current_main_page_index + 1) % len(main_controls_pages)
            update_display()

    def prev_main_page(e):
        """Перемикає на попередню `main_controls_page`"""
        nonlocal current_main_page_index
        if main_controls_pages:
            current_main_page_index = (current_main_page_index - 1) % len(main_controls_pages)
            update_display()

    def on_draw_button_click(e):
        if point_check.value:
            add_point_data_to_map(e)
        elif line_check.value:
            add_polyline_data_to_map(e)
        elif polygon_check.value:
            add_polygon_data_to_map(e)
        print(json_exp)

    def clear_map(e):
        buffer_polygons_layer.polygons = []
        polygons_layer.polygons = []
        polylines_layer.polylines = []
        points_layer.markers = []

        # Update each layer to apply changes
        buffer_polygons_layer.update()
        polygons_layer.update()
        polylines_layer.update()
        points_layer.update()
        page.update()

    def toggle_layer(e):
        nonlocal current_url
        current_url = url2 if current_url == url1 else url1
        new_tile_layer = map.TileLayer(url_template=current_url)
        map_card.layers = [new_tile_layer] + [layer for layer in map_card.layers if
                                              not isinstance(layer, map.TileLayer)]
        page.update()

    def download_file(_):
        file_name = file_name_input.value.strip()
        json_payload = json.dumps(json_exp, separators=(',', ':'), ensure_ascii=False)

        # Open browser to trigger download
        download_url = f"http://{LOCAL_IP}:8000/download/geojson?json_exp={json_payload}&file_name_input={file_name}"
        page.launch_url(download_url)

        page.update()

    page_contents = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(Icons.MENU),
                            padding=padding.only(top=10)
                        )
                    ]
                ),
                ft.Container(
                    bgcolor="#ffccbd",
                    content=(
                        ft.Column(
                            controls=[
                                ft.Divider(height=0, thickness=1, color="black"),
                                ft.Text(value='Enter polygon name'),
                                buffer_name := ft.TextField(
                                    bgcolor="white",
                                    border_color="black",
                                    color="black",
                                    content_padding=10,
                                    min_lines=1,
                                    max_lines=5,
                                    width=page.width * 0.98,
                                    height=40,
                                    text_size=15,
                                ),
                                ft.Divider(height=0, thickness=1, color="black"),
                                ft.Text(value='Add ready coordinates catalog?'),
                                ft.RadioGroup(
                                    content=ft.Row(
                                        [
                                            ft.Radio(value="no_catalog", label="No"),
                                            ft.Radio(value="yes_catalog",
                                                     label="Prepared catalog"),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_EVENLY
                                    ),
                                    on_change=showhideimputway
                                ),
                                enter_part_yes_txt := ft.Text(visible=False, value='Enter coordinates catalog'),
                                enter_part_yes := ft.Stack(
                                    [
                                        pointinptf := ft.TextField(
                                            label="point number latitude(°) longitude(°)",
                                            label_style=ft.TextStyle(size=14, color="black"),
                                            bgcolor="white",
                                            border_color="black",
                                            color="black",
                                            content_padding=10,
                                            multiline=True,
                                            min_lines=1,
                                            max_lines=5,
                                            width=page.width * 0.98,
                                            height=160,
                                            text_size=20,
                                        ),
                                        ft.Row(
                                            controls=[
                                                ft.Container(
                                                    content=ft.IconButton(
                                                        Icons.CLEAR,
                                                        icon_color="black",
                                                        on_click=clearfield,
                                                        hover_color="red"
                                                    ),
                                                    padding=padding.only(top=5, right=20)
                                                )
                                            ],
                                            alignment=ft.MainAxisAlignment.END
                                        ),
                                    ],
                                    visible=False,
                                ),
                                ft.Divider(height=0, thickness=1, color="black"),
                                display_area,
                                ft.Column(
                                    controls=[
                                        ft.Text(value='Work with:'),
                                        ft.Row(
                                            controls=[
                                                ft.Column(
                                                    controls=[
                                                        point_check := ft.Checkbox(
                                                            value=False,
                                                            on_change=lambda e: handle_checkbox_change(point_check,
                                                                                                       point_expantile,
                                                                                                       [(line_check,
                                                                                                         line_expantile),
                                                                                                        (polygon_check,
                                                                                                         None)])
                                                        ),
                                                        ft.Text(value='Points'),
                                                    ],
                                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                ),
                                                ft.Column(
                                                    controls=[
                                                        line_check := ft.Checkbox(
                                                            value=False,
                                                            on_change=lambda e: handle_checkbox_change(line_check,
                                                                                                       line_expantile, [
                                                                                                           (point_check,
                                                                                                            point_expantile),
                                                                                                           (
                                                                                                           polygon_check,
                                                                                                           None)])
                                                        ),
                                                        ft.Text(value='Line'),
                                                    ],
                                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                ),
                                                ft.Column(
                                                    controls=[
                                                        polygon_check := ft.Checkbox(
                                                            value=False,
                                                            on_change=lambda e: handle_checkbox_change(polygon_check,
                                                                                                       None, [(
                                                                                                              point_check,
                                                                                                              point_expantile),
                                                                                                              (
                                                                                                              line_check,
                                                                                                              line_expantile)])
                                                        ),
                                                        ft.Text(value='Polygon'),
                                                    ],
                                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                ),
                                            ],
                                            alignment=ft.MainAxisAlignment.SPACE_EVENLY
                                        )
                                    ]
                                ),
                                point_expantile := ft.ExpansionTile(
                                    title=ft.Text("Buffer parameters (point)",
                                                  weight=ft.FontWeight.BOLD),
                                    affinity=ft.TileAffinity.LEADING,
                                    initially_expanded=True,
                                    visible=False,
                                    collapsed_text_color="black",
                                    text_color="black",
                                    controls=[
                                        ft.ListTile(
                                            title=ft.Text("Buffer value (meters)"),
                                            subtitle=ft.TextField(
                                                bgcolor="white",
                                                border_color="black",
                                                color="black",
                                                content_padding=10,
                                                min_lines=1,
                                                max_lines=5,
                                                width=400,
                                                height=40,
                                                text_size=15,
                                            )
                                        )
                                    ]
                                ),
                                line_expantile := ft.ExpansionTile(
                                    title=ft.Text("Buffer parameters (line)",
                                                  weight=ft.FontWeight.BOLD),
                                    affinity=ft.TileAffinity.LEADING,
                                    initially_expanded=True,
                                    visible=False,
                                    collapsed_text_color="black",
                                    text_color="black",
                                    controls=[
                                        ft.ListTile(
                                            title=ft.Text("Buffer value (meters)"),
                                            subtitle=ft.TextField(
                                                bgcolor="white",
                                                border_color="black",
                                                color="black",
                                                content_padding=10,
                                                min_lines=1,
                                                max_lines=5,
                                                width=400,
                                                height=40,
                                                text_size=15,
                                            ),
                                        ),
                                        ft.ListTile(
                                            title=ft.Text("Buffer element"),
                                            subtitle=ft.Dropdown(
                                                bgcolor="white",
                                                border_color="black",
                                                color="black",
                                                content_padding=10,
                                                width=400,
                                                height=40,
                                                text_size=15,
                                                options=[
                                                    ft.dropdown.Option("Right curb"),
                                                    ft.dropdown.Option("Left curb"),
                                                    ft.dropdown.Option("Axis"),
                                                ],
                                            ),
                                        ),
                                        ft.ListTile(
                                            title=ft.Text("Buffer type"),
                                            subtitle=ft.Dropdown(
                                                bgcolor="white",
                                                border_color="black",
                                                color="black",
                                                content_padding=10,
                                                width=400,
                                                height=40,
                                                text_size=15,
                                                options=[
                                                    ft.dropdown.Option("Flat strip"),
                                                    ft.dropdown.Option("Rounded buffer zone"),
                                                ],
                                                on_change=on_round_choice
                                            ),
                                        ),
                                        ft.ListTile(
                                            title=ft.Text("Amount of segments"),
                                            subtitle=ft.TextField(
                                                bgcolor="white",
                                                border_color="black",
                                                color="black",
                                                content_padding=10,
                                                min_lines=1,
                                                max_lines=5,
                                                width=400,
                                                height=40,
                                                text_size=15,
                                            ),
                                            visible=False
                                        ),
                                    ],
                                ),
                                ft.Divider(height=0, thickness=1, color="black"),
                                ft.Text(value='Polygon shape'),
                                ft.Row(
                                    controls=[
                                        ft.ElevatedButton("Draw", on_click=on_draw_button_click),
                                        ft.ElevatedButton("Clear", on_click=clear_map),
                                    ]
                                ),
                                formation_pages_controls := ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=Icons.KEYBOARD_ARROW_LEFT,
                                            on_click=prev_main_page,
                                            padding=padding.only(top=10, bottom=10),
                                            icon_color="black",
                                            tooltip="Попередня сторінка"
                                        ),
                                        ft.IconButton(
                                            icon=Icons.DELETE,
                                            on_click=remove_main_page,
                                            padding=padding.only(top=10, bottom=10),
                                            icon_color="black",
                                            tooltip="Видалити сторінку контенту"
                                        ),
                                        ft.Container(
                                            content=ratio_text,
                                            padding=padding.only(top=10, bottom=10),
                                        ),
                                        ft.IconButton(
                                            icon=Icons.ADD,
                                            on_click=add_main_page,
                                            padding=padding.only(top=10, bottom=10),
                                            icon_color="black",
                                            tooltip="Додати сторінку контенту"
                                        ),
                                        ft.IconButton(
                                            icon=Icons.KEYBOARD_ARROW_RIGHT,
                                            on_click=next_main_page,
                                            padding=padding.only(top=10, bottom=10),
                                            icon_color="black",
                                            tooltip="Наступна сторінка"
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                                )
                            ]
                        )
                    )
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Export to GeoJSON", on_click=download_file),
                    ]
                ),
                Text(value='Enter file name'),
                file_name_input := ft.TextField(
                    bgcolor="white",
                    border_color="black",
                    color="black",
                    content_padding=10,
                    min_lines=1,
                    max_lines=5,
                    width=page.width * 0.98,
                    height=40,
                    text_size=15,
                ),
                ft.Stack(
                    [
                        map_card := map.Map(
                            width=page.width * 0.98,
                            height=300,
                            initial_center=map.MapLatitudeLongitude(50, 36),
                            initial_zoom=8,
                            layers=[
                                map.TileLayer(url_template=current_url),
                                buffer_polygons_layer := map.PolygonLayer(
                                    polygons=[]
                                ),
                                polygons_layer := map.PolygonLayer(
                                    polygons=[]
                                ),
                                polylines_layer := map.PolylineLayer(
                                    polylines=[]
                                ),
                                points_layer := map.MarkerLayer(
                                    markers=[]
                                ),
                            ]
                        ),
                        ft.Column(
                            controls=[
                                ft.Container(
                                    content=ft.IconButton(
                                        Icons.ASSISTANT_NAVIGATION,
                                        icon_color="black",
                                        on_click=lambda e: map_card.reset_rotation(
                                            animation_duration=ft.Duration(milliseconds=500)),
                                        hover_color="blue"
                                    ),
                                    padding=padding.only(top=5, right=20)
                                ),
                                ft.Container(
                                    content=ft.IconButton(
                                        Icons.AUTO_AWESOME_MOTION_OUTLINED,
                                        icon_color="black",
                                        on_click=toggle_layer,
                                        hover_color="brown"
                                    ),
                                    padding=padding.only(top=5, right=20)
                                )
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                    ],
                ),
            ]
        )
    )

    page_1 = ft.Container(
        width=page.width,
        height=page.height,
        bgcolor=FG,
        padding=padding.only(top=20, left=10, right=10, bottom=15),
        content=ft.Column(
            scroll=ft.ScrollMode.ALWAYS,
            controls=[page_contents]
        )
    )

    container = ft.Container(
        width=page.width,
        height=page.height,
        bgcolor=BG,
        content=Stack(controls=[page_1])
    )

    page.add(container)
    update_display()


server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

ft.app(target=main)


