"""
This re-codes the soils raster to values that work with the
InVEST model
"""
import numpy
from numpy import zeros
from numpy import logical_and
from osgeo import gdal

# http://geoexamples.blogspot.ca/2013/06/gdal-performance-raster-classification.html

classification_values = [1, 6, 7, 10, 13]  # The interval values to classify
classification_output_values = [4, 3, 2, 1, 255]  # The value assigned to each interval

in_file = "/Users/mikelavender/Documents/SAFER_Cryo/soils/TEXMHT_M_sl4_250m.tif"
out_file = "/Users/mikelavender/Documents/SAFER_Cryo/soils/soils.tif"

ds = gdal.Open(in_file)
band = ds.GetRasterBand(1)

block_sizes = band.GetBlockSize()
x_block_size = block_sizes[0]
y_block_size = block_sizes[1]

xsize = band.XSize
ysize = band.YSize

max_value = band.GetMaximum()
min_value = band.GetMinimum()

if max_value == None or min_value == None:
    stats = band.GetStatistics(0, 1)
    max_value = stats[1]
    min_value = stats[0]

format = "GTiff"
driver = gdal.GetDriverByName(format)
dst_ds = driver.Create(out_file, xsize, ysize, 1, gdal.GDT_Byte, options=["TILED=YES", "COMPRESS=DEFLATE"])
dst_ds.SetGeoTransform(ds.GetGeoTransform())
dst_ds.SetProjection(ds.GetProjection())

for i in range(0, ysize, y_block_size):
    print i, " of ", ysize
    if i + y_block_size < ysize:
        rows = y_block_size
    else:
        rows = ysize - i
    for j in range(0, xsize, x_block_size):
        if j + x_block_size < xsize:
            cols = x_block_size
        else:
            cols = xsize - j

        data = band.ReadAsArray(j, i, cols, rows)
        r = zeros((rows, cols), numpy.int8)

        for k in range(len(classification_values) - 1):
            if classification_values[k] <= max_value and (classification_values[k + 1] > min_value):
                r = r + classification_output_values[k] * logical_and(data >= classification_values[k],
                                                                      data < classification_values[k + 1])
        if classification_values[k + 1] < max_value:
            r = r + classification_output_values[k + 1] * (data >= classification_values[k + 1])

        dst_ds.GetRasterBand(1).SetNoDataValue(0)
        dst_ds.GetRasterBand(1).WriteArray(r, j, i)

dst_ds = None