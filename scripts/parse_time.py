import argparse
import pandas as pd
import sys
import omero
import omero.cli


def get_plane_info(conn, pixels_id):
    query = "from PlaneInfo as Info where pixels.id='" + \
        str(pixels_id) + "' orderby info.theT"
    info_list = conn.getQueryService().findAllByQuery(query, None)
    map = {}
    for info in info_list:
        map[info.theT.getValue()] = info
    return map


def set_planeinfo(conn, image, values):
    if len(values) == image.getSizeT():
        pixels = image.getPrimaryPixels()
        planes_info = get_plane_info(conn, pixels.getId())
        for index, row in values.iterrows():
           day = row['DayAfterInduction'].replace("d", "")
           time = int(day) * 24 * 3600 #  unit in seconds
           info = planes_info.get(int(row['TimePoint'] - 1))
    else:
       print(image.getName())


def parse_file(conn, file, project_id):
    df = pd.read_csv (file, sep = '\t')
    # load all the images in the project
    project = conn.getObjects("Project", project_id)
    for image in conn.getObjects('Image', opts={'project': project_id}):
        values = df.loc[df['ImageName'] == image.getName()]
        set_planeinfo(conn, image, values)



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
