
import geopandas as gpd

import gedi_fwf_processing.data_prep as gprep
from gedi_fwf_processing.data_prep import GEDI_shots_path, EXTENT_DIR
from gedi_fwf_processing.fwf_stacking import (compute_zrange, aggregate_fwf_per_cell, 
                                              get_fwf_cube, save_stacked_fwf_as_tiff, plot_fwf_per_cell)




GEDI_012_BA_GDF = gpd.read_file(GEDI_shots_path)
# Filter shots with quality flag to get rid of noised/depointed ones
# Unfortunately it lowers considerably the number of shots in GeoDataFrame, so the number of FWF aggregated
GEDI_012_BA_GDF = GEDI_012_BA_GDF[GEDI_012_BA_GDF['Quality Flag'] == 1]  

# Region of interest
north_morroco_roi = gpd.GeoDataFrame.from_file(
    EXTENT_DIR + 'emprise_gedi.geojson',
)
north_morroco_roi = north_morroco_roi.to_crs(3857)



# GEDI_filtered = GEDI_012_BA_GDF[GEDI_012_BA_GDF['Quality Flag'] == 1]
zrange_native = compute_zrange(GEDI_012_BA_GDF, pct=(1, 99))
zrange_1m = compute_zrange(GEDI_012_BA_GDF, step=1, pct=(1,99))

# print("Zrange native :", zrange_native, len(zrange_native), sep='\n')
# print("Zrange 1m :", zrange_1m, len(zrange_1m), sep='\n')

# Feel free to play with the pixel size by default GEDI data incitate the use of 1km spacing grid i.e.
# I.e. a pixel of 1000 meters of resolution, but the more the shots the more you can increase the resolution => 900m, 800m, etc ...
# If the grid cells are too small, some cells will be empty of shots, and will not aggregate waveform
 
spacing = 700  
gridcells, gridcellsinside  = gprep.get_cells_grid(north_morroco_roi, spacing=spacing)


plot_fwf_per_cell(GEDI_012_BA_GDF, gridcells, zrange_native)
mean_per_cell = aggregate_fwf_per_cell(GEDI_012_BA_GDF, gridcells, zrange_native)
cube = get_fwf_cube(north_morroco_roi, gridcells, mean_per_cell, spacing=spacing)
save_stacked_fwf_as_tiff(cube, north_morroco_roi, filename=f'stacked_fwf_roi_{str(spacing)}m.tif', spacing=spacing)
    