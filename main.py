# https://realpython.com/python-web-applications/

from flask import Flask
from flask import request

from pyproj import Transformer

app = Flask(__name__)

@app.route("/")
def index():

    epsg_orig = request.args.get("epsg_orig", "") #"EPSG:4326"
    epsg_new = request.args.get("epsg_new", "") #"EPSG:3857"
    northing = request.args.get("northing", "")
    easting = request.args.get("easting", "")

    

    if (epsg_orig and epsg_new and northing and easting):
        transform = Transformer.from_crs(epsg_orig, epsg_new)
        northing_new,easting_new = transform.transform(northing,easting)

    else:
        northing_new = ""
        easting_new = ""

    return (
        """<form action="" method="get"><br>
                EPSG original: <input type="text" name="epsg_orig"><br>
                EPSG new: <input type="text" name="epsg_new"><br>
                Northing: <input type="text" name="northing"><br>
                Easting: <input type="text" name="easting"><br>
                <input type="submit" value="Convert coordinates"><br>
            </form>"""
        + "<br>Northing: "
        + str(northing_new)
        + "<br>Easting: "
        + str(easting_new)

    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)