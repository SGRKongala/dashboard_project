# Update your dash imports
from flask import Flask
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State  # Added State here
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

def load_data():
    try:
        # Create a new connection each time
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql('SELECT * FROM main_data', conn)
            df_rpm = pd.read_sql('SELECT * FROM rpm', conn)
            df1 = pd.read_sql('SELECT * FROM corruption_status', conn)
            
            # Merge dataframes
            merged_df1 = pd.merge(df, df1, on='id', how='inner')
            merged_df2 = pd.merge(df, df_rpm, on='id', how='inner')
            
            # Convert time columns
            merged_df1['time'] = pd.to_datetime(merged_df1['time'])
            merged_df2['time'] = pd.to_datetime(merged_df2['time'])
            
            return merged_df1, merged_df2
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise

# Load initial data
merged_df1, merged_df2 = load_data()


# Get unique years from the dataset
years = sorted(merged_df1['time'].dt.year.unique())

# Define all channel-sensor combinations
sensors = []
for ch in ['ch1', 'ch2', 'ch3']:
    for s in ['s1', 's2', 's3', 's4', 's5', 's6']:
        sensors.append(f'{ch}{s}')

app.layout = html.Div([
    html.H1("Weekly Sensor Performance Dashboard"),
    
    html.Div([
        html.Div([
            html.H3("Select Year"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(year), 'value': year} for year in years],
                value=years[0],
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),
        
        html.Div([
            html.H3("Select Channel-Sensor"),
            dcc.Dropdown(
                id='sensor-dropdown',
                options=[{'label': sensor, 'value': sensor} for sensor in sensors],
                value=sensors[0],
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block'}),
    ]),
    
    dcc.Graph(id='weekly-heatmap')
])

@app.callback(
    Output('weekly-heatmap', 'figure'),
    [Input('year-dropdown', 'value'),
     Input('sensor-dropdown', 'value')]
)
def update_heatmap(selected_year, selected_sensor):
    # Filter data for selected year
    mask = merged_df1['time'].dt.year == selected_year
    df_year = merged_df1[mask].copy()
    
    # Add week number to the dataframe
    df_year['week'] = df_year['time'].dt.isocalendar().week
    
    # Count actual corruption markings (1s) for the selected sensor
    df_year['is_corrupted'] = (df_year[selected_sensor] == 1).astype(int)
    
    # Group by week and calculate metrics
    weekly_stats = df_year.groupby('week').agg({
        'id': 'count',  # Total samples
        'is_corrupted': 'sum'  # Count of corruption markings (1s)
    }).reset_index()
    
    # Calculate corruption percentage
    weekly_stats['corruption_percentage'] = (weekly_stats['is_corrupted'] / weekly_stats['id'] * 100)
    
    # Create a complete range of weeks (1-53)
    all_weeks = pd.DataFrame({'week': range(1, 54)})
    weekly_stats = pd.merge(all_weeks, weekly_stats, on='week', how='left')
    weekly_stats = weekly_stats.fillna(0)
    
    # Reshape data into a matrix (7 rows x 8 columns to show 53 weeks)
    # Reverse the row order so week 1 starts at the top
    matrix_data = np.zeros((7, 8))  # Initialize with zeros
    matrix_text = np.empty((7, 8), dtype='object')  # For text labels
    
    for i in range(53):
        row = 6 - (i // 8)  # Reverse row order
        col = i % 8
        if i < len(weekly_stats):
            matrix_data[row, col] = weekly_stats['corruption_percentage'].iloc[i]
            total_samples = weekly_stats['id'].iloc[i]
            corrupted_count = weekly_stats['is_corrupted'].iloc[i]
            week_num = weekly_stats['week'].iloc[i]
            matrix_text[row, col] = f'Week {week_num}<br>{int(total_samples)} total<br>{int(corrupted_count)} corrupted'
    
    # Create figure
    fig = go.Figure()
    
    # Add heatmap trace
    fig.add_trace(go.Heatmap(
        z=matrix_data,
        text=matrix_text,
        texttemplate="%{text}<br>%{z:.1f}% corrupted",
        textfont={"size": 10},
        colorscale=[
            [0, 'green'],     # 0% corruption
            [0.5, 'yellow'],  # 50% corruption
            [1, 'red']        # 100% corruption
        ],
        showscale=True,
        colorbar=dict(title='Corruption %'),
        zmin=0,  # Set minimum value to 0
        zmax=100  # Set maximum value to 100 since it's a percentage
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Weekly Corruption Status for {selected_sensor} ({selected_year})',
        height=800,
        width=1200,
        showlegend=False,
    )
    
    # Update axes
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8052)