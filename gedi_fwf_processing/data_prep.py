from __future__ import annotations

import os
import h5py
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import box
from shapely.geometry import LineString

from gedi_fwf_processing.data_io import get_granule_datasets, get_GEDI_files, get_GEDI_granule_h5_list

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
gedifiles_names_l2a = [f.split('.')[0] for f in gediFilesL2A]

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

############################################ Functions

def get_df_from_beam(l1b: h5py.File, l2a: h5py.File, beamName: str, stride: int) -> pd.DataFrame:
    """Get GeoDataframe combining datasets from L1B & L2A GEDI granule"""
    # L1B datasets
    shots_l1b = l1b[f'{beamName}/shot_number'][()][::stride]
    lats = l1b[f'{beamName}/geolocation/latitude_bin0'][()][::stride]
    lons = l1b[f'{beamName}/geolocation/longitude_bin0'][()][::stride]
    elev_bin0 = l1b[f'{beamName}/geolocation/elevation_bin0'][()][::stride]
    elev_lastbin = l1b[f'{beamName}/geolocation/elevation_lastbin'][()][::stride]
    rx_start_index = l1b[f'{beamName}/rx_sample_start_index'][()][::stride]
    rx_sample_count = l1b[f'{beamName}/rx_sample_count'][()][::stride]
    srf = l1b[f'{beamName}/stale_return_flag'][()][::stride]
    degrade = l1b[f'{beamName}/geolocation/degrade'][()][::stride]
    granule_path = l1b.filename

    # L2A datasets
    shots_l2a =  l2a[f'{beamName}/shot_number'][()][::stride]
    elev_lowestmode = l2a[f'{beamName}/elev_lowestmode'][()][::stride]
    elev_highestreturn = l2a[f'{beamName}/elev_highestreturn'][()][::stride] 
    quality_flag = l2a[f'{beamName}/quality_flag'][()][::stride] 
    sensitivity = l2a[f'{beamName}/sensitivity'][()][::stride] 
    surface_flag = l2a[f'{beamName}/surface_flag'][()][::stride] 
    rh = l2a[f'{beamName}/rh'][()][::stride] 

    df_l1b = pd.DataFrame({
        'Beam' : beamName,
        'Shot Number' : shots_l1b,
        'Longitude' : lons,
        'Latitude' : lats,
        'Elevation bin0' : elev_bin0,
        'Elevation lastbin' : elev_lastbin,
        'Sample Start Index' : rx_start_index,
        'Sample Count' : rx_sample_count,
        'Stale Return Flag' : srf,
        'Degrade' : degrade,
        'Granule Path' : granule_path,
    })

    df_l2a = pd.DataFrame({
        'Shot Number' : shots_l2a,
        'Elevation Lowestmode' : elev_lowestmode,
        'Elevation Highestreturn' : elev_highestreturn,
        'Quality Flag' : quality_flag,
        'Sensitivity' : sensitivity,
        'Surface Flag' : surface_flag, 
        'RH98' : rh[:, 98],
    })
    
    return pd.merge(df_l1b, df_l2a, on='Shot Number', how='inner')


def get_combined_df_from_granule(l1b: h5py.File, l2a: h5py.File, beamNames: list[str], year:int, stride: int = 1) -> pd.DataFrame:
    """Concatenate all df Beams from a Granule, and add year column"""
    dfs = [get_df_from_beam(l1b, l2a, beamName, stride) for beamName in beamNames]
    df_granule = pd.concat(dfs, axis=0, ignore_index=True)
    df_granule['year'] = year
    return df_granule 


