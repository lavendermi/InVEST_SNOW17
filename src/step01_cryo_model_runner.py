#!/usr/local/bin/python
"""
Snow-17 accumulation and ablation model runner

This script file iterates over all of the netCDF files of precipiation, minimum temperature and maximum temperature
and runs the snow model for each individual pixel. Because the snow model builds on the data of the previous
timestep (day) you need to run all of the years together. This can use a LOT of memory if your rasters are large
and your timeseries is long.

The netCDF files contain daily data in layers so each file is really 366 layers.

The output of this are monthly rasters for total monthly raw precip., total monthly snow-17 runoff, the number of
rain events per month, and the number of days below zero for each month.
"""

import datetime
import os
import sys

import numpy as np
import numpy.ma as ma
import pandas as pd
from osgeo import gdal

from supporting_scripts.arrayToRaster import array_to_raster
from supporting_scripts.snow17 import snow17

# Set GeoTiff driver
driver = gdal.GetDriverByName("netCDF")
driver.Register()

basePath = "/"
subPath = "clipped/"
template_file = '/templates/template.tif'
years = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014]

cols = 0
rows = 0


# Print iterations progress
def printProgress(iteration, total, prefix='', suffix='', decimals=1, barLength=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        barLength   - Optional  : character length of bar (Int)
    """
    formatStr = "{0:." + str(decimals) + "f}"
    percent = formatStr.format(100 * (iteration / float(total)))
    filledLength = int(round(barLength * iteration / float(total)))
    bar = '.' * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percent, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


def concatenate_arrays_and_sum_pixels(array_like):
    return np.sum(ma.concatenate(array_like, axis=0), axis=0)


def pixel2coord(col, row, affine):
    """Returns global coordinates to pixel center using base-0 raster index"""
    ux, p_width, b, uy, p_height, e = affine

    xp = p_width * col + b * row + p_width * 0.5 + b * 0.5 + ux
    yp = p_height * col + e * row + p_height * 0.5 + e * 0.5 + uy
    return (xp, yp)


first_time_flag = True

for year in years:

    fileName_minTemp = "tmin." + str(year) + ".nc"
    fileName_maxTemp = "tmax." + str(year) + ".nc"
    fileName_Precip = "precip." + str(year) + ".nc"

    print "Filenames: " + fileName_minTemp + "\t" + fileName_maxTemp + "\t" + fileName_Precip

    # Open raster and read number of rows, columns, bands
    dataset_minTemp = gdal.Open(basePath + subPath + fileName_minTemp)
    dataset_maxTemp = gdal.Open(basePath + subPath + fileName_maxTemp)
    dataset_precip = gdal.Open(basePath + subPath + fileName_Precip)

    minTemp_cols = dataset_minTemp.RasterXSize
    maxTemp_cols = dataset_maxTemp.RasterXSize
    precip_cols = dataset_precip.RasterXSize

    minTemp_rows = dataset_minTemp.RasterYSize
    maxTemp_rows = dataset_maxTemp.RasterYSize
    precip_rows = dataset_precip.RasterYSize

    minTemp_Bands = dataset_minTemp.RasterCount
    maxTemp_Bands = dataset_maxTemp.RasterCount
    precip_Bands = dataset_precip.RasterCount

    assert minTemp_cols == maxTemp_cols == precip_cols
    assert minTemp_rows == maxTemp_rows == precip_rows
    assert minTemp_Bands == maxTemp_Bands == precip_Bands

    # unravel GDAL affine transform parameters
    affine = dataset_minTemp.GetGeoTransform()

    cols = minTemp_cols
    rows = minTemp_rows

    print "Raster Band Counts:\t", minTemp_Bands
    noData = dataset_minTemp.GetRasterBand(1).GetNoDataValue()

    print dataset_minTemp.GetRasterBand(1).GetNoDataValue()
    print dataset_maxTemp.GetRasterBand(1).GetNoDataValue()
    print dataset_precip.GetRasterBand(1).GetNoDataValue()

    if not dataset_minTemp.GetRasterBand(1).GetNoDataValue() == dataset_maxTemp.GetRasterBand(
            1).GetNoDataValue() == dataset_precip.GetRasterBand(1).GetNoDataValue():
        sys.exit("NoData values do not match!")

    # calculate the mean between the two arrays
    print "Reading temperature rasters"
    minTemp = dataset_minTemp.ReadAsArray()
    masked_minTemp = ma.masked_values(minTemp, noData)
    maxTemp = dataset_maxTemp.ReadAsArray()
    masked_maxTemp = ma.masked_values(maxTemp, noData)

    print "Reading precipitation raster "
    dPrecip = dataset_precip.ReadAsArray()
    masked_dPrecip = ma.masked_where(dPrecip < 0, dPrecip)

    print "Calculating daily mean temperatures..."
    meanTemp = ma.masked_where(ma.getmask(masked_minTemp), (masked_minTemp + masked_maxTemp) / 2.0)

    print "Stacking arrays"
    if first_time_flag:
        meanTempLayers = meanTemp
        dailyPrecipLayers = masked_dPrecip
        first_time_flag = False
    else:
        tempTemp = meanTempLayers
        meanTempLayers = ma.concatenate((tempTemp, meanTemp), axis=0)

        tempPrecip = dailyPrecipLayers
        dailyPrecipLayers = ma.concatenate((tempPrecip, masked_dPrecip), axis=0)

    print "Stacked Temperature Numpy Array shape: ", meanTempLayers.shape
    print "Stacked Precipitation Numpy Array shape: ", dailyPrecipLayers.shape

    # Done - close things up
    dataset_Temp = None
    dataset_precip = None

l = cols * rows
i = 0

start = datetime.date(years[0], 1, 1)
end = datetime.date(years[-1], 12, 31)
rng = pd.date_range(start, end, freq='D')

runoff_raster = ma.masked_all_like(dailyPrecipLayers)
swe_raster = ma.masked_all_like(dailyPrecipLayers)

printProgress(i, l, prefix='Progress:', suffix='Complete', barLength=50)

for row in range(rows):
    for col in range(cols):
        temp = meanTempLayers[:, row, col]
        precip = dailyPrecipLayers[:, row, col]
        if temp.any() == noData or precip.any() == noData or temp.any() == np.nan or precip.any() == np.nan:
            result = np.nan, np.nan
        else:
            lng, lat = pixel2coord(col, row, affine)
            result = snow17(rng.to_pydatetime(), precip, temp, lat, elevation=0, dt=24, scf=1.0, rvs=1,
                            uadj=0.04, mbase=1.0, mfmax=1.05, mfmin=0.6, tipm=0.1, nmf=0.15,
                            plwhc=0.04, pxtemp=1.0, pxtemp1=-1.0, pxtemp2=3.0)
            swe_raster[:, row, col] = ma.masked_where(result[0] < 0, result[0])
            runoff_raster[:, row, col] = ma.masked_where(result[1] < 0, result[1])

        i += 1
        printProgress(i, l, prefix='Progress:', suffix='Complete', barLength=50)

# Done!!
# Now save the layers as new precipitation and SWE layers

numberLayers = runoff_raster.shape[0]
print "Layer count: " + str(numberLayers)

raw_rain_events = ma.masked_where(dailyPrecipLayers < 0, dailyPrecipLayers) > 0.1
below_zero_days = ma.masked_where(ma.getmask(meanTempLayers), meanTempLayers < 0)

# split the SNOW model output (a monolithic numpy array) into individual numpy arrays - one per day
# and calculate the monthly totals for each
total_monthly_runoff = pd.Series(np.split(runoff_raster, numberLayers), index=rng) \
    .resample('M') \
    .apply(concatenate_arrays_and_sum_pixels)
total_monthly_precip = pd.Series(np.split(dailyPrecipLayers, numberLayers), index=rng) \
    .resample('M') \
    .apply(concatenate_arrays_and_sum_pixels)
monthly_rain_events = pd.Series(np.split(raw_rain_events, numberLayers), index=rng) \
    .resample('M') \
    .apply(concatenate_arrays_and_sum_pixels)
days_below_zero = pd.Series(np.split(below_zero_days, numberLayers), index=rng) \
    .resample('M') \
    .apply(concatenate_arrays_and_sum_pixels)


def create_GeoTiff_files(series_to_write, path_str, template_file_and_path):
    for (key, v) in series_to_write.iteritems():
        data = ma.filled(v, -99)
        _filename = path_str.format(str(key.year), str(key.month))
        print "Writing file:\t", _filename
        array_to_raster(data, _filename, template_file_and_path, -99)


create_GeoTiff_files(total_monthly_runoff,
                     "/Users/mikelavender/Documents/SAFER_Cryo/precip/snow17/{0}/snow17_h2o_{0}_{1}.tif",
                     template_file)

create_GeoTiff_files(total_monthly_precip,
                     "/Users/mikelavender/Documents/SAFER_Cryo/precip/raw/{0}/raw_h2o_{0}_{1}.tif",
                     template_file)

create_GeoTiff_files(monthly_rain_events,
                     "/Users/mikelavender/Documents/SAFER_Cryo/rain_events/{0}/rain_events_{0}_{1}.tif",
                     template_file)

create_GeoTiff_files(days_below_zero,
                     "/Users/mikelavender/Documents/SAFER_Cryo/below_freezing/{0}/days_below_freezing_{0}_{1}.tif",
                     template_file)

print("ALL DONE!!!!!")

os.system('afplay /System/Library/Sounds/Glass.aiff')
