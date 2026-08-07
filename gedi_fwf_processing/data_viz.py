from __future__ import annotations

import os
import h5py
import pandas as pd
import geopandas as gpd
import cartopy.crs as ccrs

import geoviews as gv
import holoviews as hv
import matplotlib.pyplot as plt
from IPython.display import display
from geoviews import tile_sources as gvts

gv.extension('bokeh', 'matplotlib')

from collections.abc import Iterable
from gedi_fwf_processing.data_prep import extract_waveform, compute_relative_height, extract_FWF_from_shot_number

ROOT_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output/')
DATA_VIZ_DIR = os.path.join(OUTPUT_DIR, 'data_vizualization/')

os.makedirs(DATA_VIZ_DIR, exist_ok=True)

def _get_vdims(GEDI_shots: gpd.GeoDataFrame) -> list[str] :
    """Returns shots'attributs (columns'names)"""
    return [col for col in GEDI_shots if col != 'geometry']


def plot_some_fwf(open_files: dict[str, h5py.File], GEDI_shots: gpd.GeoDataFrame, number: int=5,  filename: str = 'Some_FWF.png') -> None:
    """Static png plot of five first full waveforms"""
    plt.figure(figsize=(10, 8))
    for i in range(number):
        fwf, zRelative = extract_waveform(open_files, GEDI_shots.iloc[i]), compute_relative_height(GEDI_shots.iloc[i])
        plt.plot(zRelative, fwf)

    plt.xlabel("Elévation (m)")
    plt.ylabel("Amplitude (DN)")
    plt.title("Formes d'onde complètes des cinq premiers tirs")
    plt.savefig(DATA_VIZ_DIR + filename)

def plot_a_FWF(open_files: dict[str, h5py.File], GEDI_shots: gpd.GeoDataFrame, indices: Iterable[int] = range(1994,1999), filename: str='Random_FWF.html') -> None:
    """Interactive HTML plot of full waveforms of some GEDI shots"""
    waveforms = {}
    for i in indices:
        fwf, zRelative = extract_waveform(open_files, GEDI_shots.iloc[i]), compute_relative_height(GEDI_shots.iloc[i])
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
    ).opts(
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


