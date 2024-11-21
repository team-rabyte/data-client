import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import os
import json

# Paths to the telemetry and command text files
FILE_PATH = os.path.join(os.path.dirname(__file__), "measurements.txt")
COMMAND_FILE_PATH = os.path.join(os.path.dirname(__file__), "commands.txt")

# Store trajectory data for 3D path visualization
trajectory_data = {
    "x": [],
    "y": [],
    "z": []
}

# Initialize Dash app
app = dash.Dash(__name__)

# Layout of the dashboard
app.layout = html.Div([
    html.H1("Drone Telemetry and Command Dashboard"),
    dcc.Interval(
        id="interval-component",
        interval=100,  # Refresh every 100 milliseconds
        n_intervals=0
    ),
    html.Div([
        # 3D Position visualization
        html.Div([
            html.H2("Drone Position (3D Path)"),
            dcc.Graph(id="position-3d-graph"),
        ], style={"width": "48%", "display": "inline-block"}),

        # Orientation visualization
        html.Div([
            html.H2("Drone Orientation"),
            dcc.Graph(id="orientation-graph"),
        ], style={"width": "48%", "display": "inline-block"}),
    ]),
    html.Div([
        # RC Commands visualization
        html.Div([
            html.H2("RC Commands"),
            dcc.Graph(id="rc-commands-graph"),
        ], style={"width": "48%", "display": "inline-block"}),

        # PID Outputs visualization
        html.Div([
            html.H2("PID Outputs"),
            dcc.Graph(id="pid-graph"),
        ], style={"width": "48%", "display": "inline-block"}),
    ]),
    html.Div([
        # Live Text Display
        html.Div([
            html.H2("Latest Telemetry Data"),
            html.Div(id="live-update-text"),
        ], style={"width": "100%", "display": "inline-block", "verticalAlign": "top"}),
    ]),
    html.Div([
        html.H2("Send Commands to Drone"),
        html.Div([
            html.Label("Roll:"),
            dcc.Input(id="roll-input", type="number", placeholder="Enter Roll", step=1),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.Label("Pitch:"),
            dcc.Input(id="pitch-input", type="number", placeholder="Enter Pitch", step=1),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.Label("Throttle:"),
            dcc.Input(id="throttle-input", type="number", placeholder="Enter Throttle", step=1),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.Label("Yaw:"),
            dcc.Input(id="yaw-input", type="number", placeholder="Enter Yaw", step=1),
        ], style={"marginBottom": "10px"}),
        html.Button("Send Command", id="send-button"),
        html.Div(id="command-status", style={"marginTop": "10px"}),
    ], style={"marginTop": "20px"}),
])

