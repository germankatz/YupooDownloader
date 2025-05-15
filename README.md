<h1 style="text-align:center;">YupooDownloader</h1>

<p style="text-align:center;">This script downloads all albums from a Yupoo gallery into a dump folder, creating a subfolder for each album named after its title.</p>

---

## Setup

Ensure you have python 3.6+ installed.

```
pip install -r requirements.txt

```

### Configure details.json

In the array yupoos you can place an object with a structure like this:

```
{
    "productCount": "n",
    "yupoo_link": "https://namename.x.yupoo.com/categories/3484623"
}
```

It will download the first `n` albums in the same order as the yupoo category.

### Configure the script

You can adjust these variables at the top of the script to maximize the performance:

```
# Configuración de reintentos para imágenes
MAX_RETRIES_FOR_IMAGES = 3  # Variable para controlar cuántas veces reintentar la descarga
RETRY_DELAY_MS = 1000  # Tiempo de espera entre reintentos (en milisegundos)

# Número de trabajadores para descargas paralelas
MAX_WORKERS = 36  # Ajusta según tu conexión y CPU
```

### Run the script

```
py YupooPhotoDownloader.py
```
