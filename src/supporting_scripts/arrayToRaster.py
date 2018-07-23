"""
Converts a numpy array to a raster file and compresses it to save space
"""

from osgeo import osr, gdal
import numpy


def array_to_raster(array, dst_filename, src_filename, noDataValue):

    driver = gdal.GetDriverByName('GTiff')

    src_ds = gdal.Open(src_filename)
    dst_ds = driver.CreateCopy(dst_filename, src_ds, 0,
                               options=["TILED=YES", "COMPRESS=DEFLATE", "NUM_THREADS=ALL_CPUS", "BLOCKXSIZE=512", "BLOCKYSIZE=512"])

    dst_ds.SetDescription('No Description')
    dst_ds.SetMetadata('')
    dst_ds.GetRasterBand(1).SetMetadata('')
    dst_ds.GetRasterBand(1).SetNoDataValue(noDataValue)
    dst_ds.GetRasterBand(1).WriteArray(array)
    dst_ds.FlushCache()  # Write to disk.

    # Once we're done, close the dataset
    src_ds = None
    dst_ds = None

