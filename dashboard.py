import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import os
import json
import time

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
        # Flight Controls
        html.Div([
            html.H3("Flight Controls", style={"color": "#2196F3"}),
            html.Div([
                html.Label("Roll:"),
                dcc.Input(id="roll-input", type="number", value=1500, placeholder="Enter Roll (1000-2000)", 
                         min=1000, max=2000, step=1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("Pitch:"),
                dcc.Input(id="pitch-input", type="number", value=1500, placeholder="Enter Pitch (1000-2000)", 
                         min=1000, max=2000, step=1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("Throttle:"),
                dcc.Input(id="throttle-input", type="number", value=1000, placeholder="Enter Throttle (1000-2000)", 
                         min=1000, max=2000, step=1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("Yaw:"),
                dcc.Input(id="yaw-input", type="number", value=1500, placeholder="Enter Yaw (1000-2000)", 
                         min=1000, max=2000, step=1),
            ], style={"marginBottom": "20px"}),
        ]),
        
        # PID Controls
        html.Div([
            html.H3("PID Values", style={"color": "#4CAF50"}),
            html.Div([
                html.Label("PID X:"),
                dcc.Input(id="pid-x-input", type="number", value=0, placeholder="Enter PID X", step=0.1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("PID Y:"),
                dcc.Input(id="pid-y-input", type="number", value=0, placeholder="Enter PID Y", step=0.1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("PID Z:"),
                dcc.Input(id="pid-z-input", type="number", value=0, placeholder="Enter PID Z", step=0.1),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Label("PID Yaw:"),
                dcc.Input(id="pid-yaw-input", type="number", value=0, placeholder="Enter PID Yaw", step=0.1),
            ], style={"marginBottom": "20px"}),
        ]),
        
        html.Button("Send Command", id="send-button", 
                   style={"backgroundColor": "#2196F3", "color": "white", "padding": "10px 20px"}),
        html.Div(id="command-status", style={"marginTop": "10px"}),
        
        # Command History
        html.Div([
            html.H3("Command History"),
            html.Pre(id="command-history", style={"maxHeight": "200px", "overflowY": "scroll"}),
        ], style={"marginTop": "20px"}),
    ], style={"marginTop": "20px", "padding": "20px", "border": "1px solid #ddd", "borderRadius": "5px"}),
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

def load_commands():
    """Load existing commands from file"""
    try:
        if os.path.exists(COMMAND_FILE_PATH) and os.path.getsize(COMMAND_FILE_PATH) > 0:
            with open(COMMAND_FILE_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []

# Modify the handle_command callback
@app.callback(
    [Output("command-status", "children"),
     Output("command-history", "children")],
    [Input("send-button", "n_clicks")],
    [
        State("roll-input", "value"),
        State("pitch-input", "value"),
        State("throttle-input", "value"),
        State("yaw-input", "value"),
        State("pid-x-input", "value"),
        State("pid-y-input", "value"),
        State("pid-z-input", "value"),
        State("pid-yaw-input", "value"),
    ]
)
def handle_command(n_clicks, roll_p, pitch_p, throttle_p, yaw_p, roll_i, pitch_i, throttle_i, yaw_i, roll_d, pitch_d, throttle_d, yaw_d):
    if n_clicks is None:
        commands = load_commands()
        return "", json.dumps(commands, indent=2)

    # Create a command dictionary
    new_command = {
        "pid_values": {
            "P": {
                "roll": float(roll_p) if roll_p else 0.0,
                "pitch": float(pitch_p) if pitch_p else 0.0,
                "throttle": float(throttle_p) if throttle_p else 0.0,
                "yaw": float(yaw_p) if yaw_p else 0.0,
            },
            "I": {
                "roll": float(roll_i) if roll_i else 0.0,
                "pitch": float(pitch_i) if pitch_i else 0.0,
                "throttle": float(throttle_i) if throttle_i else 0.0,
                "yaw": float(yaw_i) if yaw_i else 0.0,
            },
            "D": {
                "roll": float(roll_d) if roll_d else 0.0,
                "pitch": float(pitch_d) if pitch_d else 0.0,
                "throttle": float(throttle_d) if throttle_d else 0.0,
                "yaw": float(yaw_d) if yaw_d else 0.0,
            },
        }
    }


    try:
        # Load existing commands
        commands = load_commands()
        
        # Append new command
        commands.append(new_command)
        
        # Keep only last 100 commands to prevent file from growing too large
        commands = commands[-100:]
        
        # Write all commands to the text file
        with open(COMMAND_FILE_PATH, "w") as f:
            json.dump(commands, f, indent=2)
            
        # Update command history display
        return f"Command sent successfully! (Total commands: {len(commands)})", json.dumps(commands, indent=2)
    except Exception as e:
        return f"Error sending command: {e}", ""

# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)