# Secure Crop Recommendation Engine 🌾

A full-stack, machine learning-powered web application and RESTful API that delivers high-precision agricultural crop recommendations based on environmental telemetry. 

## Features & Recent Upgrades

* **Real-Time GPS Weather Integration**: Leverages the browser's Geolocation API (`navigator.geolocation`) to capture exact physical coordinates, sending them to the backend to seamlessly fetch live temperature and humidity via the **Open-Meteo REST API**.
* **Secure RESTful API**: Includes robust endpoints (`/api/predict` and `/api/conditions`) protected by `X-API-Key` authentication for safe, programmatic telemetry processing.
* **Machine Learning Backend**: Powered by a trained Logistic Regression model (via Scikit-Learn) to evaluate Nitrogen, Phosphorus, Potassium, pH, Rainfall, and live weather conditions to maximize crop yield predictions.
* **Dockerized Architecture**: Fully containerized with a custom `Dockerfile` and `.dockerignore`, ensuring reproducible and frictionless deployments across cloud server architectures.
* **Optimized Architecture**: The Python backend was rigorously refactored to adhere to DRY (Don't Repeat Yourself) principles, with core business logic and third-party API integration extracted into modular helper functions.
* **Gamified UI/UX**: Features a highly customized, vibrant "Minecraft" themed frontend using custom CSS, the "Press Start 2P" web font, and dynamic JavaScript interactions.

## Technologies Used
* **Backend**: Python, Flask, `urllib` (for zero-dependency external API fetching)
* **Machine Learning**: Scikit-Learn, Pandas, NumPy, Pickle
* **Frontend**: HTML5, Vanilla CSS, JavaScript, Bootstrap 5, Browser Geolocation API
* **DevOps**: Docker, Git, GitHub CLI

## Installation and Usage

### Local Python Setup
1. Clone the repository: `git clone https://github.com/HarshitChoudhary1104/Crop-Recommendation-System.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the Flask server: `python app.py`
4. Open your browser to `http://localhost:5000`

### Docker Deployment
1. Build the image: `docker build -t crop-predictor .`
2. Run the container: `docker run -p 5000:5000 -e API_KEY=your_secure_key crop-predictor`

## API Documentation

### POST `/api/predict`
Securely predict the best crop based on raw telemetry.
* **Headers**: `X-API-Key: <your_secret_key>`
* **Body** (JSON): `{"Nitrogen": 90, "Phosphorus": 42, "Potassium": 43, "Temperature": 25, "Humidity": 80, "Ph": 6.5, "Rainfall": 200}`

## Future Enhancements
* Implementation of a SQLAlchemy database to log predictions for advanced analytics.
* Automated CI/CD pipelines via GitHub Actions for seamless deployment.

## Acknowledgements
Developed with open-source machine learning datasets and integrated with the Open-Meteo free weather API.
