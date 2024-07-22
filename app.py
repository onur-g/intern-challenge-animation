import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import requests
import random
import os
from datetime import datetime, timedelta

# Initialize the Dash app
app = Dash(__name__)

# Set your Mapbox access token
mapbox_access_token = os.getenv('MAPBOX_ACCESS_TOKEN')
if not mapbox_access_token:
    raise ValueError("Please set the MAPBOX_ACCESS_TOKEN environment variable.")

# Function to get route coordinates using Mapbox Directions API
def get_route(start_lat, start_lon, end_lat, end_lon):
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start_lon},{start_lat};{end_lon},{end_lat}?geometries=geojson&access_token={mapbox_access_token}"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Error fetching route from Mapbox API: {response.text}")
    data = response.json()
    if 'routes' not in data or not data['routes']:
        raise ValueError(f"No routes found in response: {data}")
    route = data['routes'][0]['geometry']['coordinates']
    return [(coord[1], coord[0]) for coord in route]

# Function to generate random coordinates around downtown Dearborn, Michigan
def generate_random_coordinates(center_lat, center_lon, num_points, lat_range, lon_range):
    return [
        (center_lat + random.uniform(-lat_range, lat_range), center_lon + random.uniform(-lon_range, lon_range))
        for _ in range(num_points)
    ]

# Center coordinates for downtown Dearborn, Michigan
center_lat, center_lon = 42.3223, -83.1763
num_points = 20
lat_range = 0.02
lon_range = 0.02

# Generate random coordinates for the delivery route
route_coords_optimized = generate_random_coordinates(center_lat, center_lon, num_points, lat_range, lon_range)
route_coords_unoptimized = route_coords_optimized.copy()
random.shuffle(route_coords_unoptimized)

route_lats_optimized, route_lons_optimized = zip(*route_coords_optimized)
route_lats_unoptimized, route_lons_unoptimized = zip(*route_coords_unoptimized)

# Generate more random coordinates for charging points
num_charging_points = 10
charging_coords = generate_random_coordinates(center_lat, center_lon, num_charging_points, lat_range, lon_range)
charging_stops = [{"lat": lat, "lon": lon, "distance": f"{random.uniform(0.5, 2.0):.1f} miles"} for lat, lon in charging_coords]

# Generate street routes for the delivery route
street_routes_optimized = []
street_routes_unoptimized = []
for i in range(len(route_lats_optimized) - 1):
    try:
        street_routes_optimized.extend(get_route(route_lats_optimized[i], route_lons_optimized[i], route_lats_optimized[i+1], route_lons_optimized[i+1]))
        street_routes_unoptimized.extend(get_route(route_lats_unoptimized[i], route_lons_unoptimized[i], route_lats_unoptimized[i+1], route_lons_unoptimized[i+1]))
    except ValueError as e:
        print(f"Error generating route: {e}")

# Create the Plotly figures for optimized and unoptimized maps
fig_optimized = go.Figure()
fig_unoptimized = go.Figure()

# Add charging points with labels
for stop in charging_stops:
    fig_optimized.add_trace(go.Scattermapbox(
        lat=[stop["lat"]], 
        lon=[stop["lon"]], 
        mode='markers+text', 
        marker=dict(size=10, color='#7DF9FF'),  # Bright electric blue color for optimized
        text=[stop["distance"]],
        textposition="top right",
        name='Charging Point'
    ))

    fig_unoptimized.add_trace(go.Scattermapbox(
        lat=[stop["lat"]], 
        lon=[stop["lon"]], 
        mode='markers+text', 
        marker=dict(size=10, color='#FF4500'),  # Dark red color for unoptimized
        text=[stop["distance"]],
        textposition="top right",
        name='Charging Point'
    ))

# Create animation frames for the van's movement with a thick line tracing its path
frames_optimized = []
frames_unoptimized = []
van_path_lats_optimized = []
van_path_lons_optimized = []
van_path_lats_unoptimized = []
van_path_lons_unoptimized = []
initial_time = datetime.strptime("09:00", "%H:%M")  # Start at 9 AM
total_time = timedelta(hours=6)  # From 9 AM to 3 PM
time_increment = total_time / len(street_routes_optimized)

current_time = initial_time
charging_duration = timedelta(minutes=30)  # Assume 30 minutes charging time at each charging point

# Optimized path: fewer stops
charging_times_optimized = [random.choice(range(len(street_routes_optimized))) for _ in range(num_charging_points)]

# Unoptimized path: more frequent stops
charging_times_unoptimized = [random.choice(range(len(street_routes_unoptimized))) for _ in range(num_charging_points * 2)]

