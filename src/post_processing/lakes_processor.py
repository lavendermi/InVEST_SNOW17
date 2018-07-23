import statistics as statistics
from osgeo import ogr
import sys


def process_lakes_data(ws_shape, lakes_shape, country):

    driver = ogr.GetDriverByName("ESRI Shapefile")

    # dams_shape = dams_shape
    lakes_ds = driver.Open(lakes_shape, 0)
    lakes_layer = lakes_ds.GetLayer()
    if (country == 'CA'):
        lakes_layer.SetAttributeFilter("Country = 'Canada'")
    elif (country == 'US'):
        lakes_layer.SetAttributeFilter("Country = 'United States of America'")
    elif (country == 'AR'):
        lakes_layer.SetAttributeFilter("Country = 'Argentina'")

    # ws_shape = ws_shape
    ws_ds = driver.Open(ws_shape, 0)
    ws_layer = ws_ds.GetLayer()

    # setup our return variables
    number_of_lakes = 0
    lake_area = []
    vol_total = []
    depth_avg = []
    dis_avg = []
    res_time = []
    feature_count = ws_layer.GetFeatureCount()


    for ws_features in ws_layer:
        ws_geometry = ws_features.GetGeometryRef()

        for lakes_features in lakes_layer:
            lakes_geometry = lakes_features.GetGeometryRef()
            if lakes_geometry.Intersects(ws_geometry):
                number_of_lakes += 1
                lake_area.append(lakes_features.GetField("Lake_area"))
                vol_total.append(float(lakes_features.GetField("Vol_total")))
                depth_avg.append(float(lakes_features.GetField("Depth_avg")))
                dis_avg.append(float(lakes_features.GetField("Dis_avg")))
                res_time.append(float(lakes_features.GetField("Res_time")))

    try:
        mean_depth = statistics.mean(depth_avg)
    except statistics.StatisticsError as se:
        mean_depth = ''

    try:
        mean_dis = statistics.mean(res_time)
    except statistics.StatisticsError as se:
        mean_dis = ''

    return sum(lake_area), sum(vol_total), mean_depth, \
           sum(dis_avg), mean_dis, number_of_lakes, feature_count

