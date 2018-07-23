import csv
import math
import os
import signal
import sys
import getopt

import natcap.invest.seasonal_water_yield.seasonal_water_yield
import numpy.ma as ma
import pandas as pd
from osgeo import gdal, ogr

gdal.UseExceptions()
gdal.SetCacheMax(1024)

# these are the args required(??) by invest. They point to the files and set some of the parameters. This file can
# be generated from the settings window of the invest model itself. We used this as a template and modified the
# values in the code below for each run (watershed and snow, no-snow model run.
# Note: most of the path values don't matter here. We change them in the code. Only the numeric values matter.
args = {
    'alpha_m': '1/12',
    'aoi_path': '/watershed_shape/watershed_shape.shp',
    'beta_i': '1.0',
    'biophysical_table_path': '/biophysical/biophysical.csv',
    'dem_raster_path': '/dem/dem.tif',
    'et0_dir': '/ET',
    'gamma': '1.0',
    'lulc_raster_path': '/lulc/lulc.tif',
    'monthly_alpha': False,
    'precip_dir': '',
    'rain_events_table_path': '/rain_events/rain_events.csv',
    'soil_group_path': '/soils/soils.tif',
    'threshold_flow_accumulation': '1000',
    'user_defined_climate_zones': False,
    'user_defined_local_recharge': False,
    'results_suffix': '',
    'workspace_dir': '',
}

# share_path is the path to all of the data files required by the invest model.
# the layout is essentially the same as for Invest
share_path = '/InVEST_Data/'


# creat the rain events table for the current watershed and year
def build_rain_events_table(year, shapefile):
    myfile = open(share_path + 'rain_events/rain_events.csv', 'w')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow(['month', 'events'])

    for events_month in range(1, 13, 1):
        # clip it
        layer_name = shapefile.split('/')[-1].split('.')[0]
        file_path = share_path + 'rain_events/' + str(year) + '/rain_events_' + str(
            year) + '_' + str(events_month) + '.tif'
        if os.path.exists(file_path):

            ds = gdal.Warp('', file_path,
                           warpOptions=['CUTLINE_ALL_TOUCHED=TRUE'],
                           format='MEM',
                           cutlineDSName=shapefile,
                           cutlineLayer=layer_name)

            ds_band = ds.GetRasterBand(1)
            ds_band.ComputeStatistics(False)

            stats = ds_band.GetStatistics(True, True)
            if stats is None:
                sys.exit('No stats available for layer: ' + layer_name)

            wr.writerow([str(events_month), str(int(stats[2]))])

        else:
            print('File does not exist:\t' +  file_path)

        ds = None

    myfile.close()


# calculate the number of days below zero
def get_days_below_zero(year, shapefile, ws_flag, ws):
    if ws_flag:
        myfile = open(share_path + 'day_below_zero.csv', 'w+')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(['watershed', 'year', 'month', 'days.below.zero'])
    else:
        myfile = open(share_path + 'day_below_zero.csv', 'a+')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)

    month_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    for _month in month_list:
        # clip it
        layer_name = shapefile.split('/')[-1].split('.')[0]

        file_path = share_path + 'below_freezing/' + str(year) + '/days_below_freezing_' \
                    + str(year) + '_' + str(_month) + '.tif'
        if os.path.exists(file_path):

            ds = gdal.Warp('', file_path,
                           warpOptions=['CUTLINE_ALL_TOUCHED=TRUE'],
                           format='MEM',
                           cutlineDSName=shapefile,
                           cutlineLayer=layer_name,
                           cropToCutline=True,
                           cutlineBlend=2,
                           multithread=False)

            ds_band = ds.GetRasterBand(1)
            ds_band.ComputeStatistics(False)

            stats = ds_band.GetStatistics(True, True)
            if stats is None:
                sys.exit('No stats available for layer: ' + ws)

            wr.writerow([str(ws), str(year), str(_month), str(int(stats[2]))])

        else:
            print 'File does not exist:\t', file_path

        ds = None

    myfile.close()


