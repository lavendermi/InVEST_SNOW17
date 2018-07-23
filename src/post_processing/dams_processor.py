import statistics as statistics
from osgeo import ogr


def process_dams_data(ws_shape, dams_shape):

    driver = ogr.GetDriverByName("ESRI Shapefile")

    # dams_shape = dams_shape
    dams_ds = driver.Open(dams_shape, 0)
    dams_layer = dams_ds.GetLayer()

    # ws_shape = ws_shape
    ws_ds = driver.Open(ws_shape, 0)
    ws_layer = ws_ds.GetLayer()

    # setup our return variables
    number_of_dams = 0
    purposes = []
    max_stor = []
    normal_sto = []

    for ws_features in ws_layer:
        ws_geometry = ws_features.GetGeometryRef()

        for dams_features in dams_layer:
            dams_geometry = dams_features.GetGeometryRef()
            if dams_geometry.Intersects(ws_geometry):
                number_of_dams += 1
                purposes.append(dams_features.GetField("PURPOSES"))
                max_stor.append(float(dams_features.GetField("MAX_STOR")))
                normal_sto.append(float(dams_features.GetField("NORMAL_STO")))

    try:
        purp = statistics.mode(purposes)
    except statistics.StatisticsError as ex:
        purp = ''

    return purp, sum(max_stor), sum(normal_sto), number_of_dams

