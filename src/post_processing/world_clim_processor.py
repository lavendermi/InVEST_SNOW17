from osgeo import gdal


def process_wclim_data(ws_shape_path, wclim_raster_path):

    temp_raster_path = 'temp_raster.tif'
    clip_raster(ws_shape_path, wclim_raster_path, temp_raster_path)

    src_ds = gdal.Open(temp_raster_path)
    srcband = src_ds.GetRasterBand(1)
    srcband.ComputeStatistics(False)
    min_value, max_value, mean_value, stdev_value = srcband.GetStatistics(True, True)

    return min_value, max_value, mean_value, stdev_value


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