# clip the raster (global) and re-project it to a valid/correct SRS
def clip_and_reproject(lat, lng, shapefile, rastToCut, outfile):
    layer_name = shapefile.split('/')[-1].split('.')[0]
    epsg = get_epsg_number(float(lat), float(lng))
    ds1 = gdal.Open(rastToCut)
    ds1_band = ds1.GetRasterBand(1)
    noData = ds1_band.GetNoDataValue()
    print 'Clipping ' + rastToCut
    if noData is None:
        if 'lulc.tif' in rastToCut:
            noData = 255
        else:
            noData = -99

    ds = gdal.Warp(outfile, rastToCut,
                   warpOptions=['CUTLINE_ALL_TOUCHED=TRUE'],
                   creationOptions=["TILED=YES"],
                   dstSRS=epsg,
                   format='GTiff',
                   cutlineDSName=shapefile,
                   xRes=90,
                   yRes=90,
                   cutlineLayer=layer_name,
                   cropToCutline=True,
                   cutlineBlend=2,
                   multithread=False,
                   srcNodata=noData,
                   dstNodata=noData)

    ds = None


# clip and reproject the MODIS raster to match the current WS
def clip_and_reproject_MODIS(lat, lng, shapefile, rastToCut, outfile):
    layer_name = shapefile.split('/')[-1].split('.')[0]
    epsg = get_epsg_number(float(lat), float(lng))
    ds1 = gdal.Open(rastToCut, gdal.GA_Update)
    ds1_band = ds1.GetRasterBand(1)
    noData = ds1_band.GetNoDataValue()
    print 'Clipping ' + rastToCut

    if noData is None:
        noData = -32767
        ds1.GetRasterBand(1).SetNoDataValue(noData)

    data = ds1.ReadAsArray()
    masked_data = ma.masked_where((data >= 32761) | (data < 0), data).filled(noData)
    ds1.GetRasterBand(1).WriteArray(masked_data)

    ds1 = None
    ds = gdal.Warp(outfile, rastToCut,
                   warpOptions=['CUTLINE_ALL_TOUCHED=TRUE'],
                   creationOptions=["TILED=YES", "COMPRESS=DEFLATE"],
                   dstSRS=epsg,
                   format='GTiff',
                   cutlineDSName=shapefile,
                   cutlineLayer=layer_name,
                   cropToCutline=True,
                   cutlineBlend=2,
                   multithread=False,
                   srcNodata=noData,
                   dstNodata=noData)

    ds = None


# Get the correct epsg number to re-project to local UTM
def get_epsg_number(lat, lng):
    zone_number = int(math.floor((lng + 180) / 6) + 1)

    if 56.0 <= lat < 64.0 and 3.0 <= lng < 12.0:
        zone_number = 32

    # Special zones for Svalbard
    if 72.0 <= lat < 84.0:
        if 0.0 <= lng < 9.0:
            zone_number = 31;
        elif 9.0 <= lng < 21.0:
            zone_number = 33;
        elif 21.0 <= lng < 33.0:
            zone_number = 35
        elif 33.0 <= lng < 42.0:
            zone_number = 37

    if lat > 0:
        return "EPSG:" + str(32600 + zone_number)
    else:
        return "EPSG:" + str(32700 + zone_number)