times = []
charging_status_optimized = []
charging_status_unoptimized = []
battery_percentage_optimized = 100
battery_percentage_unoptimized = 100

for i in range(len(street_routes_optimized)):
    if i < len(street_routes_optimized):
        van_path_lats_optimized.append(street_routes_optimized[i][0])
        van_path_lons_optimized.append(street_routes_optimized[i][1])
    if i < len(street_routes_unoptimized):
        van_path_lats_unoptimized.append(street_routes_unoptimized[i][0])
        van_path_lons_unoptimized.append(street_routes_unoptimized[i][1])
    
    is_charging_optimized = i in charging_times_optimized
    is_charging_unoptimized = i in charging_times_unoptimized
    
    if is_charging_optimized:
        battery_percentage_optimized = min(battery_percentage_optimized + 20, 100)  # Increase by 20%
    else:
        battery_percentage_optimized = max(battery_percentage_optimized - 1, 0)  # Decrease by 1%
    
    if is_charging_unoptimized:
        battery_percentage_unoptimized = min(battery_percentage_unoptimized + 20, 100)  # Increase by 20%
    else:
        battery_percentage_unoptimized = max(battery_percentage_unoptimized - 1, 0)  # Decrease by 1%
    
    times.append(current_time.strftime("%I:%M %p"))
    charging_status_optimized.append(f"{battery_percentage_optimized}%")
    charging_status_unoptimized.append(f"{battery_percentage_unoptimized}%")
    
    frames_optimized.append(go.Frame(
        data=[
            go.Scattermapbox(
                lat=van_path_lats_optimized, 
                lon=van_path_lons_optimized, 
                mode='lines',  # Trace path with a thick line
                line=dict(width=6, color='#7DF9FF'),  # Bright electric blue color
                name='Van Path'
            ),
            go.Scattermapbox(
                lat=[van_path_lats_optimized[-1]], 
                lon=[van_path_lons_optimized[-1]], 
                mode='markers', 
                marker=dict(size=20, color='#7DF9FF'),  # Van as a point marker in bright electric blue color
                name='Van'
            )
        ],
        name=current_time.strftime("%I:%M %p")
    ))
    
    frames_unoptimized.append(go.Frame(
        data=[
            go.Scattermapbox(
                lat=van_path_lats_unoptimized, 
                lon=van_path_lons_unoptimized, 
                mode='lines',  # Trace path with a thick line
                line=dict(width=6, color='#FF4500'),  # Dark red color
                name='Van Path'
            ),
            go.Scattermapbox(
                lat=[van_path_lats_unoptimized[-1]], 
                lon=[van_path_lons_unoptimized[-1]], 
                mode='markers', 
                marker=dict(size=20, color='#FF4500'),  # Van as a point marker in dark red color
                name='Van'
            )
        ],
        name=current_time.strftime("%I:%M %p")
    ))
    
    if not is_charging_optimized:
        current_time += time_increment

fig_optimized.frames = frames_optimized
fig_unoptimized.frames = frames_unoptimized

# Set the initial map style and layout for both figures
for fig in [fig_optimized, fig_unoptimized]:
    fig.update_layout(
        mapbox_style="dark",  # Set initial style to dark
        mapbox_zoom=12,  # Zoomed out
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_accesstoken=mapbox_access_token,
        showlegend=False,  # Remove the legend
        autosize=False,
        width=800,  # Width to make it more rectangular
        height=700,  # Height to make it more rectangular
        margin={"r": 0, "t": 0, "l": 0, "b": 0},  # Remove extra margins
        updatemenus=[{
            "buttons": [
                {
                    "args": [None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True, "transition": {"duration": 500}}],
                    "label": "Play",
                    "method": "animate"
                },
                {
                    "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}],
                    "label": "Pause",
                    "method": "animate"
                }
            ],
            "direction": "left",
            "pad": {"r": 10, "t": 87},
            "showactive": False,
            "type": "buttons",
            "x": 0.1,
            "xanchor": "right",
            "y": 0,
            "yanchor": "top"
        }]
    )

