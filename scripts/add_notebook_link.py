import argparse
import sys

import omero
import omero.cli



NOTEBOOK_NAME = "idr0113_lineage.ipynb"
NAMESPACE = "openmicroscopy.org/idr/analysis/notebook"
REF_URL = "https://mybinder.org/v2/gh/IDR/idr0113-bottes-opcclones/HEAD?urlpath=notebooks%2Fnotebooks%2Fidr0113_lineage.ipynb%3FimageId%3D"


# Load the images in the project
def load_data(conn, project_id, delete):
    to_delete = []
    # load all the images in the project
    project = conn.getObject("Project", project_id)
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            # Check if image has ROIs
            if (image.getROICount() > 0):
                if (image.getAnnotation(ns=NAMESPACE) is None) and not delete:
                    add_link(conn, image)
                elif (image.getAnnotation(ns=NAMESPACE) is not None) and delete:
                    to_delete.append(image.getAnnotation(ns=NAMESPACE).getId())
    if to_delete:
        conn.deleteObjects('Annotation', to_delete, wait=True)


def add_link(conn, image):
    url = REF_URL + str(image.getId())
    key_value_data = [["Study Notebook", NOTEBOOK_NAME],
                      ["Study Notebook URL", url]]
    map_ann = omero.gateway.MapAnnotationWrapper(conn)
    map_ann.setValue(key_value_data)
    map_ann.setNs(NAMESPACE)
    map_ann.save()
    image.linkAnnotation(map_ann)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('id')
    parser.add_argument("-r",  "--remove", action="store_true", default=False,
    help="Remove the annotations")
    args = parser.parse_args(args)
    # Create a connection and load the images in the specified project
    with omero.cli.cli_login() as c:
        try:
            conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
            conn.c.enableKeepAlive(60)
            load_data(conn, args.id, args.remove)
        finally:
            conn.close()
            print("done")


if __name__ == "__main__":
    main(sys.argv[1:])

