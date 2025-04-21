# coding=utf-8

from retrying import retry
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
import csv
import json
import sys

# Forzar codificación UTF-8 para consola en Windows
if sys.platform == 'win32':
    # Intentar configurar la consola para UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # Código de página UTF-8
    except:
        pass

# Cargar configuración
with open('details.json', 'r', encoding='utf-8')as f:
    data = json.load(f)
for state in data["yupoos"]:
    break

def getAlbumURLS():
    f = open("albumURLs.csv", "w", newline="", encoding="utf-8")
    writer = csv.writer(f, delimiter=' ', quoting=csv.QUOTE_MINIMAL)

    url = state['yupoo_link']
    text = url

    head, sep, tail = text.partition('x.yupoo.com')
    print("Downloading photos from site: " + head + "x.yupoo.com")

    response = requests.get(url)
    data = response.text
    soup = BeautifulSoup(data, features="lxml")
    writer.writerow(["LINKS"])

    row1 = []
    count=0
    for link in soup.findAll('a', class_='album__main'):
        count=count+1
        q = (link.get('href'))
        row1.append(q)
    print("Found " + str(count) + " albums...")

    for c in range(len(row1)):
        writer.writerow([row1[c]])

    f.close()
    print("File with album URLS located in: " + os.getcwd())
    print("Downloading images...")

getAlbumURLS()

