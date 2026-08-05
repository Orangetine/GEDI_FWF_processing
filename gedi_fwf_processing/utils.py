from __future__ import annotations

import os
import h5py
import numpy as np
import pandas as pd
import geoviews as gv
import geopandas as gpd
import cartopy.crs as ccrs


import matplotlib.pyplot as plt

from shapely.geometry import box
from shapely.geometry import LineString

from collections.abc import Iterable

import holoviews as hv
from geoviews import tile_sources as gvts

from IPython.display import display

gv.extension('bokeh', 'matplotlib')

ROOT_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
DATA_DIR = os.path.join(ROOT_DIR, "data/")
GRANULES_DIR = os.path.join(DATA_DIR, 'granules/')
L1B_GRANULES_DIR = os.path.join(GRANULES_DIR, 'l1b/')
L2A_GRANULES_DIR = os.path.join(GRANULES_DIR, 'l2a/')
EXTENT_DIR = os.path.join(DATA_DIR, 'emprise/')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output/')
DATA_VIZ_DIR = os.path.join(OUTPUT_DIR, 'data_vizualization/')
DATA_INFO_DIR = os.path.join(OUTPUT_DIR, 'GEDI_datasets_info/')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_VIZ_DIR, exist_ok=True)
os.makedirs(DATA_INFO_DIR, exist_ok=True)


def get_GEDI_files(granules_dir: str) -> list[str]:
    gedi_files = [f for f in os.listdir(granules_dir) if f.endswith(".h5")]
    gedi_files.sort()
    return  gedi_files

def get_GEDI_granule_h5_list(directory: str, gedi_files_list: list[str]) -> list[h5py.File]:
    return [h5py.File(directory + gedi_file, 'r') for gedi_file in gedi_files_list]


def _get_granule_keys(granule_hdf5: h5py.File) -> list[str] : 
    return list(granule_hdf5.keys())


def get_granule_datasets(GEDIhdf5: h5py.File) -> list[str]:
    """Collect each dataset for each BEAM"""
    granule_objects = []
    GEDIhdf5.visit(granule_objects.append) 
    return [object for object in granule_objects if isinstance(GEDIhdf5[object], h5py.Dataset)]


def get_datasets_from_beamname(granule_datasets_list: list[str], beam_name) -> list[str]:
    """Get all datasets name (attributs) from beam name"""
    return [dataset for dataset in granule_datasets_list if beam_name in dataset]


def get_GEDI_granules_downloaded(directory: str, gedi_filenames: list[str]) -> None:
    "Write text file with granules downloaded list"
    DATA_ACCESS_URLS = {
        'GEDI01' : 'https://search.earthdata.nasa.gov/search/granules?p=C2142749196-LPCLOUD',
        'GEDI02' : 'https://search.earthdata.nasa.gov/search/granules?p=C2142771958-LPCLOUD'
    }
    name  = gedi_filenames[0]
    product, suffix = name.split('_')[0], name.split('_')[1]
    output_filename = f"GEDI_granules_list_l{product[-1]}{suffix.lower()}.txt"

    product_key = product[:6]   # {'GEDI01' or 'GEDI02'}
    data_access = DATA_ACCESS_URLS[product_key]
    
    with open(directory + output_filename, 'w') as f:
        f.write('==='*12 + '\n')
        f.write(f'List of {"".join([product, suffix])} granules downloaded\n')
        f.write('==='*12 + '\n\n')
        f.write(data_access + '\n\n')
        for gedi_filename in gedi_filenames:
            f.write(gedi_filename + '\n')


def get_GEDI_data_file_informations(granules_list: list[h5py.File], filename: str = 'GEDI_files_informations.txt') -> None:
    """Write a text file with GEDI Metadata Files informations in the Output directory"""
    granule_keys = _get_granule_keys(granules_list[0])
    granule_metadata = list(granules_list[0]['METADATA']['DatasetIdentification'].attrs)

    with open(DATA_INFO_DIR + filename, "w") as f:
        f.write(
            f"Structure du fichier H5DF constituant la granule GEDI  :\n{granule_keys}\n\n")
        for granule in granules_list:
            f.write("==="*25 + "\n")
            granule_name = granule['METADATA']['DatasetIdentification'].attrs['fileName'].split('.')[0]
            f.write(f"Granule METADATA : {granule_name}\n")
            f.write("==="*25 + "\n")
            for metadata in granule_metadata:
                f.write(f"{metadata} : {granule['METADATA']['DatasetIdentification'].attrs[metadata]}\n")