def get_all_GEDI_shots_within_roi(granules: list[int, h5py.File, h5py.File], roi: gpd.GeoDataFrame, beamNames: list[str]) -> gpd.GeoDataFrame:
    "Stack all GEDI shots from all granules and all beams within a ROI"
    all_gdf_filtered = []
    roi_polygone = roi.geometry.iloc[0]
    for year, l1b, l2a in granules :
        granule_filename_l1b = l1b.filename.split('/')[-1].split('.')[0]
        granule_filename_l2a = l2a.filename.split('/')[-1].split('.')[0]
        print(f"Année : {year} - Granule L1B : {granule_filename_l1b} - \n\t\t Granule L2A : {granule_filename_l2a}")
        granule_df = get_combined_df_from_granule(l1b, l2a, beamNames, year)
        granule_df['year'], granule_df['Granule_L1B'], granule_df['Granule_L2A'] = year, granule_filename_l1b, granule_filename_l2a
        granule_gdf = gpd.GeoDataFrame(
            granule_df, 
            geometry=gpd.points_from_xy(x = granule_df['Longitude'], y = granule_df['Latitude']),
            crs = 'EPSG:4326',
        )
        print(f"   → {len(granule_gdf)} points au total")
        granule_gdf.drop(columns=['Longitude', 'Latitude'], inplace=True)
        granule_gdf = granule_gdf[granule_gdf.within(roi_polygone)]
        print(f"   → {len(granule_gdf)} points dans la ROI")
        all_gdf_filtered.append(granule_gdf)
        del granule_df, granule_gdf
    return pd.concat(all_gdf_filtered, ignore_index=True)

def extract_waveform(open_files: dict[str, h5py.File], row: pd.Series) -> np.array:
    """Extract corresponding shot waveform from a row of DataFrame containing all shots in ROI"""
    granule = open_files[row['Granule Path']]
    beam = row['Beam']
    start = row['Sample Start Index'] - 1
    count = row['Sample Count']
    return  granule[f'{beam}/rxwaveform'][start: start+count][::-1] 


def compute_relative_height(row: pd.Series) -> np.array:
    "Compute Relative Height (elevation) of full waveform samples (ground elevation to 0))"
    zStart = row['Elevation bin0']
    zEnd = row['Elevation lastbin']
    count = row['Sample Count']
    zStretch = np.add(zEnd, np.multiply(range(count, 0, -1), ((zStart - zEnd) / int(count))))
    zRelative = zStretch - row['Elevation Lowestmode']  # Substracting ground elevation to make all shot groud elevation to zero
    return zRelative[::-1]  # Inverse to get croissant relative height from bottom to top of canopy, otherwise the return will begin from top of canopy to ground


def extract_FWF_from_shot_number(GEDI_shots: gpd.GeoDataFrame, open_files: dict[str, h5py.File], shot_number: int) -> tuple[np.array, np.array]:
    """Extract full waveform from shot number"""
    row = GEDI_shots[GEDI_shots['Shot Number'] == shot_number].iloc[0]
    fwf, zRelative = extract_waveform(open_files, row), compute_relative_height(row)
    print(f"""The waveform located at : {str(np.round(row['geometry'].y, 3))}, {str(np.round(row['geometry'].x, 3))} (shot ID: {row['Shot Number']}), is from beam "{row['Beam']}"
        and is stored in rxwaveform beginning at index {row['Sample Start Index']} and ending at index {row['Sample Start Index'] + row['Sample Count']}.""")
    return fwf, zRelative

def get_gedi_datasets_flat(granules_list: list[h5py.File]) -> list[tuple[h5py.File, str]]: 
    """Retourne une liste plate (granule, chemin_dataset)"""
    all_gedi_datasets = []
    for granule in granules_list:
        granule_sds = get_granule_datasets(granule)
        all_gedi_datasets.extend([(granule, sds) for sds in granule_sds])
    return all_gedi_datasets


def get_gedi_datasets_grouped(granules_list: list[h5py.File]) -> dict[h5py.File, list[str]]: 
    """Retourne un dict {granule: [chemins des datasets]}"""
    all_gedi_datasets = {}
    for granule in granules_list:
        all_gedi_datasets[granule] = get_granule_datasets(granule)
    return all_gedi_datasets


def filter_sds_flat(all_sds_flat: list[tuple[h5py.File, str]], suffix: str) -> list[tuple[h5py.File, str]]:
    """Return all SDS datasets matching a given name, across every beam of each granule. 
    (tuple format)"""
    return [sds_tuple for sds_tuple in all_sds_flat if sds_tuple[1].endswith(suffix) and sds_tuple[1].count('/') == 1]