# This clips all of the rasters to match the current WS shapefile
def clip_base_rasters(lat, lng):
    global cutline_and_ws_shapefile, dest
    # make sure the shapefile exists - if not log it and skip
    if os.path.exists(cutline_and_ws_shapefile):

        # reproject shapefile
        driver = ogr.GetDriverByName('ESRI Shapefile')
        if os.path.exists(ws_base_path + '~working_shp.shp'):
            driver.DeleteDataSource(ws_base_path + '~working_shp.shp')

        srcDS = gdal.OpenEx(cutline_and_ws_shapefile)
        ds = gdal.VectorTranslate(ws_base_path + '~working_shp.shp',
                                  srcDS=srcDS,
                                  format='ESRI Shapefile',
                                  reproject=True,
                                  dstSRS=get_epsg_number(lat, lng))

        # Dereference and close dataset, then reopen.
        del ds

        cutline_and_ws_shapefile = ws_base_path + '~working_shp.shp'
        args['aoi_path'] = cutline_and_ws_shapefile

        # dem
        # get the correct DEM and clip it
        if getattr(row, "wmo_reg") == 4:
            dem = root_path + 'dem/DEM_na.tif'
        elif getattr(row, "wmo_reg") == 3:
            dem = root_path + 'dem/DEM_sa.tif'

        dest = root_path + 'dem/dem_clipped.tif'
        clip_and_reproject(lat, lng,
                           shapefile=cutline_and_ws_shapefile,
                           rastToCut=dem,
                           outfile=dest)
        args['dem_raster_path'] = dest

        # lulc
        dest = root_path + 'lulc/lulc_clipped.tif'
        clip_and_reproject(lat, lng,
                           shapefile=cutline_and_ws_shapefile,
                           rastToCut=root_path + 'lulc/lulc.tif',
                           outfile=dest)
        args['lulc_raster_path'] = dest

        # soils
        dest = root_path + 'soils/soils_clipped.tif'
        clip_and_reproject(lat, lng,
                           shapefile=cutline_and_ws_shapefile,
                           rastToCut=root_path + 'soils/soils.tif',
                           outfile=dest)
        args['soil_group_path'] = dest
    else:
        raise ValueError('###### Missing shape file')


def clip_et_layer(lat, lng):
    global month, dest, src
    # et
    for month in range(1, 13, 1):
        dest = root_path + 'et/working_dir/et_{0}.tif'.format(str(month))
        src = root_path + 'et/{1}/MOD16A2_ET_0.05deg_GEO_{1}M{0:02d}.tif'.format(
            month, year)
        clip_and_reproject_MODIS(lat, lng,
                                 shapefile=cutline_and_ws_shapefile,
                                 rastToCut=src,
                                 outfile=dest)


def clip_precip_layer(lat, lng):
    global month, dest, src
    # precip
    for month in range(1, 13, 1):
        dest = root_path + 'precip/working_dir/precip_{0}.tif'.format(str(month))
        src = root_path + 'precip/{2}/{1}/{2}_h2o_{1}_{0}.tif'.format(month, year, model)
        clip_and_reproject(lat, lng,
                           shapefile=cutline_and_ws_shapefile,
                           rastToCut=src,
                           outfile=dest)


# this is a HUGE HACK to deal with the fact the InVEST hangs sometimes.
# we just kill the process if things take too long. The main reason for InVEST
# hanging seems to be that it can't figure out the flow for a DEM or the WS shapefile
# has bad data in it.
def timeout_handler(num, stack):
    print("Received SIGALRM")
    raise Exception("InVEST too slow... infinite loop")



