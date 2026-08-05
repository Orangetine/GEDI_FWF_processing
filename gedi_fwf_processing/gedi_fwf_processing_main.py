
import os
import warnings
import geopandas as gpd

import gedi_fwf_processing.data_io as gio
import gedi_fwf_processing.data_prep as gprep
import gedi_fwf_processing.data_viz as gviz

from gedi_fwf_processing.data_prep import (
    L1B_GRANULES_DIR, L2A_GRANULES_DIR, 
    gediFilesL1B, gediFilesL2A, granule_h5_list_l1b, 
    granule_h5_list_l2a, EXTENT_DIR, GEDI_shots_path, 
    granules, beamNames, open_files
)

from bokeh.util.warnings import BokehUserWarning
warnings.simplefilter(action='ignore', category=BokehUserWarning)


############################################ Main

# The GEDI instrument consists of 3 lasers producing a total of 8 beam ground transects. 
# The eight remaining groups contain data for each of the eight GEDI beam transects. 
# For additional information, be sure to check out: https://gedi.umd.edu/instrument/specifications/.

# Get GEDI granules list downloaded
gio.get_GEDI_granules_downloaded(L1B_GRANULES_DIR, gediFilesL1B)
gio.get_GEDI_granules_downloaded(L2A_GRANULES_DIR, gediFilesL2A)

# Get GEDI DATA and METADATA Informations
gio.get_GEDI_data_file_informations(granule_h5_list_l1b, 'GEDI_files_informations_l1b.txt')
gio.get_GEDI_beams_informations(granule_h5_list_l1b, 'GEDI_beams_informations_l1b.txt')

gio.get_GEDI_data_file_informations(granule_h5_list_l2a, 'GEDI_files_informations_l2a.txt')
gio.get_GEDI_beams_informations(granule_h5_list_l2a, 'GEDI_beams_informations_l2a.txt')

gio.get_datasets_specification(granule_h5_list_l1b[0])
gio.get_datasets_specification(granule_h5_list_l2a[0])


# Region of interest
north_morroco_roi = gpd.GeoDataFrame.from_file(
    EXTENT_DIR + 'emprise_gedi.geojson',
)

if not os.path.isfile(GEDI_shots_path):
    GEDI_012_BA_GDF = gprep.get_all_GEDI_shots_within_roi(granules, north_morroco_roi, beamNames)
    # GEDI_012_BA_GDF = GEDI_012_BA_GDF[(GEDI_012_BA_GDF['Quality Flag'] == 1) & (GEDI_012_BA_GDF['Degrade'] == 0)]

    # EPSG:4326 is causing an offset in projection when plotting the layers with geoviews
    GEDI_012_BA_GDF = GEDI_012_BA_GDF.to_crs(3857)
    north_morroco_roi = north_morroco_roi.to_crs(3857)
    # Saving GeoDataFrame
    GEDI_012_BA_GDF.to_file(GEDI_shots_path, driver="GeoJSON")
else:
    GEDI_012_BA_GDF = gpd.read_file(GEDI_shots_path)
    north_morroco_roi = north_morroco_roi.to_crs(3857)

# Retriving columns from GeoDataframe to plot attributes
vdims = [col for col in GEDI_012_BA_GDF if col != 'geometry']

# Plotting an interactive HTML plot of waveforms shots 
gviz.plot_a_FWF(open_files, GEDI_012_BA_GDF, indices=range(1994,2000))
# Plotting five first full waveforms shots
gviz.plot_some_fwf(open_files, GEDI_012_BA_GDF)
# Plotting shots and Region of Interest
gviz.plot_shots_and_roi(north_morroco_roi, GEDI_012_BA_GDF)


# Get points/lines/cells grid geometry within ROI 
grid, gridinside = gprep.get_points_grid(north_morroco_roi)
grid_lines_gdf, grid_lines_clipped = gprep.get_lines_grid(north_morroco_roi)
grid_cells, grid_cellsinside = gprep.get_cells_grid(north_morroco_roi)
# Compute attribute n_points in GEoDataFrame to get density of point per cells
grid_cells, grid_cellsinside = gprep.get_number_of_shots_per_cells(GEDI_012_BA_GDF, grid_cells), gprep.get_number_of_shots_per_cells(GEDI_012_BA_GDF, grid_cellsinside)

# Plot grid and shots
gviz.plot_grid_and_GEDI_shots(north_morroco_roi, GEDI_012_BA_GDF, gridinside, grid_lines_clipped)

# Plot shots density per grid cells
gviz.plot_density_map(grid_cells, north_morroco_roi)

# Plot GEDI shot position from shot number
gviz.plot_GEDI_shot(GEDI_012_BA_GDF, shot_number=21520500300373664)

# Plot FWF from GEDI shot number
gviz.plot_FWF_from_shot_number(GEDI_012_BA_GDF, open_files, shot_number=21520500300373664)










































