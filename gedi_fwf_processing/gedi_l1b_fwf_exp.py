from __future__ import annotations

import os
# import h5py
# import numpy as np
# import pandas as pd
import warnings
import geoviews as gv
import geopandas as gpd
import cartopy.crs as ccrs
from shapely.geometry import box
import matplotlib.pyplot as plt
from geoviews import tile_sources as gvts
from gedi_fwf_processing.utils import *

import holoviews as hv
gv.extension('bokeh', 'matplotlib')

from bokeh.util.warnings import BokehUserWarning
warnings.simplefilter(action='ignore', category=BokehUserWarning)

from IPython.display import display

############################################ Parameters settings

ROOT_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
DATA_DIR = os.path.join(ROOT_DIR, "data/")
GRANULES_DIR = os.path.join(DATA_DIR, 'granules/')
L1B_GRANULES_DIR = os.path.join(GRANULES_DIR, 'l1b/')
L2A_GRANULES_DIR = os.path.join(GRANULES_DIR, 'l2a/')
EXTENT_DIR = os.path.join(DATA_DIR, 'emprise/')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output/')

GEDI_shots_path = OUTPUT_DIR + 'GEDI0102_BA_GDF.geojson'

os.makedirs(OUTPUT_DIR, exist_ok=True)

############################################ Variables definition

# Getting GEDI Granule FIles from directory

gediFilesL1B = get_GEDI_files(L1B_GRANULES_DIR)
gediFilesL2A = get_GEDI_files(L2A_GRANULES_DIR)

# GEDI File names
gedifiles_names_l1b = [f.split('.')[0] for f in gediFilesL1B]
# Granule years
granule_years = [gedifiles_name.split('_')[2][:4] for gedifiles_name in gedifiles_names_l1b]

# Gedi Data are composed of 8 beams with 600meters range between each beam, the footpring is 25m
# GEDI HDF5 File contains groups in which data and metadata are stored
granule_h5_list_l1b = get_GEDI_granule_h5_list(L1B_GRANULES_DIR, gediFilesL1B)
granule_h5_list_l2a = get_GEDI_granule_h5_list(L2A_GRANULES_DIR, gediFilesL2A)

beamNames = [group for group in granule_h5_list_l1b[0].keys() if group.startswith('BEAM')]
full_power_beams = [beam for beam in beamNames if granule_h5_list_l1b[0][beam].attrs['description'] == "Full power beam"]
coverage_power_beams = [beam for beam in beamNames if granule_h5_list_l1b[0][beam].attrs['description'] == "Coverage beam"]

# Keys are granule's year & values are the granule data in h5 data format
granules = list(zip(granule_years, granule_h5_list_l1b, granule_h5_list_l2a))
open_files = {l1b.filename : l1b for l1b in granule_h5_list_l1b}

############################################ Main

# The GEDI instrument consists of 3 lasers producing a total of 8 beam ground transects. 
# The eight remaining groups contain data for each of the eight GEDI beam transects. 
# For additional information, be sure to check out: https://gedi.umd.edu/instrument/specifications/.

# Get GEDI DATA and METADATA Informations
# get_GEDI_data_file_informations(granule_h5_list_l1b, 'GEDI_files_informations_l1b.txt')
# get_GEDI_beams_informations(granule_h5_list_l1b, 'GEDI_beams_informations_l1b.txt')

# get_GEDI_data_file_informations(granule_h5_list_l2a, 'GEDI_files_informations_l2a.txt')
# get_GEDI_beams_informations(granule_h5_list_l2a, 'GEDI_beams_informations_l2a.txt')

get_datasets_specification(granule_h5_list_l1b[0])
get_datasets_specification(granule_h5_list_l2a[0])


# Region of interest
north_morroco_roi = gpd.GeoDataFrame.from_file(
    DATA_DIR + 'emprise/emprise_gedi.geojson',
)

if not os.path.isfile(GEDI_shots_path):
    GEDI_012_BA_GDF = get_all_GEDI_shots_within_roi(granules, north_morroco_roi, beamNames)
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
# plot_a_FWF(open_files, GEDI_012_BA_GDF, indices=range(1994,2000))
# # Plotting five first full waveforms shots
# plot_some_fwf(open_files, GEDI_012_BA_GDF)
# # Plotting shots and Region of Interest
# plot_shots_and_roi(north_morroco_roi, GEDI_012_BA_GDF)


# # Get points/lines/cells grid geometry within ROI 
# grid, gridinside = get_points_grid(north_morroco_roi)
# grid_lines_gdf, grid_lines_clipped = get_lines_grid(north_morroco_roi)
# grid_cells, grid_cellsinside = get_cells_grid(north_morroco_roi)
# # Compute attribute n_points in GEoDataFrame to get density of point per cells
# grid_cells, grid_cellsinside = get_number_of_shots_per_cells(GEDI_012_BA_GDF, grid_cells), get_number_of_shots_per_cells(GEDI_012_BA_GDF, grid_cellsinside)

# # Plot grid and shots
# plot_grid_and_GEDI_shots(north_morroco_roi, GEDI_012_BA_GDF, gridinside, grid_lines_clipped)

# # Plot shots density per grid cells
# plot_density_map(grid_cells, north_morroco_roi)


