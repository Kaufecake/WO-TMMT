import re
import requests
import folium
from flask import Flask, request, render_template_string
import os
import json

# Flask app setup
app = Flask(__name__)

# HTML template for user input
html_form = '''
    <!doctype html>
    <title>Interactive Map Input</title>
    <h1>Enter Google Sheet Link and Select Server</h1>
    <form action="/" method="post">
      Google Sheet Link: <input type="text" name="sheet_url"><br>
      Server: <select name="selected_server">
        <option value="Independence">Independence</option>
        <option value="Deliverance">Deliverance</option>
        <option value="Exodus">Exodus</option>
        <option value="Celebration">Celebration</option>
        <option value="Pristine">Pristine</option>
        <option value="Release">Release</option>
        <option value="Xanadu">Xanadu</option>
        <option value="Harmony">Harmony</option>
        <option value="Melody">Melody</option>
        <option value="Cadence">Cadence</option>
      </select><br>
      <div style="display:inline-block; margin-left: 20px;">
        <p>Servers not yet implemented: Chaos, Elevation, Desertion, Affliction, Serenity, Defiance.</p>
      </div><br>
      <input type="submit" value="Submit">
    </form>
'''

# Function to get data from the main Google Sheet with validation
def get_data_from_google_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&sheet=Map_Matrix"
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch data from Google Sheet.")
        return None

    # Clean up the response to parse JSON
    json_data = json.loads(response.text[47:-2])
    headers = [entry['label'] for entry in json_data['table']['cols']]
    rows = json_data['table']['rows']
    data = []
    for row in rows:
        row_data = {headers[i]: (row['c'][i]['v'] if row['c'][i] else None) for i in range(len(headers))}
        data.append(row_data)

    # Check data format
    expected_keys = {"Map Name", "Map Link", "Completed", "Landmark"}
    for row in data:
        if not expected_keys.issubset(row.keys()):
            print("Unexpected data in spreadsheet.")
            return None  # Cease further processing
    return data

# Function to load server settings from a static Google Sheet, "Sheet1" tab
def load_static_server_settings():
    sheet_id = "1Y5VcFEg9wG8HeokzLgq0o5xv5Rqyv3-FERNs52GVR6c"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&sheet=Sheet1"
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch data from Google Sheet.")
        return None

    # Clean up the response to parse JSON
    json_data = json.loads(response.text[47:-2])
    headers = [entry['label'] for entry in json_data['table']['cols']]
    rows = json_data['table']['rows']
    data = []
    for row in rows:
        row_data = {headers[i]: (row['c'][i]['v'] if row['c'][i] else None) for i in range(len(headers))}
        data.append(row_data)

    server_settings = {}
    for row in data:
        if 'Server' in row and 'X Dim' in row and 'Y Dim' in row:
            server_name = row['Server'].capitalize()
            x_dim = float(row['X Dim'])
            y_dim = float(row['Y Dim'])
            server_settings[server_name] = {
                "x_dim": x_dim,
                "y_dim": y_dim
            }
        else:
            print("Missing expected keys in row:", row)
    return server_settings

# Function to parse 'Map Link' and add 'Server', 'X Coord', 'Y Coord', 'Landmark'
def parse_map_link(data):
    parsed_data = []
    for row in data:
        map_name = row['Map Name']
        map_link = row['Map Link']
        finished = str(row['Completed']).strip().lower()  # Normalize here
        landmark = str(row['Landmark']).strip().lower() == 'true'  # Normalize landmark to boolean

        # Extract the Server, X Coord, and Y Coord from 'Map Link'
        server_match = re.search(r"https://(.*?).yaga.host", map_link)
        coord_match = re.search(r"yaga.host/#(\d+),(\d+)", map_link)

        server = server_match.group(1).capitalize() if server_match else None
        x_coord = int(coord_match.group(1)) if coord_match else None
        y_coord = int(coord_match.group(2)) if coord_match else None

        # Add parsed data to new array
        parsed_data.append([map_name, server, x_coord, y_coord, finished, landmark])
    return parsed_data

