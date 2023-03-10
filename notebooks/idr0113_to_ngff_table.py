
import requests
import pandas as pd
import numpy as np
import anndata as ad
from scipy.sparse import csr_matrix
from ome_zarr.io import parse_url
import zarr
from ngff_tables_prototype.writer import write_table_regions

from omero.cli import cli_login
from omero.gateway import BlitzGateway

imageId = 13425213

ROI_URL = "https://idr.openmicroscopy.org/api/v0/m/images/{key}/rois/?limit=500"
TABLE_URL = "https://idr.openmicroscopy.org/webgateway/table/Image/{key}/query/?query=*"


def process_image(conn, imageId):
    image = conn.getObject("Image", imageId)
    pixels_id = image.getPrimaryPixels().getId()
    query = "from PlaneInfo as Info where pixels.id='" + str(pixels_id) + "'"
    infos = conn.getQueryService().findAllByQuery(query, None)

    times = {}
    for i in infos:
        times.update({i.theT.getValue(): int(i.deltaT.getValue())})

    # create http session
    with requests.Session() as session:
        prepped = session.prepare_request(request)
        response = session.send(prepped)
        if response.status_code != 200:
            response.raise_for_status()

    qs = {'key': imageId}
    url = ROI_URL.format(**qs)
    json_data = session.get(url).json()

    # Look-up shapes from their ROI ID
    roi_map = {}
    # parse the json
    for d in json_data['data']:
        roi_id = d['@id']
        for s in d["shapes"]:
            # Assume only ONE shape per ROI
            roi_map.update({roi_id: s})

    url = TABLE_URL.format(**qs)
    json_data = session.get(url).json()

    df = pd.DataFrame(columns=json_data['data']['columns'])
    for r in json_data['data']['rows']:
        df.loc[len(df)] = r

    roi_ids = df["Roi"].tolist()

    # Use "Roi" column as index...
    col = df.loc[:, 'Roi']
    col.transpose()

    # Add ROIs (shapes) to X table and obs table
    X_df = pd.DataFrame({c: pd.Series(dtype='float') for c in ["t", "z", "y", "x"]}, index = col.astype(str))

    obs_columns = ["Cell Type", "Cell Uncertainty", "Mother Uncertainty", "Sister Uncertainty", "Roi Name"]
    obs_df = pd.DataFrame(columns=obs_columns, index = col.astype(str))


    # create sparse data...
    row_count = len(roi_ids)
    sparse_grid = np.zeros((row_count, row_count), dtype=np.int8)


    for index, row in df.iterrows():
        id = str(row["Roi"])
        shape = roi_map[row["Roi"]]

        # get coordinates for X
        dims = ["TheT", "TheZ", "Y", "X"]
        values = [shape.get(dim) for dim in dims]
        # roi id as index
        X_df.loc[id] = values

        # other columns for obs
        obs_values = [row[col] for col in obs_columns]
        obs_df.loc[id] = obs_values

        # lineage between points - save to sparse_grid
        lineage = row["Lineage Roi"]
        mother = row["Mother Roi"]
        to_idx = roi_ids.index(row["Roi"])
        from_id = None
        if lineage != "":
            from_id = int(lineage)
        elif mother != "":
            from_id = int(mother)

        if from_id is not None:
            from_idx = roi_ids.index(from_id)
            sparse_grid[from_idx, to_idx] = 1


    print(X_df)

    print(obs_df)

    print(sparse_grid)

    adata = ad.AnnData(X = X_df, obs = obs_df)

    # write as sparse data to obsp
    adata.obsp["tracking"] = csr_matrix(sparse_grid)

    store = parse_url(str(imageId) + ".zarr", mode="w").store
    root = zarr.group(store=store)

    tables_group = root.create_group(name="tables")
    write_table_regions(
        group=tables_group,
        adata=adata,
        region="labels/label_image",
        region_key=None,
        instance_key="cell_id"
    )


def main(args):
    # parser = argparse.ArgumentParser()
    # parser.add_argument('image', type=int)
    # args = parser.parse_args(args)
    # dataset_id = args.dataset

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        # image = conn.getObjects('Image', opts={'dataset': dataset_id})

        process_image(conn, imageId)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
