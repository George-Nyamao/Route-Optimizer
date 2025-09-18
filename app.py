import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from itertools import permutations
import os
import polyline

st.set_page_config(layout="wide")

st.title("Route Optimizer")

def get_geocode(address, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching geocode: {response.text}")
    data = response.json()
    if data['status'] != 'OK':
        raise Exception(f"Error from Geocoding API: {data.get('error_message', data['status'])}")
    location = data['results'][0]['geometry']['location']
    return location['lat'], location['lng']

def get_distance_matrix(waypoints, api_key):
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters"
    }

    origins = [{"waypoint": {"address": addr}} for addr in waypoints]
    destinations = origins

    payload = {
        "origins": origins,
        "destinations": destinations,
        "travelMode": "DRIVE",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error fetching distance matrix: {response.text}")

    data = response.json()

    num_waypoints = len(waypoints)
    dist_matrix = [[0] * num_waypoints for _ in range(num_waypoints)]

    for row in data:
        origin_idx = row['originIndex']
        dest_idx = row['destinationIndex']
        distance = row.get('distanceMeters', float('inf'))
        dist_matrix[origin_idx][dest_idx] = distance

    return dist_matrix

def get_route_polyline(origin, destination, api_key):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline"
    }
    payload = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "DRIVE",
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching route polyline: {response.text}")
    data = response.json()
    if not data.get('routes'):
        raise Exception(f"Could not find a route between {origin} and {destination}")
    return data['routes'][0]['polyline']['encodedPolyline']


def optimize_route(waypoints, dist_matrix):
    # ... (same as before)
    if len(waypoints) <= 2:
        return waypoints

    if len(waypoints) > 10:
        st.error("Too many waypoints for brute-force optimization. Please use 8 or fewer stops.")
        return None

    start_address = waypoints[0]
    end_address = waypoints[-1]

    if start_address == end_address:
        # Round trip
        nodes = list(range(len(waypoints)))
        best_path_indices = None
        min_dist = float('inf')

        for p in permutations(nodes[1:]):
            path = [nodes[0]] + list(p) + [nodes[0]]
            dist = 0
            for i in range(len(path) - 1):
                dist += dist_matrix[path[i]][path[i+1]]

            if dist < min_dist:
                min_dist = dist
                best_path_indices = path[:-1]

        return [waypoints[i] for i in best_path_indices]

    else:
        # One-way trip
        nodes = list(range(len(waypoints)))
        start_node = 0
        end_node = len(waypoints) - 1
        nodes_to_permute = [i for i in nodes if i != start_node and i != end_node]

        best_path_indices = None
        min_dist = float('inf')

        for p in permutations(nodes_to_permute):
            path = [start_node] + list(p) + [end_node]
            dist = 0
            for i in range(len(path) - 1):
                dist += dist_matrix[path[i]][path[i+1]]

            if dist < min_dist:
                min_dist = dist
                best_path_indices = path

        return [waypoints[i] for i in best_path_indices]

# Initialize session state
if 'stops' not in st.session_state:
    st.session_state.stops = []
if 'optimized_route' not in st.session_state:
    st.session_state.optimized_route = None
if 'route_polylines' not in st.session_state:
    st.session_state.route_polylines = []
if 'waypoint_coords' not in st.session_state:
    st.session_state.waypoint_coords = []


def add_stop():
    st.session_state.stops.append("")

def remove_stop(index):
    st.session_state.stops.pop(index)

# --- UI ---
col1, col2 = st.columns(2)

with col1:
    st.header("Inputs")
    api_key = st.text_input("Google Maps API Key", type="password")

    start_address = st.text_input("Start Address")
    end_address = st.text_input("End Address")

    st.subheader("Stops")
    for i, stop in enumerate(st.session_state.stops):
        st.session_state.stops[i] = st.text_input(f"Stop {i+1}", value=stop, key=f"stop_{i}")
        if st.button(f"Remove Stop {i+1}", key=f"remove_{i}"):
            remove_stop(i)
            st.experimental_rerun()

    if st.button("Add Stop"):
        add_stop()
        st.experimental_rerun()

    if st.button("Optimize Route"):
        if not api_key:
            st.error("Please enter your Google Maps API Key.")
        elif not start_address or not end_address:
            st.error("Please enter a start and end address.")
        else:
            with st.spinner("Optimizing route..."):
                try:
                    waypoints = [start_address] + [s for s in st.session_state.stops if s] + [end_address]
                    dist_matrix = get_distance_matrix(waypoints, api_key)
                    optimized_route = optimize_route(waypoints, dist_matrix)
                    st.session_state.optimized_route = optimized_route

                    st.session_state.waypoint_coords = [get_geocode(addr, api_key) for addr in optimized_route]

                    polylines = []
                    for i in range(len(optimized_route) - 1):
                        p = get_route_polyline(optimized_route[i], optimized_route[i+1], api_key)
                        polylines.append(p)

                    if start_address == end_address:
                        p = get_route_polyline(optimized_route[-1], optimized_route[0], api_key)
                        polylines.append(p)

                    st.session_state.route_polylines = polylines

                except Exception as e:
                    st.error(f"An error occurred: {e}")

if st.session_state.optimized_route:
    with col1:
        st.header("Optimized Route")
        for point in st.session_state.optimized_route:
            st.write(point)

with col2:
    st.header("Map")
    if st.session_state.waypoint_coords:
        # Create a DataFrame for the waypoint coordinates and labels
        waypoint_df = pd.DataFrame(st.session_state.waypoint_coords, columns=['lat', 'lon'])
        waypoint_df['label'] = [f"Stop {i+1}" for i in range(len(st.session_state.waypoint_coords))]
        waypoint_df.iloc[0, waypoint_df.columns.get_loc('label')] = 'Start'
        waypoint_df.iloc[-1, waypoint_df.columns.get_loc('label')] = 'End'


        view_state = pdk.ViewState(
            latitude=waypoint_df['lat'].mean(),
            longitude=waypoint_df['lon'].mean(),
            zoom=5,
            pitch=50,
        )

        # Layer for the waypoints
        scatterplot = pdk.Layer(
            'ScatterplotLayer',
            data=waypoint_df,
            get_position='[lon, lat]',
            get_color='[200, 30, 0, 160]',
            get_radius=10000,
        )

        # Layer for the waypoint labels
        text_layer = pdk.Layer(
            "TextLayer",
            data=waypoint_df,
            get_position='[lon, lat]',
            get_text="label",
            get_color=[0, 0, 0, 200],
            get_size=15,
            get_alignment_baseline="'bottom'",
        )

        layers = [scatterplot, text_layer]

        # Layer for the route path
        for p in st.session_state.route_polylines:
            decoded_polyline = polyline.decode(p)
            path_df = pd.DataFrame(decoded_polyline, columns=['lat', 'lon'])
            path_layer = pdk.Layer(
                'PathLayer',
                data=path_df,
                get_path='[lon, lat]',
                get_color='[0, 0, 255, 255]',
                width_min_pixels=3,
            )
            layers.append(path_layer)

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=view_state,
            layers=layers
        ))
    else:
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=40.7128,
                longitude=-74.0060,
                zoom=11,
                pitch=50,
            )
        ))
