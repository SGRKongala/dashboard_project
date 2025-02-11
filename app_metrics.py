# Update your dash imports
from flask import Flask
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import sqlite3
import pandas as pd
import os
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Initialize Flask
server = Flask(__name__)

# Initialize Dash
app = dash.Dash(__name__, server=server)

# Database path
DB_PATH = os.path.join('data', 'text.db')

# Add database path verification
if not os.path.exists(DB_PATH):
    print(f"Database file not found at: {DB_PATH}")
    print(f"Current working directory: {os.getcwd()}")

# Data Loading and Preprocessing
def load_data(metric='std_dev'):
    try:
        # Create a new connection each time (don't use the global conn)
        with sqlite3.connect(DB_PATH) as conn:
            # Load main datasets
            print(f"Loading data for metric: {metric}")
            df = pd.read_sql('SELECT * FROM main_data', conn)
            print(f"main_data rows: {len(df)}")
            
            df_rpm = pd.read_sql('SELECT * FROM rpm', conn)
            print(f"rpm data rows: {len(df_rpm)}")
            
            df1 = pd.read_sql(f'SELECT * FROM {metric}', conn)
            print(f"{metric} data rows: {len(df1)}")
            
            # Merge dataframes
            merged_df1 = pd.merge(df, df1, on='id', how='inner')
            print(f"merged_df1 rows after first merge: {len(merged_df1)}")
            
            merged_df2 = pd.merge(df, df_rpm, on='id', how='inner')
            print(f"merged_df2 rows after second merge: {len(merged_df2)}")
            
            # Convert time columns
            merged_df1['time'] = pd.to_datetime(merged_df1['time'])
            merged_df2['time'] = pd.to_datetime(merged_df2['time'])
            
            return merged_df1, merged_df2, metric
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise

# Define available metrics
AVAILABLE_METRICS = ['std_dev', 'rms', 'iqr', 'clean_max', 'clean_min', 'clean_range', 
                    'outlier_count', 'skewness', 'simpson', 'trapz', 'std_error']

# Load initial data with std_dev as default
merged_df1, merged_df2, metric = load_data(metric='std_dev')

# Constants
SENSORS = ['s1', 's2', 's3', 's4', 's5', 's6']
BINS = np.arange(0, 18, 0.5)
CHANNELS = ['ch1', 'ch2', 'ch3']
COLORS = {'ch1': 'blue', 'ch2': 'red', 'ch3': 'green'}

# Calculate default y-limits
def calculate_y_limits():
    all_values = []
    for ch in CHANNELS:
        for s in SENSORS:
            col = f'{ch}{s}'
            all_values.extend(merged_df1[col].dropna().values)
    return np.percentile(all_values, [2.5, 97.5])

y_min, y_max = calculate_y_limits()

