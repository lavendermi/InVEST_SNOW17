from osgeo import gdal


def process_dem_data(ws_shape_path, dem_raster_path):

    temp_DEM_path = 'temp_DEM.tif'
    clip_raster(ws_shape_path, dem_raster_path, temp_DEM_path)

    src_ds = gdal.Open(temp_DEM_path)
    srcband = src_ds.GetRasterBand(1)
    srcband.ComputeStatistics(False)
    min_elev, max_elev, mean_elev, stdev_elev = srcband.GetStatistics(True, True)

    return min_elev, max_elev, mean_elev, stdev_elev


def clip_raster(shapefile, rastToCut, outfile):
    layer_name = shapefile.split('/')[-1].split('.')[0]
    ds1 = gdal.Open(rastToCut)
    ds1_band = ds1.GetRasterBand(1)
    nodata = ds1_band.GetNoDataValue()
    print 'Clipping ' + rastToCut
    if nodata is None:
        nodata = -99
    ds1 = None

    ds = gdal.Warp(outfile, rastToCut,
                   warpOptions=['CUTLINE_ALL_TOUCHED=TRUE'],
                   format='GTiff',
                   cutlineDSName=shapefile,
                   cutlineLayer=layer_name,
                   cropToCutline=True,
                   multithread=True,
                   srcNodata=nodata,
                   dstNodata=nodata)

    ds = None
