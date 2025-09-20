import streamlit as st
import pandas as pd
import requests
from itertools import permutations
import os
from urllib.parse import quote

st.set_page_config(layout="wide")

st.title("Route Optimizer")

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

def optimize_route(waypoints, dist_matrix):
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
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""


def add_stop():
    st.session_state.stops.append("")

def remove_stop(index):
    st.session_state.stops.pop(index)

# --- UI ---
st.session_state.api_key = st.text_input("Google Maps API Key", type="password", value=st.session_state.api_key)
col1, col2 = st.columns(2)

with col1:
    st.header("Inputs")
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
        if not st.session_state.api_key:
            st.error("Please enter your Google Maps API Key.")
        elif not start_address or not end_address:
            st.error("Please enter a start and end address.")
        else:
            with st.spinner("Optimizing route..."):
                try:
                    waypoints = [start_address] + [s for s in st.session_state.stops if s] + [end_address]
                    dist_matrix = get_distance_matrix(waypoints, st.session_state.api_key)
                    optimized_route = optimize_route(waypoints, dist_matrix)
                    st.session_state.optimized_route = optimized_route
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if st.session_state.optimized_route:
    with col1:
        st.header("Optimized Route")
        for point in st.session_state.optimized_route:
            st.write(point)

with col2:
    st.header("Map")
    if st.session_state.optimized_route:
        origin = quote(st.session_state.optimized_route[0])
        destination = quote(st.session_state.optimized_route[-1])
        # The waypoints parameter should only contain the stops between the origin and destination.
        waypoints_str = "|".join([quote(s) for s in st.session_state.optimized_route[1:-1]])

        embed_url = f"https://www.google.com/maps/embed/v1/directions?key={st.session_state.api_key}&origin={origin}&destination={destination}&waypoints={waypoints_str}"
        st.components.v1.iframe(embed_url, height=600)
    else:
        # Placeholder map
        placeholder_address = "4645 Plano Pkwy, Carrollton, TX 75010, USA"
        embed_url = f"https://www.google.com/maps/embed/v1/place?key={st.session_state.api_key}&q={quote(placeholder_address)}"
        st.components.v1.iframe(embed_url, height=600)
