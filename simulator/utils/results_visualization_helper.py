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