# Define the Dash layout
app.layout = html.Div([
    html.H1(id='title', children='Enhancing the Electric Experience for Commercial Drivers', style={'textAlign': 'center'}),
    html.H2(id='subtitle', children='Onur Gunduz', style={'textAlign': 'center'}),
    html.Div(className='toggle-container', children=[
        html.Label('Dark Mode', className='toggle-label', style={'textAlign': 'center'}),
        dcc.Checklist(
            id='dark-mode-toggle',
            options=[{'label': '', 'value': 'dark'}],
            value=['dark']  # Set dark mode on by default
        )
    ], style={'textAlign': 'center'}),
    html.Div(style={'display': 'flex', 'justifyContent': 'space-between'}, children=[
        html.Div(style={'width': '50%', 'textAlign': 'center', 'position': 'relative'}, children=[
            html.H2('Unoptimized', style={'color': 'black'}),
            dcc.Graph(id='map-unoptimized', figure=fig_unoptimized, className='map-container'),
            html.Div(id='time-display-unoptimized', style={'position': 'absolute', 'top': '10px', 'left': '10px', 'color': 'black', 'fontSize': '20px', 'backgroundColor': 'white', 'padding': '5px', 'borderRadius': '5px'}),
            html.Div(id='charging-display-unoptimized', style={'position': 'absolute', 'top': '10px', 'right': '10px', 'color': 'red', 'fontSize': '20px', 'backgroundColor': 'white', 'padding': '5px', 'borderRadius': '5px'})
        ]),
        html.Div(style={'width': '50%', 'textAlign': 'center', 'position': 'relative'}, children=[
            html.H2('Optimized', style={'color': 'black'}),
            dcc.Graph(id='map-optimized', figure=fig_optimized, className='map-container'),
            html.Div(id='time-display-optimized', style={'position': 'absolute', 'top': '10px', 'left': '10px', 'color': 'black', 'fontSize': '20px', 'backgroundColor': 'white', 'padding': '5px', 'borderRadius': '5px'}),
            html.Div(id='charging-display-optimized', style={'position': 'absolute', 'top': '10px', 'right': '10px', 'color': 'red', 'fontSize': '20px', 'backgroundColor': 'white', 'padding': '5px', 'borderRadius': '5px'})
        ])
    ]),
    dcc.Interval(id='interval-component', interval=500, n_intervals=0, disabled=True)  # Update every 500 ms, disabled by default
])

@app.callback(
    [Output('interval-component', 'disabled'), Output('interval-component', 'n_intervals')],
    [Input('map-optimized', 'relayoutData'), Input('map-unoptimized', 'relayoutData')],
    [State('interval-component', 'n_intervals')]
)
def control_interval(relayout_data_optimized, relayout_data_unoptimized, n_intervals):
    if (relayout_data_optimized and 'sliders[0].value' in relayout_data_optimized) or (relayout_data_unoptimized and 'sliders[0].value' in relayout_data_unoptimized):
        if (relayout_data_optimized and relayout_data_optimized['sliders[0].value'] == 0) or (relayout_data_unoptimized and relayout_data_unoptimized['sliders[0].value'] == 0):
            return False, 0  # Enable the interval and reset n_intervals when starting
        return False, n_intervals  # Enable the interval when animation is playing
    return True, n_intervals  # Disable the interval when animation is paused

@app.callback(
    [Output('time-display-optimized', 'children'), Output('charging-display-optimized', 'children'), 
     Output('time-display-unoptimized', 'children'), Output('charging-display-unoptimized', 'children')],
    [Input('interval-component', 'n_intervals')],
    [State('interval-component', 'disabled')]
)
def update_time_and_charging(n_intervals, interval_disabled):
    frame_idx = n_intervals % len(times) if not interval_disabled else 0
    current_time_display = times[frame_idx]
    charging_status_display_optimized = charging_status_optimized[frame_idx]
    charging_status_display_unoptimized = charging_status_unoptimized[frame_idx]
    return current_time_display, charging_status_display_optimized, current_time_display, charging_status_display_unoptimized

@app.callback(
    [Output('map-optimized', 'figure'), Output('map-unoptimized', 'figure')],
    [Input('dark-mode-toggle', 'value')]
)
def update_map_style(dark_mode):
    # Create a copy of the figures using to_dict and from_dict
    updated_fig_dict_optimized = fig_optimized.to_dict()
    updated_fig_dict_unoptimized = fig_unoptimized.to_dict()
    updated_fig_optimized = go.Figure(updated_fig_dict_optimized)
    updated_fig_unoptimized = go.Figure(updated_fig_dict_unoptimized)
    
    if 'dark' in dark_mode:
        updated_fig_optimized.update_layout(mapbox_style="dark")
        updated_fig_unoptimized.update_layout(mapbox_style="dark")
    else:
        updated_fig_optimized.update_layout(mapbox_style="open-street-map")
        updated_fig_unoptimized.update_layout(mapbox_style="open-street-map")
        
    return updated_fig_optimized, updated_fig_unoptimized

if __name__ == '__main__':
    app.run_server(debug=True)