# Callback to update graphs and live telemetry text
@app.callback(
    [
        Output("position-3d-graph", "figure"),
        Output("orientation-graph", "figure"),
        Output("rc-commands-graph", "figure"),
        Output("pid-graph", "figure"),
        Output("live-update-text", "children")
    ],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    # Check if telemetry file exists
    if not os.path.exists(FILE_PATH):
        return {}, {}, {}, {}, "Waiting for telemetry data..."

    try:
        # Read telemetry file
        with open(FILE_PATH, "r") as file:
            raw_data = file.read()

        # Split concatenated JSON objects
        raw_entries = raw_data.strip().split("}{")
        raw_entries = [entry if entry.startswith("{") else "{" + entry for entry in raw_entries]
        raw_entries = [entry if entry.endswith("}") else entry + "}" for entry in raw_entries]

        # Parse JSON entries into dictionaries
        parsed_entries = [json.loads(entry) for entry in raw_entries]

        # Get the latest telemetry data
        latest_data = parsed_entries[-1]

        # Check for position and orientation fields
        position = latest_data.get("position", [0, 0, 0])  # Default to [0, 0, 0] if missing
        orientation = latest_data.get("orientation", [0, 0, 0, 0])  # Default to [0, 0, 0, 0] if missing

        # Update trajectory data
        trajectory_data["x"].append(position[0])
        trajectory_data["y"].append(position[1])
        trajectory_data["z"].append(position[2])

        # Limit trajectory size to prevent memory issues
        max_points = 200  # Retain fewer points to reduce clutter
        if len(trajectory_data["x"]) > max_points:
            trajectory_data["x"].pop(0)
            trajectory_data["y"].pop(0)
            trajectory_data["z"].pop(0)

        # Create figures for the dashboard
        position_figure = {
            "data": [
                {
                    "x": trajectory_data["x"],
                    "y": trajectory_data["y"],
                    "z": trajectory_data["z"],
                    "type": "scatter3d",
                    "mode": "lines+markers",
                    "line": {"color": "blue", "width": 2},
                    "marker": {"size": 5, "color": "blue", "opacity": 0.8},
                }
            ],
            "layout": {
                "title": "Drone 3D Path",
                "scene": {
                    "xaxis": {"title": "X Position", "range": [-50, 50]},  # Zoom out x-axis
                    "yaxis": {"title": "Y Position", "range": [-50, 50]},  # Zoom out y-axis
                    "zaxis": {"title": "Z Position", "range": [-50, 50]},  # Zoom out z-axis
                }
            }
        }

        orientation_figure = {
            "data": [
                {"x": ["QX", "QY", "QZ", "QW"],
                 "y": orientation,
                 "type": "bar"}
            ],
            "layout": {
                "title": "Orientation Quaternion",
                "xaxis": {"title": "Components"},
                "yaxis": {"title": "Value"}
            }
        }

        rc_commands_figure = {
            "data": [
                {"x": ["Roll", "Pitch", "Throttle", "Yaw"],
                 "y": [float(latest_data["roll"]), float(latest_data["pitch"]),
                       float(latest_data["throttle"]), float(latest_data["yaw"])],
                 "type": "bar"}
            ],
            "layout": {
                "title": "RC Commands",
                "xaxis": {"title": "Control"},
                "yaxis": {"title": "Value", "range": [800, 2200]}  # Locked range
            }
        }

        pid_graph_figure = {
            "data": [
                {"x": ["PID X", "PID Y", "PID Z", "PID Yaw"],
                 "y": [float(latest_data["pid_x"]), float(latest_data["pid_y"]),
                       float(latest_data["pid_z"]), float(latest_data["pid_yaw"])],
                 "type": "bar"}
            ],
            "layout": {
                "title": "PID Outputs",
                "xaxis": {"title": "Control"},
                "yaxis": {"title": "Value", "range": [-100, 100]}  # Locked range
            }
        }

        live_text = [
            html.P(f"Roll: {latest_data['roll']}"),
            html.P(f"Pitch: {latest_data['pitch']}"),
            html.P(f"Throttle: {latest_data['throttle']}"),
            html.P(f"Yaw: {latest_data['yaw']}"),
            html.P(f"PID X: {latest_data['pid_x']}, PID Y: {latest_data['pid_y']}, "
                   f"PID Z: {latest_data['pid_z']}, PID Yaw: {latest_data['pid_yaw']}"),
            html.P(f"Position: {position}"),
            html.P(f"Orientation: {orientation}"),
        ]

        return position_figure, orientation_figure, rc_commands_figure, pid_graph_figure, live_text

    except Exception as e:
        return {}, {}, {}, {}, f"Error processing telemetry data: {e}"

# Callback to handle command submission
@app.callback(
    Output("command-status", "children"),
    [Input("send-button", "n_clicks")],
    [
        State("roll-input", "value"),
        State("pitch-input", "value"),
        State("throttle-input", "value"),
        State("yaw-input", "value"),
    ]
)
def handle_command(n_clicks, roll, pitch, throttle, yaw):
    if n_clicks is None:
        return ""

    # Create a command dictionary
    command = {
        "roll": roll or 0,
        "pitch": pitch or 0,
        "throttle": throttle or 0,
        "yaw": yaw or 0
    }

    # Write the command to the text file
    try:
        with open(COMMAND_FILE_PATH, "w") as f:
            f.write(json.dumps(command))
        return "Command sent successfully!"
    except Exception as e:
        return f"Error sending command: {e}"


# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
