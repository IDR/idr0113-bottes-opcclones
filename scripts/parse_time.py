import argparse
import pandas as pd
import sys
import omero
import omero.cli
from omero.rtypes import rint
from omero.model import PixelsI, PlaneInfoI, TimeI


def populate_planeinfo(conn, image, values):
    pixels = image.getPrimaryPixels()
    planes = []
    for index, row in values.iterrows():
        day = row['DayAfterInduction'].replace("d", "")
        t = int(row['TimePoint'] - 1)
        if t < image.getSizeT():
            for c in range(0, image.getSizeC()):
                for z in range(0, image.getSizeZ()):
                    plane = PlaneInfoI()
                    plane.theT = rint(t)
                    plane.theC = rint(c)
                    plane.theZ = rint(z)
                    time = TimeI()
                    time.setValue(int(day))
                    time.setUnit(omero.model.enums.UnitsTime.DAY)
                    plane.deltaT = time
                    plane.setPixels(PixelsI(pixels.getId(), False))
                    planes.append(plane)
    # save the planes
    conn.getUpdateService().saveAndReturnArray(planes)


def parse_file(conn, file, project_id):
    df = pd.read_csv(file, sep='\t')
    # load all the images in the project
    project = conn.getObject("Project", project_id)
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            values = df.loc[df['ImageName'] == image.getName()]
            populate_planeinfo(conn, image, values)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('inputfile')
    parser.add_argument('id')
    args = parser.parse_args(args)
    # Create a connection and scan the inputdir
    with omero.cli.cli_login() as c:
        try:
            conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
            conn.c.enableKeepAlive(60)
            parse_file(conn, args.inputfile, args.id)
        finally:
            conn.close()
            print("done")


if __name__ == "__main__":
    main(sys.argv[1:])
