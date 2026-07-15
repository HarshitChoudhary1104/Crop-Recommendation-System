from flask import Flask, request, render_template, jsonify
import pandas as pd
import pickle
import os
from functools import wraps
import urllib.request
import urllib.parse
import json

app = Flask(__name__)

# --- Load Model and Dataset ---
try:
    model = pickle.load(open('LogisticRegression.pkl', 'rb'))
except FileNotFoundError:
    model = None
    app.logger.error("Model file 'LogisticRegression.pkl' not found. The predictor will not work.")

try:
    df = pd.read_csv('Crop_recommendation.csv')
    CROP_NAMES = sorted(df['label'].unique())
except FileNotFoundError:
    df = None
    CROP_NAMES = []
    app.logger.error("Dataset 'Crop_recommendation.csv' not found. The reverse search will not work.")

# --- Configuration for the Predictor ---
INPUT_CONFIG = [
    {'form_name': 'Nitrogen', 'model_col': 'N', 'display_name': 'Nitrogen', 'min': 0, 'max': 200},
    {'form_name': 'Phosphorus', 'model_col': 'P', 'display_name': 'Phosphorus', 'min': 0, 'max': 200},
    {'form_name': 'Potassium', 'model_col': 'K', 'display_name': 'Potassium', 'min': 0, 'max': 200},
    {'form_name': 'Temperature', 'model_col': 'temperature', 'display_name': 'Temperature (°C)', 'min': 0, 'max': 50},
    {'form_name': 'Humidity', 'model_col': 'humidity', 'display_name': 'Humidity (%)', 'min': 0, 'max': 100},
    {'form_name': 'Ph', 'model_col': 'ph', 'display_name': 'pH Level', 'min': 0, 'max': 14},
    {'form_name': 'Rainfall', 'model_col': 'rainfall', 'display_name': 'Rainfall (mm)', 'min': 0, 'max': 300},
]
FEATURE_COLS = [field['model_col'] for field in INPUT_CONFIG]

# --- Security / Authentication ---
API_KEY = os.environ.get("API_KEY", "secure_secret_key_123")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key")
        if provided_key and provided_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized. Invalid or missing X-API-Key header."}), 401
    return decorated_function

# --- Helper Functions ---
def fetch_weather_data(lat, lon):
    """Fetches real-time temperature and humidity for given coordinates."""
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    req = urllib.request.Request(weather_url, headers={'User-Agent': 'CropApp/1.0'})
    with urllib.request.urlopen(req, timeout=5) as response:
        weather_data = json.loads(response.read().decode())
    return weather_data['current']['temperature_2m'], weather_data['current']['relative_humidity_2m']

def validate_telemetry(data_dict):
    """Validates telemetry dictionary against INPUT_CONFIG. Returns (valid_data, errors)."""
    errors = {}
    valid_data = {}
    for field_config in INPUT_CONFIG:
        name = field_config['form_name']
        display_name = field_config['display_name']
        min_val, max_val = field_config['min'], field_config['max']
        value_str = data_dict.get(name)

        if value_str is None or str(value_str).strip() == '':
            errors[name] = f"{display_name} is a required field."
            continue
        try:
            value = float(value_str)
            if not (min_val <= value <= max_val):
                errors[name] = f"{display_name} must be between {min_val} and {max_val}."
            else:
                valid_data[name] = value
        except ValueError:
            errors[name] = f"{display_name} must be a valid number."
    return valid_data, errors

# --- Main Predictor Route ---
@app.route('/')
def index():
    """Renders the main prediction page."""
    return render_template("index.html")