def get_GEDI_beams_informations(granule_list: list[h5py.File], filename: str = 'GEDI_beams_informations.txt') -> None:
    """Write in output directory a text file with each GEDI datasets per beam and per granule"""
    beamNames = [group for group in granule_list[0].keys() if group.startswith('BEAM')]
    with open(DATA_INFO_DIR + filename, 'w') as f:
        f.write(
            "The GEDI instrument consists of 3 lasers producing a total of 8 beam ground transects.\n" + \
            "The eight remaining groups contain data for each of the eight GEDI beam transects.\n" + \
            "For additional information, be sure to check out: https://gedi.umd.edu/instrument/specifications/.\n\n"
        )
        f.write(f"The folder contains {len(granule_list)} GEDI granules with {len(beamNames)} BEAMS each. \n\n")
        f.write("==="*3 + " Beams'Type " + "==="*3 + "\n")
        for beam in beamNames:
            f.write(f"{beam} is a {granule_list[0][beam].attrs['description']} \n")

        f.write("\n\n")
        for granule in granule_list:
            granule_sds = get_granule_datasets(granule)
            granule_name = granule['METADATA']['DatasetIdentification'].attrs['fileName'].split('.')[0]
            for beam in beamNames:
                beam_sds = get_datasets_from_beamname(granule_sds, beam)
                f.write("==="*22 + "\n")
                f.write(f"Granule : {granule_name} \n")
                f.write(f"{beam}'s Datasets ({len(beam_sds)})\n\n")
                f.write(f"{beam_sds} \n\n")


def get_datasets_specification(granule: h5py.File) -> None:
    """Write in output directory a text file with description of each GEDI product datasets"""
    beam_sds = get_datasets_from_beamname(get_granule_datasets(granule), 'BEAM0000')
    name = granule.filename.split('/')[-1]
    product, suffix = name.split('_')[0], name.split('_')[1]     # product : {'GEDI01' or 'GEDI02'}, suffix : {'A' or 'B'}
    filename = f'GEDI_datasets_specification_l{product[-1]}{suffix.lower()}.txt'
    with open(DATA_INFO_DIR + filename, 'w') as f:
        f.write(
            f"{product}_{suffix} Datasets Description ({len(beam_sds)} datasets per beam)\n\n" +
            "rxwaveform est le tableau qui contient les waveforms\n" +
            "Ce n'est pas un tableau bien rangé (n_shots, n_samples)\n"+
            """Mais un tableau 1D qui contient bout à bout tous les échantillons \nde tous les shots du beam à la suite.\n"""+
            """rxwaveform = [ shot1_ech1, shot1_ech2, ..., shot1_echN1,\n\t\t\t\tshot2_ech1, shot2_ech2, ..., shot2_echN2,\n\t\t\t\tshot3_ech1, ..., shot3_echN3, ... ]\n""" +
            "Chaque shots sur le terrain n'a pas le même nombre d'échantillons.\n"+
            "Un shot sur terrain plat de peu de végétation a une fenêtre d'enregistrement courte,\n"+
            "un shot sur relief accidenté avec canopée dense a une fenêtre bien plus longue."   
        )
        f.write("\n\n")
        f.write( "==="*7 + "\n" +"Attributs'description\n"+ "==="*7 + "\n\n")
        for dataset in beam_sds:
            f.write(f"{dataset.replace('BEAM0000/', '')} => {granule[dataset].attrs['description']}\n")


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

def _get_vdims(GEDI_shots: gpd.GeoDataFrame) -> list[str] :
    """Returns shots'attributs (columns'names)"""
    return [col for col in GEDI_shots if col != 'geometry']