def filter_sds_grouped(all_sds_grouped: dict[h5py.File, list[str]], suffix: str) -> dict[h5py.File, list[str]]:
    """Return all SDS datasets matching a given name, across every beam of each granule. 
    (dict format)"""
    return {granule : [sds for sds in sds_list if sds.endswith(suffix) and sds.count('/') == 1] for granule, sds_list in all_sds_grouped.items()}


def _get_coords_xy(roi: gpd.GeoDataFrame, spacing: int):
    """Get X, Y Coordinates with define spacing over a Region of Interest"""
    xmin, ymin, xmax, ymax = roi.total_bounds
    xcoords = [i for i in np.arange(xmin, xmax, spacing)]
    ycoords = [i for i in np.arange(ymin, ymax, spacing)]
    return xcoords, ycoords


def get_points_coords_roi(roi: gpd.GeoDataFrame, spacing: int=1000) -> np.array:
    """Get ndarray point coordinates of a Grid of 1km resolution over a ROI"""
    xcoords, ycoords = _get_coords_xy(roi, spacing)
    pointscoords = np.array(np.meshgrid(xcoords, ycoords)).T.reshape(-1, 2)
    return pointscoords


def get_points_grid(roi: gpd.GeoDataFrame) -> tuple[gpd.GeoSeries, gpd.GeoDataFrame]:
    """Get points Grid Coordinates over a ROI"""
    pointscoords = get_points_coords_roi(roi)
    points_grid = gpd.points_from_xy(x = pointscoords[:,0], y = pointscoords[:,1])
    grid = gpd.GeoSeries(points_grid, crs=roi.crs)
    grid.name = 'geometry'
    gridinside = gpd.sjoin(gpd.GeoDataFrame(grid), roi[['geometry']], how='inner')
    return grid, gridinside


def get_lines_grid(roi: gpd.GeoDataFrame, spacing: int=1000) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    "Get Grid Lines Coordinates over a ROI"
    xmin, ymin, xmax, ymax = roi.total_bounds
    xcoords, ycoords = _get_coords_xy(roi, spacing)
    vlines = [LineString([(x, ymin), (x, ymax)]) for x in xcoords]   # One line per xcoords
    hlines = [LineString([(xmin, y), (xmax, y)]) for y in ycoords]   # One line per ycoords
    grid_lines = gpd.GeoSeries(vlines + hlines, crs=roi.crs)
    grid_lines_gdf = gpd.GeoDataFrame(geometry=grid_lines)

    grid_lines_clipped = grid_lines.intersection(roi.geometry.iloc[0])      # Shapely Polygon Object
    grid_lines_clipped = grid_lines_clipped[~grid_lines_clipped.is_empty]   # Deleting empty geometries
    grid_lines_clipped = grid_lines_clipped[grid_lines_clipped.geom_type.isin(['LineString'])] # Deleting intersections reduced to points
    grid_lines_clipped_gdf = gpd.GeoDataFrame(geometry=grid_lines_clipped, crs=roi.crs)
    return grid_lines_gdf, grid_lines_clipped_gdf


def get_cells_grid(roi: gpd.GeoDataFrame, spacing: int=1000) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Return Grid Cells from ROI coordinates"""
    xcoords, ycoords = _get_coords_xy(roi, spacing)
    cells = [box(x, y, x + spacing, y + spacing) for x in xcoords for y in ycoords]
    grid_cells = gpd.GeoDataFrame(geometry=cells, crs=roi.crs)
    grid_cells['cell_id'] = np.arange(len(grid_cells))
    grid_cellsinside = gpd.sjoin(grid_cells, roi[['geometry']], how='inner')
    return grid_cells, grid_cellsinside


def get_number_of_shots_per_cells(GEDI_shots: gpd.GeoDataFrame, gridcells: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Compute the number of GEDI shots per cells grid"""
    joined = gpd.sjoin(GEDI_shots, gridcells[['geometry', 'cell_id']], how='left', predicate='within')
    counts = joined.groupby('cell_id').size().reset_index(name='n_points')
    gridcells = gridcells.merge(counts, on='cell_id', how='left')
    gridcells['n_points'] = gridcells['n_points'].fillna(0).astype(int)
    return gridcells

