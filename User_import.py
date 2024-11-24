import requests
import json
from flask import Flask, request, render_template_string

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

def get_data_from_google_sheet(sheet_id):
    """
    Function to get data from the main Google Sheet with validation.
    This function imports data from a Google Sheet provided by the user.
    Args:
        sheet_id (str): The ID of the Google Sheet to import.
    Returns:
        list: A list of dictionaries representing the rows from the Google Sheet.
    """
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

        # Step 1: Get data from the primary Google Sheet
        raw_data = get_data_from_google_sheet(sheet_id)

        if raw_data is None:
            return "Unexpected data format in Google Sheet. Please check the sheet."

        # Process data or perform other actions as needed here
        return render_template_string("<h1>Data Imported Successfully</h1>")

    return html_form

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
