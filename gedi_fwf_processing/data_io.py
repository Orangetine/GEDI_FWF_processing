from __future__ import annotations

import h5py
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output/')
DATA_INFO_DIR = os.path.join(OUTPUT_DIR, 'GEDI_datasets_info/')

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