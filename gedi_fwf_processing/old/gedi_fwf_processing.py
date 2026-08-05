import numpy as np
import pandas as pd

import holoviews as hv
from IPython.display import display

from gedi_fwf_processing.data_prep import (get_gedi_datasets_flat, get_gedi_datasets_grouped, 
                                           filter_sds_flat, filter_sds_grouped, granule_h5_list_l1b)


# Every datasets from each beam and granule
all_sds_flat = get_gedi_datasets_flat(granule_h5_list_l1b)
all_sds_grouped = get_gedi_datasets_grouped(granule_h5_list_l1b)
# Sample Count datasets from each beam and granule
sds_sample_count_flat = filter_sds_flat(all_sds_flat, suffix='/rx_sample_count')
sds_sample_count_grouped = filter_sds_grouped(all_sds_grouped, suffix='/rx_sample_count')
# Start index datasets from each beam and granule
sds_sample_start_index_flat = filter_sds_flat(all_sds_flat, suffix='/rx_sample_start_index')
sds_sample_start_index_grouped = filter_sds_grouped(all_sds_grouped, suffix='/rx_sample_start_index')
# Start waveform datasets from each beam and granule
sds_waveform_flat = filter_sds_flat(all_sds_flat, '/rxwaveform')
sds_waveform_grouped = filter_sds_grouped(all_sds_grouped, '/rxwaveform')
# Start shot number datasets from each beam and granule
sds_shot_number_flat = filter_sds_flat(all_sds_flat, '/shot_number')
sds_shot_number_grouped = filter_sds_grouped(all_sds_grouped, '/shot_number')

granule, path_sc = sds_sample_count_flat[0]
print(f"{granule} -> {path_sc} is {granule[path_sc].attrs['description']}")

granule, path_ssi = sds_sample_start_index_flat[0]
print(f"{granule} -> {path_ssi} is {granule[path_ssi].attrs['description']}")

granule, path_wf = sds_waveform_flat[0]
print(f"{granule} -> {path_wf} is {granule[path_wf].attrs['description']}")

granule, path_sn = sds_shot_number_flat[0]
print(f"{granule} -> {path_sn} is {granule[path_sn].attrs['description']}")



shot = 316060100200223812


for granule, path_sn in sds_shot_number_flat :
    shots = granule[path_sn][()]
    local_idx = np.where(shots == shot)[0]
    if local_idx.size:
        local_idx = local_idx[0]
        beam = path_sn.split('/')[0]
        break

wf_count = granule[f"{beam}/rx_sample_count"][local_idx]
wf_start = granule[f"{beam}/rx_sample_start_index"][local_idx] - 1
wf_shot_number = granule[f"{beam}/shot_number"][local_idx]

# latitude_bin0 : Latitude of the start of the RX window.
wf_latitude = granule[f"{beam}/geolocation/latitude_bin0"][local_idx]
# longitude_bin0 : Longitude of the start of the RX window.
wf_longitude = granule[f"{beam}/geolocation/longitude_bin0"][local_idx]

# Grab the elevation recorded at the start and end of the full waveform capture
# elevation_bin0 : Height of the start of the RX window, relative to the WGS-84 ellipsoid.
z_start = granule[f"{beam}/geolocation/elevation_bin0"][local_idx]
# elevation_lastbin : Height of the end of the RX window, relative to the WGS-84 ellipsoid.
z_end = granule[f"{beam}/geolocation/elevation_lastbin"][local_idx]
# Extraction des valeurs d'intensité de la waveform 
waveform = granule[f"{beam}/rxwaveform"][wf_start:wf_start + wf_count]


# Find elevation difference from start to finish and divide into equal intervals based on sample_count
z_stretch = np.add(z_end, np.multiply(range(wf_count, 0, -1), ((z_start - z_end) / int(wf_count))))


waveform_df = pd.DataFrame({
    "Elevation (m)": z_stretch, "Amplitude (DN)" : waveform
})

display(hv.Curve(waveform_df))

print(waveform_df)

print()
print(f"The waveform located at: {str(wf_latitude)}, {str(wf_longitude)} (shot ID: {wf_shot_number}, index {local_idx}) is from beam {beam} \
      and is stored in rxwaveform beginning at index {wf_start} and ending at index {wf_start + wf_count}")

# index = np.where(all_shots_array == shot)
# print(index)