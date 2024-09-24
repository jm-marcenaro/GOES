import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from datetime import datetime, timedelta
import xarray as xr
import urllib.request
from tqdm import tqdm
from shapely.geometry import mapping
import rasterio
import json
import os
import glob
import sys

# Capture the date of interest sent by the client

# Read input data from stdin
stdin_01 = sys.stdin.read()

# Parse JSON data
stdin_02 = json.loads(stdin_01)

# Extract date of interest
date_oi_01 = stdin_02.get('date_oi')

# Parse to datetime
date_oi_02 = datetime.strptime(date_oi_01, '%Y-%m-%d %H:%M')

# Initialize EE
ee.Initialize()

# Define dates of interest
N = 6 # N° de horas hacia atras de la animación
UTC = 3 # Pasaje entre UTC-0 y UTC-3

# Definir el lapso de la animación

# DS_UTC_3 = datetime.now() - timedelta(hours=N)
# DE_UTC_3 = datetime.now()

# Convertir a UTC 0 y al formato de entrada de GEE
DE_UTC_0 = (date_oi_02 + timedelta(hours=UTC)).strftime('%Y-%m-%dT%H:%M')
DS_UTC_0 = (date_oi_02 + timedelta(hours=UTC) - timedelta(hours=N)).strftime('%Y-%m-%dT%H:%M')

# Read ROI & grid shapefiles

# ROI
GDF_ROI = gpd.read_file(r"GEE/GIS/ROI.shp")

BB_01 = GDF_ROI.total_bounds

# Define coordinates
x_min, y_min, x_max, y_max = BB_01

# Create ee.Geometry
ROI = ee.Geometry.Rectangle([x_min, y_min, x_max, y_max])

# GRID
GDF_GRD = gpd.read_file(r"GEE/GIS/Grid.shp")

# Define IC
C_01 = ee.ImageCollection("NOAA/GOES/16/MCMIPF")\
        .filterBounds(ROI)\
        .filterDate(DS_UTC_0, DE_UTC_0)

# Get image collection size
S_01 = C_01.size().getInfo()

# Loop over the images starting from the last one, and keep 1 every 3 images

# Create an empty ImageCollection to store the filtered images
C_02 = ee.ImageCollection([])

for i in range(S_01 - 1, -1, -3):  # Start at the last index, move backwards by 3

    # Get the image at the current index
    image = ee.Image(C_01.toList(S_01).get(i))

    # Merge the image with the collection
    C_02 = C_02.merge(ee.ImageCollection([image]))

# Reverse the order of the collection
C_02 = C_02.sort('system:time_start')

# Get image collection size
S_02 = C_02.size().getInfo()

# Definir función que escala las imágenes
def scale_red_blue_nir(image):
    
    sc_blue = ee.Number(image.get("CMI_C01_scale"))
    off_blue = ee.Number(image.get("CMI_C01_offset"))
    
    sc_red = ee.Number(image.get("CMI_C02_scale"))
    off_red = ee.Number(image.get("CMI_C02_offset"))
    
    sc_nir = ee.Number(image.get("CMI_C03_scale"))
    off_nir = ee.Number(image.get("CMI_C03_offset"))
    
    blue_sc_off = image.select("CMI_C01").multiply(sc_blue).add(off_blue).rename("bl_scaled_off")
    red_sc_off = image.select("CMI_C02").multiply(sc_red).add(off_red).rename("red_scaled_off")
    nir_sc_off = image.select("CMI_C03").multiply(sc_nir).add(off_nir).rename("nir_scaled_off")
    
    # Add the scaled bands back to the image
    return image.addBands([blue_sc_off, red_sc_off, nir_sc_off])

# Define function to calculate the synthetic green band
def synthetic_green(image):
    
    green_1 = image.select("red_scaled_off").multiply(0.45)
    green_2 = image.select("nir_scaled_off").multiply(0.10)
    green_3 = image.select("bl_scaled_off").multiply(0.45)

    green = green_1.add(green_2).add(green_3).rename("GREEN")
    
    return image.addBands(green)

# Map the functions over the IC
C_02 = C_02.map(scale_red_blue_nir)
C_02 = C_02.map(synthetic_green)

# Download images locally

# First remove previously generated images
for F in glob.glob(r'GEE/Output/*.tif'):
    os.remove(F)

TSs_01 = [] # List to append timestamps

for i in range(S_02):
    
    I = ee.Image(C_02.toList(S_02).get(i))

    TS = (datetime.utcfromtimestamp(I.getInfo()["properties"]["system:time_start"] / 1000) - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

    TSs_01.append(TS)
    
    for (E, G) in enumerate(range(len(GDF_GRD))):
        
        FN = f"{E+1:02d}.G-{i+1:03d}.tif"

        # Existing code to download images
        GRD = ee.Geometry(mapping(GDF_GRD["geometry"][G]))
        url = I.getDownloadURL({
            "scale": 5000,
            "bands": ["red_scaled_off", "GREEN", "bl_scaled_off"],
            "crs": "EPSG:4326",
            "region": GRD,
            "filePerBand": True,
            "format": "GEO_TIFF"
        })
        urllib.request.urlretrieve(url, fr"GEE/Output/{FN}")
        # print(f"{FN} downloaded! - {D}")

# Delete duplicate TSs and sort by date
TSs_01 = sorted(list(set(TSs_01)), key=lambda TS: datetime.strptime(TS, "%Y-%m-%d %H:%M"))

# Sobrescribir archivo TSs.json con la fecha y hora en que fue capturada cada imagen    
with open('GEE/Output/PNGs/TSs.json', 'w') as f:
    json.dump(TSs_01, f)

# Read images with rasterio, plot them and overlay a shapefile
DICT_Rs_01 = {}

for i in range(S_02):

    for j in range(len(GDF_GRD)):

        FN = f"{j+1:02d}.G-{i+1:03d}.tif"

        DICT_Rs_01[f"{FN}"] = rasterio.open(fr"GEE/Output/{FN}")

GDF_PROVs = gpd.read_file(r"GEE/GIS/Provincias.shp")

# Dictionary of bounds
Bs = {}

for i in range(len(GDF_GRD)):
    
    Bs[f"{i}"] = DICT_Rs_01[f"{i+1:02d}.G-001.tif"].bounds

# Define image ratio
IR = DICT_Rs_01[f"01.G-001.tif"].shape[0] / DICT_Rs_01[f"01.G-001.tif"].shape[1]

# First remove previously generated images
for F in glob.glob(r'GEE/Output/PNGs/*.png'):
    os.remove(F)

# Generate PNGs
for t in range(S_02):
    
    fig, ax = plt.subplots(figsize=(5, 5*IR))

    for g, (k_2, B) in zip(range(len(GDF_GRD)), Bs.items()):

        RGB = np.stack([DICT_Rs_01[f"{g+1:02d}.G-{t+1:03d}.tif"].read(j) for j in range(1, 4)], axis=-1)
        
        _ = ax.imshow(RGB, extent=(B.left, B.right, B.bottom, B.top), zorder=1, vmin=0, vmax=0.7)

    ax.axis("off")

    GDF_PROVs.plot(ax=ax, facecolor="none", edgecolor="white", zorder=2, linewidth=.25)

    fig.tight_layout()
    plt.savefig(fr"GEE/Output/PNGs/T_{t+1:03d}.png")
    # TSs_02.append({f"T_{t+1:03d}.png" : TS})