from shiny import App, render, ui
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json
import requests

collapsed_df_hour = pd.read_csv("/Users/benzhang/Documents/GitHub/PS6_Ben/top_alerts_map_byhour/basic-app/top_alerts_map_byhour.csv")
collapsed_df_hour["type_subtype"] = collapsed_df_hour["updated_type"] + " - " + collapsed_df_hour["updated_subtype"]
type_subtype_combinations = sorted(collapsed_df_hour["type_subtype"].unique())

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)

file_path = "chicago_neighborhoods.geojson"
with open(file_path, 'wb') as file:
    file.write(response.content)

with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson["features"])
collapsed_df_hour['hour'] = collapsed_df_hour['hour'].apply(lambda x: int(x.split(':')[0]))

app_ui = ui.page_fluid(
    ui.input_select(
        id="type_subtype",
        label="Select Alert Type and Subtype:",
        choices=type_subtype_combinations,
        selected=type_subtype_combinations[0]
    ),
    ui.input_switch(
        id="switch",
        label="Toggle to switch to range of hours",
        value=False
    ),
    ui.output_ui("single_hour_slider"),
    ui.output_ui("hour_range_slider"),
    output_widget("top_alerts_plot")
)

def server(input, output, session):
    @output
    @render.ui
    def single_hour_slider():
        if not input.switch():
            return ui.input_slider(
                id="single_hour",
                label="Select Hour:",
                min=0,
                max=23,
                value=6,
                step=1
            )
        return None

    @output
    @render.ui
    def hour_range_slider():
        if input.switch():
            return ui.input_slider(
                id="hour_range",
                label="Select Hour Range:",
                min=0,
                max=23,
                value=(6, 9),
                step=1
            )
        return None

    @output
    @render_altair
    def top_alerts_plot():
        selected_type, selected_subtype = input.type_subtype().split(" - ")
        if input.switch():
            start_hour, end_hour = input.hour_range()
        else:
            start_hour = end_hour = input.single_hour()
        if input.switch():
            filtered_df_hour_range = collapsed_df_hour[
                (collapsed_df_hour['updated_type'] == selected_type) & 
                (collapsed_df_hour['updated_subtype'] == selected_subtype) & 
                (collapsed_df_hour['hour'] >= start_hour) & 
                (collapsed_df_hour['hour'] < end_hour)
            ]
        else:
            filtered_df_hour_range = collapsed_df_hour[
                (collapsed_df_hour['updated_type'] == selected_type) & 
                (collapsed_df_hour['updated_subtype'] == selected_subtype) & 
                (collapsed_df_hour['hour'] == start_hour)
            ]
        aggregated_alerts = filtered_df_hour_range.groupby(['latitude_bin', 'longitude_bin'])['alert_count'].sum().reset_index()
        top_alerts = aggregated_alerts.sort_values('alert_count', ascending=False).head(10)
        if top_alerts.empty:
            return alt.Chart().mark_text(
                text="No data available for the selected combination and hour range.",
                align='center',
                baseline='middle',
                size=20
            ).properties(width=600, height=400)
        lat_min, lat_max = top_alerts['latitude_bin'].min() - 0.02, top_alerts['latitude_bin'].max() + 0.02
        long_min, long_max = top_alerts['longitude_bin'].min() - 0.02, top_alerts['longitude_bin'].max() + 0.02
        scatter_plot = alt.Chart(top_alerts).mark_circle(size=80, color='blue', opacity=0.7).encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[long_min, long_max])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[lat_min, lat_max])),
            size=alt.Size('alert_count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'alert_count']
        ).properties(
            title=f'Top 10 Locations for {selected_type} - {selected_subtype} ({start_hour}:00-{end_hour}:00)',
            width=600,
            height=600
        )
        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0.3,
            stroke=None
        ).encode(
            tooltip=["properties.neighborhood:N"]
        ).project(
            type="identity", reflectY=True
        ).properties(
            width=600,
            height=600
        )
        return map_layer + scatter_plot

app = App(app_ui, server)
