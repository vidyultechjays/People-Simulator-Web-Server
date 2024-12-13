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

def _parse_personality_traits(traits_dict):
    """
    Parse and format personality traits for display.
    """
    if not traits_dict:
        return {}

    formatted_traits = {}
    for key, value in traits_dict.items():
        if isinstance(value, list):
            formatted_traits[key] = ", ".join(map(str, value))
        elif isinstance(value, dict):
            formatted_traits[key] = ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            formatted_traits[key] = value

    return formatted_traits

def create_demographic_charts(category_type, categories):
    category_charts = {}
    for category, data in categories.items():
        if data.get('total', 0) > 0:
            chart_data = [
                {'emotion': 'Positive', 'count': data.get('positive_percentage', 0)},
                {'emotion': 'Negative', 'count': data.get('negative_percentage', 0)},
                {'emotion': 'Neutral', 'count': data.get('neutral_percentage', 0)}
            ]
            category_charts[category] = create_pie_chart(
                chart_data,
                f'{category_type.replace("_", " ").title()} - {category}'
            )
    return category_charts