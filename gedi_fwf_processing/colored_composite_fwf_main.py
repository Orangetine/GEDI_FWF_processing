import os

import numpy as np
from osgeo import gdal
from gedi_fwf_processing.fwf_stacking import STACKED_FWF_DIR

stacked_fwf_path = os.path.join(STACKED_FWF_DIR, 'stacked_fwf_roi_800m.tif')
cc_output_path = os.path.join(STACKED_FWF_DIR, 'color_composite_800m.tif')

stacked_fwf_ds = gdal.Open(stacked_fwf_path)
stacked_fwf = stacked_fwf_ds.ReadAsArray()
stacked_fwf = np.moveaxis(stacked_fwf, 0, -1)   

# Computing statistics on full waveforms
mean_fwf = np.mean(stacked_fwf, axis=-1)
median_fwf = np.median(stacked_fwf, axis=-1)
std_fwf = np.std(stacked_fwf, axis=-1)
max_fwf = np.max(stacked_fwf, axis=-1)

# Color composite is saved as to put the max of the FWF in red channel, 
# The mean of FWF in the blue channel and the standard deviation of FWF in the green channel

nrows, ncols = stacked_fwf.shape[:2]

# Saving Color Composite
driver = gdal.GetDriverByName('GTiff')
out_ds = driver.Create(cc_output_path, ncols, nrows, 3, gdal.GDT_Float32)
out_ds.SetProjection(stacked_fwf_ds.GetProjection())
out_ds.SetGeoTransform(stacked_fwf_ds.GetGeoTransform())

out_ds.GetRasterBand(1).WriteArray(max_fwf)   #R
out_ds.GetRasterBand(2).WriteArray(mean_fwf)  #G
out_ds.GetRasterBand(3).WriteArray(std_fwf)   #B

out_ds.FlushCache()
out_ds = None