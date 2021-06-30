import argparse
import mimetypes
import os
import pandas
import sys
import tempfile

from pathlib import Path

# dependency used to read ImageJ roi
from read_roi import read_roi_zip

# OMERO dependencies
import omero.cli
from omero.model import ImageI, PointI, RoiI
from omero.rtypes import (
    rdouble,
    rint,
    rstring,
)
from omero_metadata.populate import ParsingContext
from omero.util.metadata_utils import NSBULKANNOTATIONSRAW

# table columns to be linked to the image
columns = [
        "Roi",
        "Cell type",
        "Cell Uncertainty",
        "Mother Roi",
        "Mother Uncertainty",
        "Sister Roi",
        "Sister Uncertainty",
        "Cell Death"
    ]

cell_types = {"1": "OPCs", "2": "PM", "3": "M"}
uncertainty_types = {"1": "certain", "0-5": "semi-certain", "0": "uncertain"}


def handle_position(value):
    """
    Parse the position field of the ImageJ shape.
    """
    z = -1
    c = -1
    t = -1
    if (type(value) is dict):
        z = value.get("slice") - 1
        c = value.get("channel") - 1
        t = value.get("frame") - 1
    return (z, c, t)


def convert_point(value):
    """
    Convert the ImageJ point into OMERO point
    """
    x_coordinates = value.get("x")
    y_coordinates = value.get("y")
    (z, c, t) = handle_position(value.get("position"))
    name = value.get("name")
    slices = value.get("slices")
    roi = RoiI()
    for i in range(len(x_coordinates)):
        point = PointI()
        point.x = rdouble(x_coordinates[i])
        point.y = rdouble(y_coordinates[i])
        point.theZ = rint(z)
        point.theT = rint(t)
        point.textValue = rstring(name)
        roi.addShape(point)
    return roi


def process_rois(conn, image, path, roi_zip_name):
    """
    Parse the roi corresponding to the specified image. 
    """
    roi_ids = {}
    to_parse = {}
    for zip_file in os.listdir(path):
        if zip_file.startswith(roi_zip_name):
            roi = read_roi_zip(os.path.join(path, zip_file))
            for key, value in roi.items():
                omero_roi = convert(conn, image, value, roi_ids)
                name = value.get("name").lower()
                to_parse.update({omero_roi.getId().getValue(): name})
    
    return populate_dataframe(roi_ids, to_parse)


def populate_dataframe(roi_ids, to_parse):
    df = pandas.DataFrame(columns=columns)
    for id, name in to_parse.items():
        values = name.split("_")
        cell_id = values[0]
        mother_id = values[3]
        sister_id = values[6]
        omero_mother_id = ""
        omero_sister_id = ""
        if mother_id != "na":
            omero_mother_id = str(roi_ids.get(mother_id))
        else:
            print("no mother")
        if sister_id != "na":
            omero_sister_id = str(roi_ids.get(sister_id))
        else:
            print("no sister")
        cell_type = cell_types.get(values[1])
        uncertainty_type = uncertainty_types.get(values[4])
        uncertainty_mother_type = uncertainty_types.get(values[5])
        uncertainty_sister_type = uncertainty_types.get(0)
        cell_death = ""
        if len(values) == 8:
            uncertainty_sister_type = uncertainty_types.get(values[7])
        if len(values) == 9:
            cell_death = "yes"

        df.loc[len(df)] = (id, cell_type,
                           uncertainty_type, omero_mother_id,
                           uncertainty_mother_type, omero_sister_id,
                           uncertainty_sister_type, cell_death)

    return df


def convert(conn, image, value, roi_ids):
    """
    Convert the ImageJ shapes into OMERO shapes.
    Add the metadata to the dataframe
    """
    roi_type = value.get("type").lower()
    name = value.get("name").lower()
    values = name.split("_")
    cell_id = values[0]
    if roi_type == "point":
        omero_roi = convert_point(value)
        omero_roi.setName(rstring(name))
        omero_roi.setImage(ImageI(image.getId(), False))
        omero_roi = conn.getUpdateService().saveAndReturnObject(omero_roi)
        roi_ids.update({cell_id: omero_roi.getId().getValue()})
        return omero_roi


def populate_metadata(conn, image, file_path, file_name):
    """
    Create OMERO.table from the CSV.
    """
    mt = mimetypes.guess_type(file_name, strict=False)[0]
    # originalfile path will be ''
    fileann = conn.createFileAnnfromLocalFile(
        file_path, origFilePathAndName=file_name, mimetype=mt, ns=NSBULKANNOTATIONSRAW
    )
    fileid = fileann.getFile().getId()
    # image.linkAnnotation(fileann)
    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, fileid=fileid, file=file_path, allow_nan=True
    )
    ctx.parse()


def parse_dir(conn, directory):
    """
    Parse the files contained the directory.
    The name of each file should allow us to find the corresponding image.
    """
    query_svc = conn.getQueryService()
    svc = conn.getUpdateService()
    for subdir, dirs, files in os.walk(directory):
        for f in Path(subdir).glob('*.tif'):
            file_name = os.path.basename(os.path.normpath(f))
            dir_path = os.path.dirname(f)
            roi_dir_name = os.path.basename(os.path.normpath(dir_path)) + "_ROIs"
            roi_zip_name = file_name.replace("Image5D_", "").replace(".tif", "")
            path = os.path.join(dir_path, roi_dir_name)
            print(file_name)
            query = "select i from Image i where i.name like '%s'" % file_name
            images = query_svc.findAllByQuery(query, None)
            if len(images) == 0:
                print("image not found")
                continue
            else:
                print("processing roi")
                for index in range(len(images)):
                    image = conn.getObject("Image", images[index].getId())
                    # find the corresponding roi files
                    df = process_rois(conn, image, path, roi_zip_name)
                    iid = image.getId()
                    csv_name = f"{iid}.csv"
                    csv_path = os.path.join(tempfile.gettempdir(), csv_name)
                    df.to_csv(csv_path, index=False)
                    # Create an OMERO.table from csv
                    populate_metadata(conn, image, csv_path, csv_name)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('inputdir')
    args = parser.parse_args(args)
    # Create a connection and scan the inputdir
    with omero.cli.cli_login() as c:
        try:
            conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
            conn.c.enableKeepAlive(60)
            parse_dir(conn, args.inputdir)
        finally:
            conn.close()
            print("done")


if __name__ == "__main__":
    main(sys.argv[1:])
