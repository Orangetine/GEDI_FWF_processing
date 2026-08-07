import os
from gedi_fwf_processing.data_prep import (open_files, extract_waveform, OUTPUT_DIR,
                                           compute_relative_height, _get_coords_xy)
from gedi_fwf_processing.data_viz import DATA_VIZ_DIR

import geopandas as gpd
import numpy as np

from osgeo import gdal, osr
import matplotlib.pyplot as plt

STACKED_FWF_DIR = os.path.join(OUTPUT_DIR + 'stacked_fwf/')
os.makedirs(STACKED_FWF_DIR, exist_ok=True)

# for cells => get gedi shots => extract waveforms from cells shots => 
# interpolation des fwf on zrange et rasterisation des fullwaveform agrégées au niveau du pixel

def _get_zmin_zmax(GEDI_shots:gpd.GeoDataFrame, low_pct: int=0, high_pct: int=100) -> tuple[float, float]:
    """Get the global Relative Height minimum and maximum to construct zrange"""
    # RH0 est la hauteur relative où 0% de l'énergie à été accumulée (Elevation relative du sol)
    # RH98 est la hauteur relative où 98% de l'énergie à été accumulée (Elévation relative du sommet de la canopée)
    return np.percentile(GEDI_shots['RH0'], low_pct) - 5, np.percentile(GEDI_shots['RH98'], high_pct) + 5


def compute_zrange(GEDI_shots: gpd.GeoDataFrame, step: float=0.15, pct: tuple[int, int] = (0, 100)) -> np.ndarray:
    """
    Return zrange to interpolate FWF on a common z-axis.
    GEDI RX waveform is sampled every nanosecondes.
    distance = (vitesse lumière x temps) / 2   (aller-retour)
    distance = (300 0000 000 m/s x 1x10⁻⁹ s) / 2
    distance = 0.15m is the step between each sample of FWF. 
    """
    low_pct, high_pct = pct
    zmin, zmax = _get_zmin_zmax(GEDI_shots, low_pct, high_pct)
    return np.arange(zmin, zmax + step, step)


def aggregate_fwf_per_cell(GEDI_shots: gpd.GeoDataFrame, gridcells: gpd.GeoDataFrame, zrange: np.array) -> np.array:
    "Compute FWF aggreation by mean per cell, this function output a 2D array of shape (n_cells, n_bands (zrange's lenght))"
    joined = gpd.sjoin(GEDI_shots, gridcells[['geometry', 'cell_id']], how='inner', predicate='within')
    n_band = len(zrange)
    n_cells = len(gridcells)
    accum = np.zeros((n_cells, n_band))
    counter = np.zeros((n_cells, n_band))

    # Cells with shots in it (inner spatial join exclude cells with no points)
    unique_cell_ids = joined['cell_id'].unique()
    number_cells = len(unique_cell_ids)
    for i, (cell_id, group) in enumerate(joined.groupby('cell_id')):
        print(f"{i+ 1}/{number_cells} Aggregated Cell ID : {cell_id}")
        for _, row in group.iterrows():
            waveform, zRelative = extract_waveform(open_files, row), compute_relative_height(row)
            fit = np.interp(zrange, zRelative, waveform, left=np.nan, right=np.nan)
            mask = ~np.isnan(fit)
            accum[cell_id, mask] += fit[mask]
            counter[cell_id, mask] += 1

    return np.divide(accum, counter, out=np.full_like(accum, np.nan), where=counter > 0)


def plot_fwf_per_cell(GEDI_shots, gridcells, zrange, nplots: int = 9):
    """Plot interpolated FWF per cells, by default it plots the FWFs of nineth first cells, 
    otherwise it saves too much files because of the number of cells"""
    joined = gpd.sjoin(GEDI_shots, gridcells[['geometry', 'cell_id']], how='inner', predicate='within')
    for i, (cell_id, shots_per_cell) in enumerate(joined.groupby('cell_id')):
        plt.figure(figsize=(10, 8))
        if i > nplots - 1 : 
            break
        for _, row in shots_per_cell.iterrows():
            waveform, zRelative = extract_waveform(open_files, row), compute_relative_height(row)
            fit = np.interp(zrange, zRelative, waveform, left=np.nan, right=np.nan)
            plt.plot(zrange, fit)
        plt.xlabel('Elévation (m)')
        plt.ylabel('Amplitude (DN)')
        plt.title(f"Formes d'onde complètes interpolées : Cellule {cell_id}")    
        plt.savefig(DATA_VIZ_DIR + f'interpolated_fwf_cell_{cell_id}')
        plt.close()    

def get_fwf_cube(roi: gpd.GeoDataFrame, gridcells: gpd.GeoDataFrame,  mean_per_cell: np.array, spacing: int=1000) -> np.array:
    "Place each FWF to its place in a cube of shape (nrows, ncols, nbands)"
    xcoords, ycoords = _get_coords_xy(roi, spacing)
    n_cols = len(xcoords) 
    n_rows = len(ycoords) 
    n_cells, n_band = mean_per_cell.shape
    cube = np.full((n_rows, n_cols, n_band), np.nan)
    for cell_id in range(n_cells):
        row = gridcells.iloc[cell_id]['row']
        col = gridcells.iloc[cell_id]['col']
        cube[row, col, :] = mean_per_cell[cell_id]
    return cube


def save_stacked_fwf_as_tiff(cube: np.array, roi: gpd.GeoDataFrame, filename: str='stacked_fwf_roi.tif',  spacing: int=1000) -> None:
    "Saving stacked full waveforms in GeoTiff"
    xcoords, ycoords = _get_coords_xy(roi, spacing)
    nrows, ncols, nbands = cube.shape

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(STACKED_FWF_DIR + filename, ncols, nrows, nbands, gdal.GDT_Float32)

    xmin = min(xcoords)
    ymax = max(ycoords)

    geotransform = (xmin, spacing,0, ymax, 0, -spacing)
    dataset.SetGeoTransform(geotransform)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(roi.crs.to_epsg())
    dataset.SetProjection(srs.ExportToWkt())

    for b in range(nbands):
        band = dataset.GetRasterBand(b + 1)
        corrected_band = np.flipud(cube[:, :, b])
        band.WriteArray(corrected_band)
        band.SetNoDataValue(np.nan)
    dataset.FlushCache()
    dataset = None


