import gedi_fwf_processing.data_prep as gprep
from gedi_fwf_processing.data_prep import GEDI_shots_path, EXTENT_DIR, open_files, extract_waveform, compute_relative_height
import geopandas as gpd
import pandas as pd
import numpy as np

# for cells => get gedi shots => extract waveforms from cells shots => 
# interpolation on zrange rasterisation des fullwaveform agrégées au niveau du pixel


GEDI_012_BA_GDF = gpd.read_file(GEDI_shots_path)
# Region of interest
north_morroco_roi = gpd.GeoDataFrame.from_file(
    EXTENT_DIR + 'emprise_gedi.geojson',
)
north_morroco_roi = north_morroco_roi.to_crs(3857)

def _get_zmin_zmax(GEDI_shots:gpd.GeoDataFrame, low_pct: int=0, high_pct: int=100) -> tuple[float, float]:
    """Get the global Relative Height minimum and maximum to construct zrange"""
    # z_top = GEDI_shots['Elevation bin0'] - GEDI_shots['Elevation Lowestmode']
    # z_bottom = GEDI_shots['Elevation lastbin'] - GEDI_shots['Elevation Lowestmode']
    return np.percentile(GEDI_shots['RH0'], low_pct) - 5, np.percentile(GEDI_shots['RH98'], high_pct) + 5



def compute_zrange(GEDI_shots: gpd.GeoDataFrame, step: float=0.15, pct: tuple[int, int] = (0, 100)) -> np.ndarray:
    """
    Return zrange to interpolate FWF on a common z-axis.
    GEDI RX waveform is sampled every nanosecondes.
    distance = (vitesse lumière x temps) / 2   (aller-retour)
    distance = (300 0000 000 m/s x 1x10⁻⁹ s) / 2
    distance = 0.15m 
    """
    low_pct, high_pct = pct
    zmin, zmax = _get_zmin_zmax(GEDI_shots, low_pct, high_pct)
    return np.arange(zmin, zmax + step, step)

# GEDI_filtered = GEDI_012_BA_GDF[GEDI_012_BA_GDF['Quality Flag'] == 1]
zrange_native = compute_zrange(GEDI_012_BA_GDF, pct=(1, 99))
zrange_1m = compute_zrange(GEDI_012_BA_GDF, step=1, pct=(1,99))

# print("Zrange native :", zrange_native, len(zrange_native), sep='\n')
# print("Zrange 1m :", zrange_1m, len(zrange_1m), sep='\n')

gridcells, gridcellsinside  = gprep.get_cells_grid(north_morroco_roi)

GEDI_012_BA_GDF_with_cellsid = gpd.sjoin(GEDI_012_BA_GDF, gridcells[['geometry', 'cell_id']], how='left', predicate='within')

print(gridcells)

joined = gpd.sjoin(GEDI_012_BA_GDF, gridcells[['geometry', 'cell_id']], how='inner', predicate='within')

nband = len(zrange_native)
n_cells = len(gridcells)
accum = np.zeros((n_cells, nband))
counter = np.zeros((n_cells, nband))



unique_cell_ids = joined['cell_id'].unique()
number_cells = len(unique_cell_ids)


cell_id_count = 0
for cell_id, group in joined.groupby('cell_id'):
    cell_id_count += 1
    print(f"{cell_id_count}/{number_cells} Cell iD : {cell_id}")
    # print(group)
    for _, row in group.iterrows():
        waveform, zRelative = extract_waveform(open_files, row), compute_relative_height(row)
        fit = np.interp(zrange_native, zRelative, waveform, left=np.nan, right=np.nan)
        mask = ~np.isnan(fit)
        accum[cell_id, mask] += fit[mask]
        counter[cell_id, mask] += 1

mean_per_cell = np.divide(accum, counter, out=np.full_like(accum, np.nan), where=counter > 0)

print(mean_per_cell.shape)
