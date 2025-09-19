# Route Optimizer

This is a simple web application that optimizes a route between a start and end address with multiple intermediate stops. It uses the Google Maps Routes API to calculate the most efficient route.

## Features

-   Find the optimal route for a multi-stop trip.
-   Supports both one-way and round trips.
-   Simple web interface to enter addresses and view the optimized route.

## Setup and Usage

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd route-optimizer
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Get a Google Maps API Key:**
    -   You will need a Google Maps API key with the **Routes API** enabled.
    -   You can get a key from the [Google Cloud Console](https://console.cloud.google.com/).

4.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

5.  **Use the application:**
    -   Open your web browser and go to `http://127.0.0.1:8501`.
    -   Enter your Google Maps API key.
    -   Enter your start and end addresses, and add any intermediate stops.
    -   Click "Optimize Route" to see the most efficient path.

## Development environment

The project is tested using Python 3.11 on Windows. Pandas and several other packages provide prebuilt wheels for Python 3.11 which avoids expensive local builds.

Recommended steps to recreate the development venv (PowerShell):

```powershell
# Install Python 3.11 if you don't have it (use the installer from python.org or winget):
winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements

# Remove any existing venv (optional backup first):
Remove-Item -Recurse -Force .\map_env

# Create a new venv using Python 3.11 (adjust path if needed):
py -3.11 -m venv .\map_env

# Activate the venv and install deps:
.\map_env\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements.txt
```

Note about dependencies
- `Werkzeug` is pinned to `<3.0` in `requirements.txt` to ensure compatibility with the Flask/Streamlit versions used here. If you upgrade Flask/Streamlit you may need to review and update this pin.
