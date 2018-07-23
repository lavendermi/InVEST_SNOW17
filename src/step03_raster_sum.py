import csv
import sys

import numpy.ma as np
from osgeo import gdal

# https://major.io/2007/07/05/bintar-argument-list-too-long/
# super useful link!!!

driver = gdal.GetDriverByName('GTiff')

# print the header
print 'year\tmonth\tws\tmodel\tqf.sum\tpx.count\tulx\txres\txskew\tuly\tyskew\tyres\tcubic.m\tfile'

myfile = open('/Users/mikelavender/Google Drive/Work/Projects/Cryosphere paper/Model Outputs/WaterSI_Model.csv', 'w')
wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
wr.writerow(['year', 'month', 'ws', 'model', 'qf.sum', 'px.count', 'ulx', 'xres', 'xskew', 'uly', 'yskew', 'yres',
             'cubic.m', 'file'])

import tarfile

fileName = ["/Users/mikelavender/Desktop/clusterDataStagging/final_tiffs_01.tar.gz",
            "/Users/mikelavender/Desktop/clusterDataStagging/final_tiffs_02.tar.gz",
            "/Users/mikelavender/Desktop/clusterDataStagging/final_tiffs_03.tar.gz"
            ]

for fName in fileName:

    tfile = tarfile.open(fName, 'r|gz')
    for cfile in tfile:
        if cfile.name[-4:] == ".tif" and "qf_" in cfile.name:
            print cfile.name.split("/")[-1:][0]
            file_ = tfile.extractfile(cfile)

        # for file_ in files:
        # if file_.endswith(".tif") & file_.startswith("qf_"):
            parts = cfile.name.split("/")[-1:][0].split("_")

            model = 'non-snow' if parts[3] == 'raw' else 'snow'
            year = parts[-1].rstrip('.tif')
            month = parts[1]
            ws = parts[2]

            # full_path = os.path.join(root, file_)

            gdal.FileFromMemBuffer("/vsimem/tiffinmem", file_.read())
            src_ds = gdal.Open("/vsimem/tiffinmem")
            # dst_ds = driver.CreateCopy(full_path, src_ds, 0, options=["TILED=YES", "COMPRESS=DEFLATE", "ZLEVEL=9", "PREDICTOR=3"])
            # the following line will use all cpus/threads available on a node. Use the above line for clustered computing
            # dst_ds = driver.CreateCopy(full_path, src_ds, 0, options=["TILED=YES", "COMPRESS=DEFLATE", "ZLEVEL=9", "PREDICTOR=3", "NUM_THREADS=ALL_CPUS"])
            # dst_ds = None

            if src_ds is None:
                print 'Unable to open INPUT.tif'
                gdal.Unlink('/vsimem/tiffinmem')
                sys.exit(1)

            ulx, xres, xskew, uly, yskew, yres = src_ds.GetGeoTransform()

            srcband = src_ds.GetRasterBand(1)
            srcband.ComputeStatistics(False)
            array = srcband.ReadAsArray()
            no_data_value = srcband.GetNoDataValue()
            stats = srcband.GetStatistics(True, True)
            # print "mean:\t", stats[2]

            mx = np.masked_equal(array, no_data_value)

            wr.writerow(
                [year,
                 month,
                 ws,
                 model,
                 str(mx.sum()),
                 str(mx.count()),
                 str(ulx),
                 str(xres),
                 str(xskew),
                 str(uly),
                 str(yskew),
                 str(abs(yres)),
                 str((abs(xres * yres) * (mx.sum() * 0.001))),
                 file_]
            )

            # print(
            #         year + '\t' +
            #         month + '\t' +
            #         ws + '\t' +
            #         model + '\t' +
            #         str(mx.sum()) + '\t' +
            #         str(mx.count()) + '\t' +
            #         str(ulx) + '\t' +
            #         str(xres) + '\t' +
            #         str(xskew) + '\t' +
            #         str(uly) + '\t' +
            #         str(yskew) + '\t' +
            #         str(abs(yres)) + '\t' +
            #         str((abs(xres * yres) * (mx.sum() * 0.001))) + '\t' +
            #         file_
            # )

            src_ds = None
            gdal.Unlink('/vsimem/tiffinmem')

myfile.close()