@retry(stop_max_attempt_number=5)
def createHandler(X):
    try:
        # Usar un título simple y seguro para el archivo CSV
        csv_filename = str(X) + '.csv'
        with open(csv_filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=',')
            
            df = pd.read_csv('albumURLs.csv', sep=' ')
            TEXT = (df['LINKS'][X])

            url = state['yupoo_link']
            text = url
            head, sep, tail = text.partition('x.yupoo.com')
            url = head + "x.yupoo.com" + TEXT

            print(f"Procesando URL: {url}")

            response = requests.get(url, timeout=None)
            data = response.content
            soup = BeautifulSoup(data, 'lxml')
            
            # Extraer título del tag <title>
            title_tag = soup.find('title')
            if title_tag:
                full_title = title_tag.text.strip()
                album_name = full_title.split('|')[0].strip()
                print(f"Título encontrado: {album_name}")
                
                # Reemplazar caracteres no válidos en nombres de carpetas
                album_name = ''.join(c if c.isalnum() or c in '-_()' else '_' for c in album_name)
                # Asegurarse de que no haya espacios en el nombre
                album_name = album_name.replace(' ', '_')
                
                # Limitar longitud para evitar problemas con rutas muy largas
                if len(album_name) > 50:
                    album_name = album_name[:50]
                # Asegurar que no esté vacío
                if not album_name:
                    album_name = f"album_{X}"
            else:
                album_name = f"album_{X}"
                print("No se encontró título, usando nombre genérico")
            
            writer.writerow([album_name])
            print(f"Album: {album_name}")

            # El resto de tu código para extraer las imágenes...
            search = soup.select('.image__landscape')
            img_count = 0
            for x in search:
                try:
                    q = x['data-src']
                    writer.writerow(['https:' + q])
                    img_count += 1
                except Exception as e:
                    print(f"Error al procesar imagen: {str(e)}")
                
            search = soup.select('.image__portrait')
            for x in search:
                try:
                    q = x['data-src']
                    writer.writerow(['https:' + q])
                    img_count += 1
                except Exception as e:
                    print(f"Error al procesar imagen: {str(e)}")
                
            print(f"Encontradas {img_count} imágenes para descargar")
            return True
    except Exception as e:
        print(f"Error en createHandler({X}): {str(e)}")
        # Crear un archivo CSV válido para evitar errores en imageDownloader
        try:
            with open(str(X) + '.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=',')
                writer.writerow([f"album_{X}"])  # Cabecera con nombre simple
        except:
            pass
        return False
    
def imageDownloader(x):
    try:
        def create_directory(directory):
            # Reemplazar espacios con guiones bajos para evitar problemas con las rutas
            safe_directory = directory.replace(' ', '_')
            
            # Crear directorio base dump si no existe
            if not os.path.exists('dump'):
                os.makedirs('dump')
                
            if not os.path.exists('dump/' + safe_directory):
                try:
                    os.makedirs('dump/' + safe_directory)
                    print(f"Directorio creado: dump/{safe_directory}")
                except Exception as e:
                    print(f"Error al crear directorio: {str(e)}")
                    # Si falla, crear un directorio seguro
                    safe_directory = f"album_{x}"
                    if not os.path.exists('dump/' + safe_directory):
                        os.makedirs('dump/' + safe_directory)
            
            return safe_directory

        def download_save(url, folder):
            try:
                # Asegurarse de que no hay espacios en la ruta
                safe_folder = folder.replace(' ', '_')
                
                c = requests.Session()
                c.get('https://photo.yupoo.com/')
                c.headers.update({'referer': 'https://photo.yupoo.com/'})
                print(f"Descargando: {url}")
                res = c.get(url, timeout=None)
                
                # Generar un nombre de archivo seguro basado en la última parte de la URL
                parts = url.split("/")
                if len(parts) >= 3:
                    file_name = parts[-2]
                else:
                    file_name = f"image_{x}"
                
                file_path = f'./dump/{safe_folder}/{file_name}.jpg'
                print(f"Guardando en: {file_path}")
                
                with open(file_path, 'wb') as f:
                    f.write(res.content)
                print(f"Guardado como: {file_path}")
                return True
            except Exception as e:
                print(f"Error al descargar {url}: {str(e)}")
                return False
                
        file_path = str(x) + ".csv"
        print(f"Intentando leer archivo: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"El archivo {file_path} no existe")
            return False
        
        try:    
            # Leer el nombre del álbum de la primera fila del CSV
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                folder_name = next(reader)[0]  # Primera fila, primera columna
            
            print(f"Usando nombre de carpeta: {folder_name}")
            
            # Asegurar que el nombre es válido para una carpeta
            if not folder_name or folder_name.isspace():
                folder_name = f"album_{x}"
            
            # Crear la carpeta antes de descargar
            safe_folder_name = create_directory(folder_name)
                
            file = pd.read_csv(file_path)
            
            successful_downloads = 0
            for col in file.columns:
                print(f"Procesando columna: {col}")
                
                for url in file[col].tolist():
                    if str(url).startswith("http"):
                        if download_save(url, safe_folder_name):
                            successful_downloads += 1
            
            if successful_downloads > 0:
                print(f"Descargadas {successful_downloads} imágenes en total.")
                
                # Renombrar archivos
                try:
                    path = f'./dump/{safe_folder_name}'
                    if os.path.exists(path):
                        files = os.listdir(path)
                        for index, file in enumerate(files):
                            os.rename(os.path.join(path, file), os.path.join(path, ''.join([str(index), '_big.jpg'])))
                except Exception as e:
                    print(f"Error al renombrar archivos: {str(e)}")
                    
            return successful_downloads > 0
        except Exception as e:
            print(f"Error al procesar el archivo CSV: {str(e)}")
            return False

    except Exception as e:
        print(f"Error en imageDownloader({x}): {str(e)}")
        return False

# Ejecución principal
print("Iniciando descarga de álbumes...")
success_count = 0
fail_count = 0

for x in range(int(state['productCount'])):
    print(f"\n--- Procesando álbum {x+1} de {state['productCount']} ---")
    if createHandler(x):
        if imageDownloader(x):
            success_count += 1
        else:
            fail_count += 1
    else:
        fail_count += 1
    
    # Limpiar archivo CSV temporal
    try:
        csv_file = str(x) + '.csv'
        if os.path.exists(csv_file):
            os.remove(csv_file)
    except:
        pass

print(f"\n=== Resumen ===")
print(f"Total de álbumes procesados: {int(state['productCount'])}")
print(f"Álbumes descargados correctamente: {success_count}")
print(f"Álbumes con errores: {fail_count}")