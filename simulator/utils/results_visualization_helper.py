import plotly.express as px
import plotly.offline as pio
import pandas as pd
import plotly.graph_objs as go

def create_pie_chart(data, title):
    df = pd.DataFrame(list(data))
    fig = px.pie(
        df, 
        values='count', 
        names='emotion', 
        title=title,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return pio.plot(fig, output_type='div', include_plotlyjs=True)

def create_emotion_intensity_bar_chart(data, title):
    df = pd.DataFrame(list(data))
    
    # Create bar chart with average intensity
    fig = go.Figure([
        go.Bar(
            x=df['emotion'], 
            y=df['avg_intensity'], 
            text=df['avg_intensity'].round(2),
            textposition='auto',
            marker_color=px.colors.qualitative.Pastel
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title='Emotion',
        yaxis_title='Average Intensity',
        yaxis_range=[0, 10]  # Assuming intensity is on a 0-10 scale
    )
    
    return pio.plot(fig, output_type='div', include_plotlyjs=True)