# GEDI Data Structure 
# rxwaveform est le tableau qui contient les waveforms
# Ce n'est pas un tableau bien rangé (n_shots, n_samples)
# Mais un tableau 1D qui contient bout à bout tous les échantillons 
# de tous les shots du beam à la suite. 
# 
# rxwaveform = [ shot1_ech1, shot1_ech2, ..., shot1_echN1,
#                shot2_ech1, shot2_ech2, ..., shot2_echN2,
#                shot3_ech1, ..., shot3_echN3, ... ]

# Chaque shots sur le terrain n'a pas le même nombre d'échantillons. 
# Un shot sur terrain plat de peu de végétation a une fenêtre d'enregistrement courte, 
# un shot sur relief accidenté avec canopée dense a une fenêtre bien plus longue.

# # Plot GEDI shot position from shot number
plot_GEDI_shot(GEDI_012_BA_GDF, shot_number=21520500300373664)

# Plot FWF from GEDI shot number
plot_FWF_from_shot_number(GEDI_012_BA_GDF, open_files, shot_number=21520500300373664)

# print(GEDI_012_BA_GDF.columns)

# # Every datasets from each beam and granule
# all_sds_flat = get_gedi_datasets_flat(granule_h5_list_l1b)
# all_sds_grouped = get_gedi_datasets_grouped(granule_h5_list_l1b)
# # Sample Count datasets from each beam and granule
# sds_sample_count_flat = filter_sds_flat(all_sds_flat, suffix='/rx_sample_count')
# sds_sample_count_grouped = filter_sds_grouped(all_sds_grouped, suffix='/rx_sample_count')
# # Start index datasets from each beam and granule
# sds_sample_start_index_flat = filter_sds_flat(all_sds_flat, suffix='/rx_sample_start_index')
# sds_sample_start_index_grouped = filter_sds_grouped(all_sds_grouped, suffix='/rx_sample_start_index')
# # Start waveform datasets from each beam and granule
# sds_waveform_flat = filter_sds_flat(all_sds_flat, '/rxwaveform')
# sds_waveform_grouped = filter_sds_grouped(all_sds_grouped, '/rxwaveform')
# # Start shot number datasets from each beam and granule
# sds_shot_number_flat = filter_sds_flat(all_sds_flat, '/shot_number')
# sds_shot_number_grouped = filter_sds_grouped(all_sds_grouped, '/shot_number')

# granule, path_sc = sds_sample_count_flat[0]
# print(f"{granule} -> {path_sc} is {granule[path_sc].attrs['description']}")

# granule, path_ssi = sds_sample_start_index_flat[0]
# print(f"{granule} -> {path_ssi} is {granule[path_ssi].attrs['description']}")

# granule, path_wf = sds_waveform_flat[0]
# print(f"{granule} -> {path_wf} is {granule[path_wf].attrs['description']}")

# granule, path_sn = sds_shot_number_flat[0]
# print(f"{granule} -> {path_sn} is {granule[path_sn].attrs['description']}")



# shot = 316060100200223812


# for granule, path_sn in sds_shot_number_flat :
#     shots = granule[path_sn][()]
#     local_idx = np.where(shots == shot)[0]
#     if local_idx.size:
#         local_idx = local_idx[0]
#         beam = path_sn.split('/')[0]
#         break

# wf_count = granule[f"{beam}/rx_sample_count"][local_idx]
# wf_start = granule[f"{beam}/rx_sample_start_index"][local_idx] - 1
# wf_shot_number = granule[f"{beam}/shot_number"][local_idx]

# # latitude_bin0 : Latitude of the start of the RX window.
# wf_latitude = granule[f"{beam}/geolocation/latitude_bin0"][local_idx]
# # longitude_bin0 : Longitude of the start of the RX window.
# wf_longitude = granule[f"{beam}/geolocation/longitude_bin0"][local_idx]

# # Grab the elevation recorded at the start and end of the full waveform capture
# # elevation_bin0 : Height of the start of the RX window, relative to the WGS-84 ellipsoid.
# z_start = granule[f"{beam}/geolocation/elevation_bin0"][local_idx]
# # elevation_lastbin : Height of the end of the RX window, relative to the WGS-84 ellipsoid.
# z_end = granule[f"{beam}/geolocation/elevation_lastbin"][local_idx]
# # Extraction des valeurs d'intensité de la waveform 
# waveform = granule[f"{beam}/rxwaveform"][wf_start:wf_start + wf_count]


# # Find elevation difference from start to finish and divide into equal intervals based on sample_count
# z_stretch = np.add(z_end, np.multiply(range(wf_count, 0, -1), ((z_start - z_end) / int(wf_count))))


# waveform_df = pd.DataFrame({
#     "Elevation (m)": z_stretch, "Amplitude (DN)" : waveform
# })

# display(hv.Curve(waveform_df))

# print(waveform_df)

# print()
# print(f"The waveform located at: {str(wf_latitude)}, {str(wf_longitude)} (shot ID: {wf_shot_number}, index {local_idx}) is from beam {beam} \
#       and is stored in rxwaveform beginning at index {wf_start} and ending at index {wf_start + wf_count}")

# # index = np.where(all_shots_array == shot)
# # print(index)








