def extract_waveform(open_files: dict[str, h5py.File], row: pd.Series) -> tuple[np.array, np.array]:
    """Extract corresponding shot waveform from a row of DataFrame containing all shots in ROI"""
    granule = open_files[row['Granule Path']]
    beam = row['Beam']
    start = row['Sample Start Index']- 1
    count = row['Sample Count']
    zStart = row['Elevation bin0']
    zEnd = row['Elevation lastbin']
    zStretch = np.add(zEnd, np.multiply(range(count, 0, -1), ((zStart - zEnd) / int(count))))
    zRelative = zStretch - row['Elevation Lowestmode']
    return  granule[f'{beam}/rxwaveform'][start: start+count][::-1], zRelative[::-1]

def extract_FWF_from_shot_number(GEDI_shots: gpd.GeoDataFrame, open_files: dict[str, h5py.File], shot_number: int) -> tuple[np.array, np.array]:
    """Extract full waveform from shot number"""
    row = GEDI_shots[GEDI_shots['Shot Number'] == shot_number].iloc[0]
    fwf, zRelative = extract_waveform(open_files, row)
    print(f"""The waveform located at : {str(np.round(row['geometry'].y, 3))}, {str(np.round(row['geometry'].x, 3))} (shot ID: {row['Shot Number']}), is from beam "{row['Beam']}"
        and is stored in rxwaveform beginning at index {row['Sample Start Index']} and ending at index {row['Sample Start Index'] + row['Sample Count']}.""")
    return fwf, zRelative

def plot_some_fwf(open_files: dict[str, h5py.File], GEDI_shots: gpd.GeoDataFrame, number: int=5,  filename: str = 'Some_FWF.png') -> None:
    """Static png plot of five first full waveforms"""
    plt.figure(figsize=(10, 8))
    for i in range(number):
        fwf, zStretch = extract_waveform(open_files, GEDI_shots.iloc[i])
        plt.plot(zStretch, fwf)

    plt.xlabel("Elévation (m)")
    plt.ylabel("Amplitude (DN)")
    plt.title("Formes d'onde complètes des cinq premiers tirs")
    plt.savefig(DATA_VIZ_DIR + filename)

def plot_a_FWF(open_files: dict[str, h5py.File], GEDI_shots: gpd.GeoDataFrame, indices: Iterable[int] = range(1994,1999), filename: str='Random_FWF.html') -> None:
    """Interactive HTML plot of full waveforms of some GEDI shots"""
    waveforms = {}
    for i in indices:
        fwf, zRelative = extract_waveform(open_files, GEDI_shots.iloc[i])
        wvDF = pd.DataFrame({'Elevation (m)': zRelative, 'Amplitude (DN)': fwf})
        waveforms[i] = hv.Curve(wvDF)

    plot = hv.HoloMap(waveforms, kdims='Full Waveform index').opts(width=600, height=400)
    hv.save(plot, DATA_VIZ_DIR + filename)
    display(plot)

def pointVisual(features, vdims, crs):
    """Plot GEDI shots with Esri Overlay"""
    return (gvts.ESRI * gv.Points(features, vdims=vdims, crs=crs)
            .options(tools=['hover'], height=500, width=900, size=5,
                     color='yellow', fontsize={'xticks': 10, 'yticks': 10, 
                                                'xlabel':16, 'ylabel': 16},
                     title='Plotting GEDI Shots'))

def plot_shots_and_roi(roi: gpd.GeoDataFrame, GEDI_shots: gpd.GeoDataFrame, filename: str='gedi_points_map.html') ->  None:
    """Plot GEDI Shots with ROI"""
    vdims = _get_vdims(GEDI_shots)
    plot = (
        gv.Polygons(roi['geometry'], crs=ccrs.epsg(3857))
                .opts(line_color='red', color=None, line_width=3)
        * 
        pointVisual(GEDI_shots, vdims=vdims, crs=ccrs.epsg(3857))
        ).opts(width=900, height=500, active_tools=['wheel_zoom'])

    hv.save(plot, DATA_VIZ_DIR + filename)
    display(plot)


