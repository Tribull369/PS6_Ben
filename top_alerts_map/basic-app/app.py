from shiny import App, render, ui
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json
import requests

merged_df = pd.read_csv("merged_df.csv")
merged_df["type_subtype"] = merged_df["updated_type"] + " - " + merged_df["updated_subtype"]
type_subtype_combinations = sorted(merged_df["type_subtype"].unique())

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)
file_path = "chicago_neighborhoods.geojson"
with open(file_path, 'wb') as file:
    file.write(response.content)
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson["features"])

def get_top_alerts(selected_type, selected_subtype):
    filtered_df = merged_df[
        (merged_df['updated_type'] == selected_type) &
        (merged_df['updated_subtype'] == selected_subtype)
    ]
    collapsed_df = (
        filtered_df.groupby(['latitude_bin', 'longitude_bin'])
        .size()
        .reset_index(name='alert_count')
    )
    top_alerts = collapsed_df.sort_values('alert_count', ascending=False).head(10)
    return top_alerts

ui = ui.page_fluid(
    ui.input_select(
        id="alert_type_subtype",
        label="Select Alert Type and Subtype",
        choices=type_subtype_combinations,
        selected=type_subtype_combinations[0]
    ),
    output_widget("top_alerts_plot")
)

def server(input, output, session):
    @output
    @render_altair
    def top_alerts_plot():
        selected_type, selected_subtype = input.alert_type_subtype().split(" - ")
        top_alerts = get_top_alerts(selected_type, selected_subtype)
        lat_min, lat_max = top_alerts['latitude_bin'].min() - 0.02, top_alerts['latitude_bin'].max() + 0.02
        long_min, long_max = top_alerts['longitude_bin'].min() - 0.02, top_alerts['longitude_bin'].max() + 0.02

        scatter_plot = alt.Chart(top_alerts).mark_circle().encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[long_min, long_max])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[lat_min, lat_max])),
            size=alt.Size('alert_count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'alert_count']
        ).properties(
            title=f'Top 10 Locations for {selected_type} - {selected_subtype} Alerts',
            width=600,
            height=600
        )

        map_layer = alt.Chart(geo_data).mark_geoshape(fillOpacity=0.3).encode(
            tooltip=["properties.neighborhood:N"]
        ).project(type='identity', reflectY=True).properties(
            width=600,
            height=600
        )

        return map_layer + scatter_plot

app = App(ui, server)