@app.route("/predict", methods=['POST'])
def predict():
    """Handles the prediction form submission."""
    if model is None or df is None:
        return render_template('index.html', errors={'prediction': "Model or dataset is not loaded. Please check server logs."})

    form_values = dict(request.form)
    errors = {}

    # --- Live Weather API Integration ---
    if 'Latitude' in form_values and str(form_values['Latitude']).strip() and 'Longitude' in form_values and str(form_values['Longitude']).strip():
        lat = str(form_values['Latitude']).strip()
        lon = str(form_values['Longitude']).strip()
        try:
            temp, hum = fetch_weather_data(lat, lon)
            form_values['Temperature'] = temp
            form_values['Humidity'] = hum
        except Exception as e:
            app.logger.error(f"Weather API Error (Exact Location): {e}")
            errors['City'] = "Failed to fetch live weather data for exact location. Please try again."

    elif 'City' in form_values and str(form_values['City']).strip():
        city = str(form_values['City']).strip()
        try:
            # Geocode the City
            geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
            req = urllib.request.Request(geocode_url, headers={'User-Agent': 'CropApp/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                geo_data = json.loads(response.read().decode())
                
            if not geo_data.get('results'):
                errors['City'] = f"Could not find coordinates for city '{city}'."
            else:
                lat = geo_data['results'][0]['latitude']
                lon = geo_data['results'][0]['longitude']
                temp, hum = fetch_weather_data(lat, lon)
                form_values['Temperature'] = temp
                form_values['Humidity'] = hum
        except Exception as e:
            app.logger.error(f"Weather API Error: {e}")
            errors['City'] = f"Failed to fetch live weather data for '{city}'. Please try again."

    valid_data, validation_errors = validate_telemetry(form_values)
    errors.update(validation_errors)

    if errors:
        return render_template('index.html', errors=errors, values=form_values)

    try:
        model_input_data = {field['model_col']: valid_data[field['form_name']] for field in INPUT_CONFIG}
        single_pred_df = pd.DataFrame([model_input_data])
        prediction = model.predict(single_pred_df)
        result_text = f"'{prediction[0]}' is the best crop to cultivate."
        return render_template('index.html', result=result_text, values=form_values)
    except Exception as e:
        app.logger.error(f"PREDICTION FAILED. Error: {e}")
        return render_template('index.html', errors={'prediction': f"An error occurred during prediction: {e}"}, values=form_values)


# --- Reverse Search Route ---
@app.route('/conditions', methods=['GET', 'POST'])
def conditions():
    """Handles the reverse search feature."""
    if df is None:
        return render_template('conditions.html', error="Dataset not found. Cannot perform reverse search.")

    conditions_data = None
    selected_crop = None

    if request.method == 'POST':
        selected_crop = request.form.get('crop')
        if selected_crop:
            crop_df = df[df['label'] == selected_crop]
            conditions_data = {}
            for col in FEATURE_COLS:
                q1 = crop_df[col].quantile(0.25)
                q3 = crop_df[col].quantile(0.75)
                conditions_data[col.capitalize()] = {'min': q1, 'max': q3}

    return render_template('conditions.html', crops=CROP_NAMES, selected_crop=selected_crop, conditions=conditions_data)


# --- RESTful API Routes ---
@app.route('/api/predict', methods=['POST'])
@require_api_key
def api_predict():
    """Secure REST API endpoint for real-time telemetry prediction."""
    if model is None or df is None:
        return jsonify({"error": "Internal server error. Model or dataset not loaded."}), 500
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400
            
        valid_data, errors = validate_telemetry(data)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
                
        model_input_data = {field['model_col']: valid_data[field['form_name']] for field in INPUT_CONFIG}
        single_pred_df = pd.DataFrame([model_input_data])
        prediction = model.predict(single_pred_df)
        
        return jsonify({
            "status": "success",
            "telemetry_processed": valid_data,
            "recommended_crop": prediction[0]
        }), 200
        
    except Exception as e:
        app.logger.error(f"API PREDICTION FAILED. Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conditions', methods=['GET'])
def api_conditions():
    """API endpoint to get ideal environmental ranges for a given crop."""
    crop = request.args.get('crop')
    if not crop:
        return jsonify({"error": "Missing 'crop' query parameter."}), 400
        
    if df is None:
        return jsonify({"error": "Dataset not found."}), 500
        
    if crop not in CROP_NAMES:
        return jsonify({"error": f"Crop '{crop}' not found. Available crops: {', '.join(CROP_NAMES)}"}), 404
        
    crop_df = df[df['label'] == crop]
    conditions_data = {}
    for col in FEATURE_COLS:
        q1 = crop_df[col].quantile(0.25)
        q3 = crop_df[col].quantile(0.75)
        conditions_data[col.capitalize()] = {'min': round(q1, 2), 'max': round(q3, 2)}
        
    return jsonify({
        "crop": crop,
        "ideal_conditions": conditions_data
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
