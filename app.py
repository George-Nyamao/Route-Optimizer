import streamlit as st
import pandas as pd
import requests
from itertools import permutations
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

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

def find_closest_stop(start_address, stops, api_key):
    if not stops:
        return None, None

    waypoints = [start_address] + stops
    dist_matrix = get_distance_matrix(waypoints, api_key)

    # The first row of the distance matrix contains the distances from the start address to all stops
    distances = [dist_matrix[0][i+1] for i in range(len(stops))]

    closest_stop_index = distances.index(min(distances))
    closest_stop = stops[closest_stop_index]

    return closest_stop, closest_stop_index


def optimize_route(waypoints, dist_matrix, is_round_trip):
    if len(waypoints) < 2:
        return waypoints

    if len(waypoints) > 10:
        st.error("Too many waypoints for brute-force optimization. Please use 8 or fewer stops.")
        return None

    if is_round_trip:
        # Round trip
        nodes = list(range(len(waypoints)))
        best_path_indices = None
        min_dist = float('inf')

        # We start at node 0, so we permute the other nodes
        for p in permutations(nodes[1:]):
            # We add the start node at the beginning and end to complete the loop
            path = [nodes[0]] + list(p) + [nodes[0]]
            dist = 0
            for i in range(len(path) - 1):
                dist += dist_matrix[path[i]][path[i+1]]

            if dist < min_dist:
                min_dist = dist
                # For a round trip, we return the path including the final return to the start
                best_path_indices = path

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


def add_stop():
    st.session_state.stops.append("")

def remove_stop(index):
    st.session_state.stops.pop(index)

# --- UI ---
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
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

    st.subheader("Bulk Add Stops")
    bulk_stops = st.text_area("Paste a list of stops (one per line)")
    if st.button("Add Bulk Stops"):
        stops_list = [s.strip() for s in bulk_stops.split("\n") if s.strip()]
        st.session_state.stops.extend(stops_list)
        st.experimental_rerun()

    if st.button("Optimize Route"):
        if not api_key:
            st.error("Please create a .env file with your GOOGLE_MAPS_API_KEY.")
        elif not start_address or not end_address:
            st.error("Please enter a start and end address.")
        else:
            with st.spinner("Optimizing route..."):
                try:
                    stops = [s for s in st.session_state.stops if s]

                    # Step 1: Find the closest stop to the start address
                    closest_stop, closest_stop_index = find_closest_stop(start_address, stops, api_key)

                    if closest_stop is None:
                        st.error("Please add at least one stop.")
                    else:
                        # The rest of the stops to be optimized
                        remaining_stops = stops[:closest_stop_index] + stops[closest_stop_index+1:]

                        # Step 2: Optimize the route for the remaining stops
                        is_round_trip = (start_address == end_address)

                        # The new start point for the optimization is the closest stop
                        new_start_address = closest_stop

                        if is_round_trip:
                            # The end point for the optimization is the original start address
                            new_end_address = start_address
                            waypoints = [new_start_address] + remaining_stops + [new_end_address]
                            dist_matrix = get_distance_matrix(waypoints, api_key)
                            optimized_remaining_route = optimize_route(waypoints, dist_matrix, False)

                            # The final route
                            optimized_route = [start_address] + optimized_remaining_route

                        else:
                            # The end point is the original end address
                            new_end_address = end_address
                            waypoints = [new_start_address] + remaining_stops + [new_end_address]
                            dist_matrix = get_distance_matrix(waypoints, api_key)
                            optimized_remaining_route = optimize_route(waypoints, dist_matrix, False)

                            # The final route
                            optimized_route = [start_address] + optimized_remaining_route

                        st.session_state.optimized_route = optimized_route

                except Exception as e:
                    st.error(f"An error occurred: {e}")

if st.session_state.optimized_route:
    with col1:
        st.header("Optimized Route")
        route = st.session_state.optimized_route
        st.write(f"Start: {route[0]}")
        for i, point in enumerate(route[1:-1]):
            st.write(f"Stop {i+1}: {point}")
        st.write(f"End: {route[-1]}")

with col2:
    st.header("Map")
    if st.session_state.optimized_route:
        origin = quote(st.session_state.optimized_route[0])
        destination = quote(st.session_state.optimized_route[-1])
        waypoints_str = "|".join([quote(s) for s in st.session_state.optimized_route[1:-1]])

        embed_url = f"https://www.google.com/maps/embed/v1/directions?key={api_key}&origin={origin}&destination={destination}&waypoints={waypoints_str}"
        st.components.v1.iframe(embed_url, height=600)
    else:
        # Placeholder map
        embed_url = f"https://www.google.com/maps/embed/v1/view?key={api_key}&center=32.973514,-96.8920588&zoom=12"
        st.components.v1.iframe(embed_url, height=600)