# this is the main runner. It loops through each combination of
# WS, YEAR, & MODEL, clipping the rasters as needed, updating file locations
# in the args list and running the InVEST model for each one.
if __name__ == '__main__':
    argv = sys.argv[1:]

    df_start = -1
    df_stop = -1
    try:
        opts, args2 = getopt.getopt(argv, "b:e:", ["begin=", "end="])
    except getopt.GetoptError:
        print 'test.py -b <beginRow> -e <endRow>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -b <beginRow> -e <endRow>'
            sys.exit()
        elif opt in ("-b", "--beginRow"):
            df_start = int(arg)
        elif opt in ("-e", "--endRow"):
            df_stop = int(arg)
    print 'First row to process is:"', df_start
    print 'Lat row to process is:"', df_stop

    ws_flag = True
    df = pd.read_csv(share_path + 'GRDC_Stations.csv').sort_values('area').query('area >= 10')
    df_len = len(df)

    rand_sample = pd.DataFrame()

    if df_stop >= df_len:
        rand_sample = df[df_start:]
    else:
        rand_sample = df[df_start:df_stop]

    print rand_sample

    ws_base_path = share_path + 'watershed_shp/'
    root_path = share_path + ''
    year_list = range(2000, 2014 + 1, 1)

    # year_list = [2007]
    precip_model = ['snow17', 'raw']

    # loop through each of the randomly selected watersheds
    # doing raw runoff and snow17 modelled runoff for each year
    for row in rand_sample.itertuples(index=True, name='Pandas'):

        grdc_no = getattr(row, 'grdc_no')
        # grdc_no = getattr(row, 'Watershed')
        lat_ = getattr(row, 'lat')
        lng_ = getattr(row, 'long')

        # get the shapefile for the watershed
        # cutline_and_ws_shapefile = ws_base_path + 'grdc_basins_smoothed_md_no_' + str(
        #     getattr(row, "Watershed")) + '.shp'
        cutline_and_ws_shapefile = ws_base_path + 'grdc_basins_smoothed_md_no_' + str(
            getattr(row, "grdc_no")) + '.shp'

        print cutline_and_ws_shapefile

        try:
            try:
                clip_base_rasters(lat_, lng_)

                for year in year_list:

                    for model in precip_model:

                        try:
                            # et
                            clip_et_layer(lat_, lng_)

                            # precip
                            clip_precip_layer(lat_, lng_)

                            # build the rain_events.csv file for this run
                            build_rain_events_table(year, cutline_and_ws_shapefile)

                            # days below zero
                            if model == 'snow17':
                                get_days_below_zero(year, cutline_and_ws_shapefile, ws_flag, grdc_no)

                            ws_flag = False

                            # update natcap settings to reflect correct paths
                            args['precip_dir'] = root_path + 'precip/working_dir/'
                            args['et0_dir'] = root_path + 'et/working_dir/'
                            args['rain_events_table_path'] = root_path + 'rain_events/rain_events.csv'
                            args['biophysical_table_path'] = root_path + 'biophysical/biophysical.csv'
                            # set to 125 pixels (dem is about 90m pixel size)
                            args['threshold_flow_accumulation'] = 125
                            args['results_suffix'] = '_{0}_{1}_{2}'.format(str(grdc_no), model, str(year))
                            args['workspace_dir'] = root_path + 'workspace'

                            print(args)

                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(5 * 60)  # give it ten minutes then time it out

                            try:
                                natcap.invest.seasonal_water_yield.seasonal_water_yield.execute(args)
                            except Exception as ex:
                                if "InVEST too slow... infinite loop" in ex:
                                    print(ex)
                                    pass
                                else:
                                    print(ex)
                            finally:
                                print "do nothing"
                                signal.alarm(0)

                        except RuntimeError as re:
                            print("#### Houston, we have a problem!!")
                            print re
                            pass

                    # do some cleanup
                    print "Cleaning things up a bit..."

                    folder = root_path + 'workspace'
                    for the_file in os.listdir(folder):
                        file_path = os.path.join(folder, the_file)
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            print(e)

                    folder = root_path + 'workspace/intermediate_outputs'
                    for the_file in os.listdir(folder):
                        if not the_file.startswith('qf'):
                            file_path = os.path.join(folder, the_file)
                            try:
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                            except Exception as e:
                                print(e)

                    dst = root_path + 'final_tiffs'
                    for fname in os.listdir(folder):
                        if os.path.isfile(os.path.join(folder, fname)) and fname.startswith('qf'):
                            os.rename(os.path.join(folder, fname), os.path.join(dst, fname))

            except ValueError as ve:
                # sys.exit(ve)
                pass

        except RuntimeError as re:
            # sys.exit(re)
            pass
