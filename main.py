from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap5

from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from pyproj import Transformer
import pyproj.database

import pandas as pd

from bokeh.models import WMTSTileSource, ColumnDataSource
from bokeh.palettes import Category10, viridis
from bokeh.plotting import figure
from bokeh.io import output_notebook
import bokeh.embed

app = Flask(__name__)
app.secret_key = 'tO$&!|0wkamvVia0?n$NqIRVWOG'

# Bootstrap-Flask requires this line
bootstrap = Bootstrap5(app)
# Flask-WTF requires this line
csrf = CSRFProtect(app)

# with Flask-WTF, each web form is represented by a class
# "NameForm" can change; "(FlaskForm)" cannot
# see the route for "/" and "index.html" to see how this is used
class NameForm(FlaskForm):
    epsg_orig = StringField("epsg_orig", "") #"EPSG:4326"
    epsg_new = StringField("epsg_new", "") #"EPSG:3857"
    northing = TextAreaField("northing", "")
    easting = TextAreaField("easting", "")
    submit = SubmitField('Submit')

# list of EPSG valid coordinate transforms
def get_crs_list(): 
    crs_info_list = pyproj.database.query_crs_info(auth_name=None, pj_types=None) 
    crs_list = ["EPSG:" + info[1] for info in crs_info_list] 
    print(crs_list) 
    return sorted(crs_list)

def plot_map(asset_df,
    tile_name="OpenMap",
    plot_width=800,
    plot_height=800,
    marker_size=14):
    
    # See https://wiki.openstreetmap.org/wiki/Tile_servers for various tile services
    MAP_TILES = {
        "OpenMap": WMTSTileSource(url="http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png"),
        "ESRI": WMTSTileSource(
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg"
        ),
        "OpenTopoMap": WMTSTileSource(url="https://tile.opentopomap.org/{Z}/{X}/{Y}.png"),
    }

    # Use pyproj to transform longitude and latitude into web-mercator and add to a copy of the asset dataframe
    TRANSFORM_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

    asset_df["x"], asset_df["y"] = TRANSFORM_4326_TO_3857.transform(
        asset_df["latitude"], asset_df["longitude"]
    )
    asset_df["latlon"] = tuple(zip(asset_df["latitude"], asset_df["longitude"]))

    # Define default and then update figure and marker options based on kwargs
    figure_options = {
        "tools": "save,hover,pan,wheel_zoom,reset,help",
        "x_axis_label": "Longitude",
        "y_axis_label": "Latitude",
        "match_aspect": True,
        "tooltips": [("(Lat,Lon)", "@latlon"),
                     ("Old coord", "@old_coords"),
                     ("New coord", "@new_coords"),],
    }

    marker_options = {
        "marker": "circle_y",
        "line_width": 1,
        "alpha": 0.8,
        "fill_color": "blue",
        "line_color": "black",
    }

    # Create the bokeh data source without the "geometry" that isn't compatible with bokeh
    source = ColumnDataSource(asset_df)

    # Create a bokeh figure with tiles
    plot_map = figure(
        width=plot_width,
        height=plot_height,
        x_axis_type="mercator",
        y_axis_type="mercator",
        **figure_options,
    )

    plot_map.add_tile(MAP_TILES[tile_name])

    # Plot the asset devices
    plot_map.scatter(x="x", y="y", source=source, size=marker_size, **marker_options)

    return plot_map


# all Flask routes below
@app.route('/', methods=['GET', 'POST'])
def index():
    
    epsg_list = get_crs_list()
    # you must tell the variable 'form' what you named the class, above
    # 'form' is the variable name used in this template: index.html
    
    form = NameForm()
    
    message = ""
    output = ""

    if form.validate_on_submit():
        epsg_orig = form.epsg_orig.data
        epsg_new = form.epsg_new.data
        
        northing = form.northing.data.split(",")
        northings = [float(i) for i in northing]

        easting = form.easting.data.split(",")
        eastings = [float(i) for i in easting]

        if (epsg_orig.upper() in epsg_list) and (epsg_new.upper() in epsg_list):

            try:
                transform_new = Transformer.from_crs(epsg_orig, epsg_new)
                transform_latlon = Transformer.from_crs(epsg_orig, "EPSG:4326")

                lat,lon = transform_latlon.transform(northings,eastings)
                northing_new,easting_new = transform_new.transform(northings,eastings)

                output = f"Northings: {northing_new}, Eastings: {easting_new}"

                
                asset_df = pd.DataFrame.from_dict({"latitude":lat,"longitude":lon,
                                                   "old_northing":northings,"old_easting":eastings,
                                                   "new_northing":northing_new,"new_easting":easting_new})
                
                asset_df["old_coords"] = tuple(zip(asset_df["old_northing"], asset_df["old_easting"]))
                asset_df["new_coords"] = tuple(zip(asset_df["new_northing"], asset_df["new_easting"]))

                plot_coords = plot_map(asset_df)

                script, div = bokeh.embed.components(plot_coords)

            except:
                message = "Coordinate transform failed."
                message = northing
            
        else:
            message = "EPSG code is not in the database."

    return render_template('index.html', form=form, message=message, output=output, bokeh_script=script, bokeh_div=div)

# keep this as is
if __name__ == '__main__':
    app.run(debug=True)