# Function to filter data based on server and completion status
def filter_data(data, selected_server, show_finished=False):
    filtered_data = []
    for row in data:
        server = row[1]
        completed = row[4]
        if server == selected_server and (show_finished or str(completed).strip().lower() == "false"):
            filtered_data.append(row)
        else:
            print(f"Row omitted: {row}")
    return filtered_data

# Function to create an interactive map with Folium
def create_interactive_map(data, x_dim, y_dim, server_name):
    # Creates an interactive map with a custom image overlay
    # Center map at midpoint of the area, with zoom adjusted to fit dimensions
    map_object = folium.Map(
        location=[y_dim / 2, x_dim / 2],
        zoom_start=1,
        crs='Simple',
        max_bounds=False,
        width='100%',
        height='100%',
        tiles=None
    )
    image_path = None
    for file_name in os.listdir('maps'):
        if file_name.startswith(server_name.lower()) and file_name.endswith('.png'):
            image_path = os.path.join('maps', file_name)
            break
    if image_path is None or not os.path.exists(image_path):
        print(f"Image for server '{server_name}' not found at {image_path}")
        return
    folium.raster_layers.ImageOverlay(
        image=image_path,
        bounds=[[0, 0], [y_dim, x_dim]],
        origin='upper',
        interactive=True,
        opacity=1.0
    ).add_to(map_object)

    # Adjust bounds for the map to fit the image
    map_object.fit_bounds([[0, 0], [y_dim, x_dim]])

    # Add each point to the map
    for row in data:
        x, y, name, landmark = row[2], row[3], row[0], row[5]
        if landmark:
            folium.Marker(
                location=[y_dim - y, x],
                icon=folium.Icon(icon='star', color='gold', prefix='fa'),
                popup=folium.Popup(name, parse_html=True)
            ).add_to(map_object)
        else:
            folium.CircleMarker(
                location=[y_dim - y, x],
                radius=8,
                color="white",
                fill=True,
                fill_opacity=0.5,
                popup=folium.Popup(name, parse_html=True)
            ).add_to(map_object)

    # Save map to an HTML file
    os.makedirs("templates", exist_ok=True)
    map_object.save("templates/interactive_map.html")

# Flask routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form data
        sheet_url = request.form['sheet_url']
        selected_server = request.form['selected_server']

        # Extract the sheet ID from the URL
        sheet_id = sheet_url.split("/d/")[1].split("/")[0] if "/d/" in sheet_url else None

        if not sheet_id:
            return "Invalid Google Sheet link. Please go back and try again."

        # Load server settings from the static Google Sheet's "Sheet1" tab
        server_settings = load_static_server_settings()
        if server_settings is None or selected_server not in server_settings:
            return "Failed to load server settings from Google Sheet or server not found."

        # Step 1: Get data from the primary Google Sheet
        raw_data = get_data_from_google_sheet(sheet_id)

        if raw_data is None:
            return "Unexpected data format in Google Sheet. Please check the sheet."

        # Step 2: Parse data
        parsed_data = parse_map_link(raw_data)

        # Step 3: Filter data based on server and completion status
        filtered_data = filter_data(parsed_data, selected_server)

        # Step 4: Create an interactive map using the selected server's settings
        server_info = server_settings[selected_server]
        create_interactive_map(filtered_data, x_dim=server_info["x_dim"], y_dim=server_info["y_dim"], server_name=selected_server)

        # Step 5: Create a table to show an overview of the filtered data
        table_html = "<table border='1'><tr><th>Map Name</th><th>Server</th><th>X Coord</th><th>Y Coord</th><th>Landmark</th></tr>"
        for row in filtered_data:
            landmark = 'TRUE' if row[5] else 'FALSE'
            table_html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{landmark}</td></tr>"
        table_html += "</table>"

        return render_template_string(f"""
            <h1>Map Created Successfully</h1>
            <a href='/map'>View Map</a><br><br>
            <h2>Filtered Data</h2>
            {table_html}
        """)

    return html_form

@app.route('/map')
def map():
    return render_template_string(open("templates/interactive_map.html").read())

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