def plot_grid_and_GEDI_shots(roi: gpd.GeoDataFrame, GEDI_shots: gpd.GeoDataFrame, 
                             gridpoints: gpd.GeoDataFrame, gridlines: gpd.GeoDataFrame, filename: str='gedi_grid_points_map.html') -> None:
    """Plot GEDI grid and shots to visualize the number of shots per cells of 1km"""
    vdims = _get_vdims(GEDI_shots)
    plot = (
        gvts.ESRI 
        *
        gv.Polygons(roi['geometry'], crs=ccrs.epsg(3857))
                .opts(line_color='red', color=None, line_width=3)
        * 
        pointVisual(GEDI_shots, vdims=vdims, crs=ccrs.epsg(3857))

        *
        gv.Path(gridlines, crs=ccrs.epsg(3857))
                .opts(line_color='black', line_width=3)

        *
        gv.Points(gridpoints, crs=ccrs.epsg(3857))
                .opts(color='red', size=18, marker='+', alpha=0.8)
        
        ).opts(
            width=900, 
            height=500,
            active_tools=['wheel_zoom'],
            title='Plotting Grid and GEDI shots'
    )
    hv.save(plot, DATA_VIZ_DIR + filename)
    display(plot)
    

def plot_density_map(gridcells: gpd.GeoDataFrame, roi: gpd.GeoDataFrame, filename: str='gedi_shots_density_map.html'):
    """Plot GEDI shots density per 1km cells"""
    plot = (
        gvts.ESRI
        * 
        gv.Polygons(gridcells, vdims=['n_points'], crs=ccrs.epsg(3857)).opts(
        color='n_points', cmap='YlOrRd', colorbar=True, line_width=0.3, line_color='gray',  tools=['hover']
        )
        *
        gv.Polygons(roi['geometry'], crs=ccrs.epsg(3857)).opts(line_color = 'red', color=None)
        ).opts(
            width=900, 
            height=500,
            active_tools=['wheel_zoom'],
            title='GEDI shots Density Map'
    )
    hv.save(plot, DATA_VIZ_DIR + filename)
    display(plot)

def plot_GEDI_shot(GEDI_shots: gpd.GeoDataFrame, shot_number: int=122320300200224555, fileprefix:str = f'gedi_shot_') -> None:
    "Plot a GEDI shot from his Shot Number"
    vdims = _get_vdims(GEDI_shots)
    sample = GEDI_shots[GEDI_shots['Shot Number'] == shot_number]
    x = sample.geometry.iloc[0].x
    y = sample.geometry.iloc[0].y
    buffer = 200

    plot = (
        gvts.ESRI * gv.Points(sample, vdims=vdims, crs=ccrs.epsg(3857))
                .options(tools=['hover'], active_tools=['wheel_zoom'], 
                        height=500, width=900, size=50,
                        line_color='green', line_width = 5, color='yellow', 
                        fontsize={'xticks': 10, 'yticks': 10, 
                                            'xlabel':16, 'ylabel': 16},
                        marker='diamond',                           
                        title=f'Position GEDI shot number : {shot_number}')
    )\
        .opts(
        xlim=(x - buffer, x + buffer),
        ylim=(y - buffer, y + buffer),
    )
    hv.save(plot, DATA_VIZ_DIR + fileprefix + f'{shot_number}.html')
    display(plot)


def plot_FWF_from_shot_number(GEDI_shots: gpd.GeoDataFrame, open_files: dict[str, h5py.File], shot_number: int=122320300200224555) -> None:
    """Plot full waveform from shot number"""
    fwf, zRelative = extract_FWF_from_shot_number(GEDI_shots, open_files, shot_number)
    wvDF = pd.DataFrame({'Elevation (m)': zRelative, 'Amplitude (DN)': fwf})
    plot = hv.Curve(wvDF).opts(tools=['hover'], height=500, width=900, title=f'Full waveform from shot : {shot_number}')
    hv.save(plot, DATA_VIZ_DIR + f'gedi_fwf_shot_{shot_number}.html')
    display(plot)


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