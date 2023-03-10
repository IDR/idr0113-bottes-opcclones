# idr0113-bottes-opcclones

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/IDR/idr0113-bottes-opcclones/main?urlpath=notebooks%2Fnotebooks%2Fidr0113_lineage.ipynb%3FimageId%3D13425213)

After importing the data, the following steps need to be run to set the pixels size,
the time information and convert the ROIs.

Before running any of the steps below, you must activate the virtual environment where the OMERO dependencies are installed.

Pixels size
-----------

The pixels size needs to be set after import, run:

```
omero metadata pixelsize --x 2.21645 --y 2.21645 Project:$ID
```

Replace $ID by the project ID for the experiment ``idr0113-bottes-opcclones``.


ROIs
----

* As root, in the virtual environment where all the dependenices are installed, run:


```
pip install -r requirements.txt
```

You can now run the script [roi_converter.py](scripts/roi_converter.py) to
convert the ImageJ ROIs. The script takes the absolute path to the folder containing all the data
e.g. ```python roi_converter.py /uod/idr/filesets/idr0113-bottes-opcclones/20210607-ftp/```.

Time
----

To create the time information the file [timelapse.tsv](experimentA/timelapse.tsv) 
is parsed.

Run the script specifying the inputfile and the project ID.

Add Notebook Link
-----------------

To add a link to the images with ROIs, run [add_notebook_link.py](scripts/add_notebook_link.py)
specifying the project ID as a parameter.


Export tracks to OME-NGFF
-------------------------

To export a sample image as an OME-NGFF with tracks stored in AnnData tables
for viewing in `napari`. First, use `omero-cli-zarr` plugin to export the Image:

    $ omero zarr export Image:13425213

We need `ome-ngff-tables-prototype` and it is safest to pin to a known commit:

    $ pip install git+https://github.com/kevinyamauchi/ome-ngff-tables-prototype.git@51cc60e22807e67253ffcbebbe6dabb597fb94dd
    $ python path/to/notebooks/idr0113_to_ngff_table.py

Then open in napari:

    $ napari --plugin napari-ome-zarr 13425213.zarr