# App Layout
app.layout = html.Div([
    html.H1("Sensor Data Analysis Dashboard"),
    
    # Add Metric Selection Dropdown
    html.Div([
        html.H3("Select Metric"),
        dcc.Dropdown(
            id='metric-dropdown',
            options=[{'label': metric.replace('_', ' ').title(), 'value': metric} 
                    for metric in AVAILABLE_METRICS],
            value='std_dev',  # Set default value
            clearable=False
        )
    ], style={'width': '30%', 'marginBottom': '20px'}),
    
    # Control Panel
    html.Div([
        # Sensor Selection
        html.Div([
            html.H3("Select Sensor"),
            dcc.Dropdown(
                id='sensor-dropdown',
                options=[{'label': f'Sensor {s}', 'value': s} for s in SENSORS],
                value=SENSORS[0],
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),
        
        # Channel Selection - Now allows multiple channels
        html.Div([
            html.H3("Select Channels"),
            dcc.Dropdown(
                id='channel-dropdown',
                options=[{'label': f'Channel {ch}', 'value': ch} for ch in CHANNELS],
                value=[CHANNELS[0]], # Default to first channel
                multi=True, # Allow multiple selections
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),
        
        # RPM Selection
        html.Div([
            html.H3("Select RPM Bin"),
            dcc.Dropdown(
                id='rpm-dropdown',
                options=[{'label': f'{b}-{b+0.5} RPM', 'value': b} for b in BINS[:-1]],
                value=10.0,
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),
        
        # Moving Average Control
        html.Div([
            html.H3("Moving Average Window (Days)"),
            dcc.Slider(
                id='ma-slider',
                min=1, max=30, step=1, value=1,
                marks={i: str(i) for i in [1,7,14,21,30]},
            )
        ], style={'width': '30%', 'display': 'inline-block'})
    ]),
    
    # Y-Axis Controls
    html.Div([
        html.H3("Y-Axis Limits"),
        html.Div([
            dcc.Input(id='y-min-input', type='number', value=y_min, step=0.1,
                     style={'width': '100px', 'marginRight': '10px'}),
            dcc.Input(id='y-max-input', type='number', value=y_max, step=0.1,
                     style={'width': '100px'})
        ])
    ], style={'marginTop': '20px'}),
    
    # Date Range Selection
    html.Div([
        html.H3("Select Date Range"),
        dcc.DatePickerRange(
            id='date-picker',
            start_date=merged_df1['time'].min().date(),
            end_date=merged_df1['time'].max().date(),
            display_format='YYYY-MM-DD'
        )
    ], style={'marginTop': '20px'}),
    
    # Graph and Download Section
    dcc.Graph(id='sensor-graph'),
    html.Button("Download Graph", id="btn-download"),
    dcc.Download(id="download-graph")
])


# Update the callback to include metric selection
@app.callback(
    Output('sensor-graph', 'figure'),
    [Input('metric-dropdown', 'value'),  # Add this line
     Input('sensor-dropdown', 'value'),
     Input('rpm-dropdown', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date'),
     Input('y-min-input', 'value'),
     Input('y-max-input', 'value'),
     Input('ma-slider', 'value')]
)
def update_graph(selected_metric, selected_sensor, rpm_bin, start_date, end_date, y_min, y_max, ma_days):
    # Load data with selected metric
    merged_df1, merged_df2, metric = load_data(metric=selected_metric)
    
    # Date filtering
    mask = (merged_df1['time'].dt.date >= pd.to_datetime(start_date).date()) & \
           (merged_df1['time'].dt.date <= pd.to_datetime(end_date).date())
    df_filtered = merged_df1[mask].sort_values('time')
    
    # RPM filtering
    rpm_mask = (merged_df2['ch1s1'] >= rpm_bin) & (merged_df2['ch1s1'] < (rpm_bin + 0.5))
    rpm_filtered = merged_df2[rpm_mask].sort_values('time')
    
    # Combine filtered data
    final_df = pd.merge(df_filtered, rpm_filtered[['id', 'time']], on=['id', 'time'])
    final_df = final_df.sort_values('time')
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for each channel
    for ch in CHANNELS:
        col_name = f'{ch}{selected_sensor}'
        ma_window = f'{ma_days}D'
        ma_data = final_df.set_index('time')[col_name].resample('D').mean().rolling(
            window=ma_days, min_periods=1).mean()
        
        fig.add_trace(go.Scatter(
            x=ma_data.index,
            y=ma_data.values,
            mode='lines+markers',
            name=f'Channel {ch} ({ma_days}-day MA)',
            line=dict(color=COLORS[ch], width=1.5, shape='linear'),
            marker=dict(color=COLORS[ch], size=5),
            connectgaps=True,
            opacity=0.6
        ))
    
    # Update layout
    fig.update_layout(
        title=f'{selected_metric.replace("_", " ").title()} - Sensor {selected_sensor} Data for RPM {rpm_bin}-{rpm_bin+0.5} ({ma_days}-day Moving Average)',
        xaxis_title='Time',
        yaxis_title='Value',
        yaxis=dict(range=[y_min, y_max]),
        showlegend=True,
        height=600,
        legend_title='Channel'
    )
    
    return fig


# Also update the download callback to use selected_metric
@app.callback(
    Output("download-graph", "data"),
    Input("btn-download", "n_clicks"),
    [State('metric-dropdown', 'value'),  # Add this line
     State('sensor-dropdown', 'value'),
     State('rpm-dropdown', 'value'),
     State('ma-slider', 'value'),
     State('sensor-graph', 'figure')],
    prevent_initial_call=True
)
def download_graph(n_clicks, selected_metric, selected_sensor, rpm_bin, ma_days, figure):
    if n_clicks:
        filename = f'{selected_metric}_Sensor_{selected_sensor}_RPM_{rpm_bin}-{rpm_bin+0.5}_MA_{ma_days}days.png'
        img_bytes = go.Figure(figure).to_image(
            format='png',
            width=1920,
            height=1080,
            scale=2.0,
            engine='kaleido'
        )
        return dcc.send_bytes(img_bytes, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  
    app.run(host="0.0.0.0", port=port)