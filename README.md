# idr0113-bottes-opcclones

Pixels size
-----------

The pixels size needs to be set after import, run:

```
omero metadata pixelsize --x 2.21645 --y 2.21645 Project:$ID
```

Replace $ID.

ROIs
----

* Activate the virtual environment where the OMERO dependencies are installed.

* Run:

```
pip install -r requirements.txt
```

You can now run the script [roi_converter.py](scripts/roi_converter.py) to
convert the ImageJ ROIs. The script takes the absolute path to the folder containing all the data
e.g. ```/uod/idr/filesets/idr0113-bottes-opcclones/20210607-ftp/```.
