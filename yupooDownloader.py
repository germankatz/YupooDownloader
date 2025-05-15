# coding=utf-8

from retrying import retry
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
import csv
import json
import sys
import re
import traceback
import concurrent.futures
import time
from pathlib import Path

# Configuración de reintentos para imágenes
MAX_RETRIES_FOR_IMAGES = 3  # Variable para controlar cuántas veces reintentar la descarga
RETRY_DELAY_MS = 1000  # Tiempo de espera entre reintentos (en milisegundos)

# Número de trabajadores para descargas paralelas 
MAX_WORKERS = 36  # Ajusta según tu conexión y CPU

# Forzar codificación UTF-8 para consola en Windows
if sys.platform == 'win32':
    # Intentar configurar la consola para UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # Código de página UTF-8
    except:
        pass

# Configurar sesión de requests global para reutilizar conexiones
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
})

# Cargar configuración
with open('details.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for state in data["yupoos"]:
    break

def getAlbumURLS():
    """
    Obtiene los URLs de todos los álbumes disponibles en un sitio Yupoo,
    explorando todas las páginas de colecciones disponibles.
    """
    try:
        # Preparar CSV de salida
        with open("albumURLs.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["LINKS"])

            # Base URL y estado
            url = state['yupoo_link']
            head, _, _ = url.partition('x.yupoo.com')
            base_url = head + "x.yupoo.com"
            print(f"Downloading photos from site: {base_url}")

            # Detectar colección (si aplica)
            collection_id = None
            if "collections" in url:
                m = re.search(r'/collections/(\d+)', url)
                if m:
                    collection_id = m.group(1)
                    print(f"Detectada colección con ID: {collection_id}")

            # Construir URL base de paginación
            if collection_id:
                pagination_base_url = f"{base_url}/collections/{collection_id}"
            else:
                pagination_base_url = f"{base_url}/albums"

            # Forzar page=1
            first_page_url = pagination_base_url + ("&page=1" if "?" in pagination_base_url else "?page=1")
            print(f"Obteniendo información de paginación desde: {first_page_url}")

            resp = session.get(first_page_url)
            if resp.status_code != 200:
                print(f"Error al acceder a la página: {resp.status_code}")
                return 0

            soup = BeautifulSoup(resp.text, "lxml")

            # Bloque simplificado para detectar total de páginas
            total_pages = 1
            span = soup.select_one("form.pagination__jumpwrap > span")
            if span:
                m = re.search(r'(\d+)', span.get_text(strip=True))
                if m:
                    total_pages = int(m.group(1))
                    print(f"Total de páginas detectadas: {total_pages}")

            # Función para procesar una página y extraer enlaces de álbum
            def process_page(page_num):
                page_url = f"{pagination_base_url}?page={page_num}"
                print(f"Procesando página {page_num}/{total_pages}: {page_url}")
                
                try:
                    pr = session.get(page_url)
                    if pr.status_code != 200:
                        print(f"  → Error en página {page_num}: {pr.status_code}")
                        return []
                    
                    page_soup = BeautifulSoup(pr.text, "lxml")
                    found_links = []
                    
                    for a in page_soup.find_all('a', class_='album__main'):
                        href = a.get('href')
                        if href:
                            found_links.append(href)
                    
                    print(f"  → {len(found_links)} álbum(es) encontrados esta página")
                    return found_links
                except Exception as e:
                    print(f"Error procesando página {page_num}: {e}")
                    return []

            # Procesamiento paralelo de páginas
            all_album_links = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, total_pages)) as executor:
                # Mapear las páginas a la función de procesamiento
                future_to_page = {executor.submit(process_page, page_num): page_num 
                                 for page_num in range(1, total_pages + 1)}
                
                # Recoger resultados a medida que se completan
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        links = future.result()
                        # Añadir solo enlaces únicos
                        for link in links:
                            if link not in all_album_links:
                                all_album_links.append(link)
                    except Exception as e:
                        print(f"Excepción procesando página {page_num}: {e}")

            # Guardar resultados y actualizar estado
            for link in all_album_links:
                writer.writerow([link])

            state['productCount'] = len(all_album_links)
            print(f"Total de álbumes encontrados: {state['productCount']}")
            print("albumURLs.csv generado en:", os.getcwd())
            return state['productCount']

    except Exception as e:
        print("Error en getAlbumURLS:", e)
        traceback.print_exc()
        return 0


@retry(stop_max_attempt_number=5, wait_fixed=2000)
def createHandler(X):
    try:
        # Usar un título simple y seguro para el archivo CSV
        csv_filename = str(X) + '.csv'
        with open(csv_filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=',')
            
            df = pd.read_csv('albumURLs.csv', sep=' ')

            # Verificar si el índice existe
            if X >= len(df['LINKS']):
                print(f"Error: No existe el índice {X} en el DataFrame. Total de filas: {len(df['LINKS'])}")
                writer.writerow([f"album_{X}"])  # Escribir un nombre genérico
                return False

            TEXT = (df['LINKS'][X])

            url = state['yupoo_link']
            text = url
            head, sep, tail = text.partition('x.yupoo.com')
            url = head + "x.yupoo.com" + TEXT

            print(f"Procesando URL: {url}")

            response = session.get(url, timeout=15)  # Timeout aumentado pero no infinito
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

            # Extraer imágenes con un enfoque más eficiente
            image_urls = []
            
            # Procesar imágenes landscape
            for x in soup.select('.image__landscape'):
                try:
                    if 'data-src' in x.attrs:
                        img_url = 'https:' + x['data-src']
                        image_urls.append(img_url)
                except Exception as e:
                    print(f"Error al procesar imagen landscape: {str(e)}")
            
            # Procesar imágenes portrait
            for x in soup.select('.image__portrait'):
                try:
                    if 'data-src' in x.attrs:
                        img_url = 'https:' + x['data-src']
                        image_urls.append(img_url)
                except Exception as e:
                    print(f"Error al procesar imagen portrait: {str(e)}")
            
            # Escribir todas las URLs de imágenes
            for img_url in image_urls:
                writer.writerow([img_url])
                
            print(f"Encontradas {len(image_urls)} imágenes para descargar")
            return True
            
    except Exception as e:
        print(f"Error en createHandler({X}): {str(e)}")
        print(f"Tipo de error: {type(e)}")
        traceback.print_exc()
        
        # Crear un archivo CSV válido para evitar errores en imageDownloader
        try:
            with open(str(X) + '.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=',')
                writer.writerow([f"album_{X}"])  # Cabecera con nombre simple
        except:
            pass
        return False

# Función específica para descargar una imagen con reintentos personalizados
def download_image_with_retry(url, folder, img_index):
    """Descarga una imagen con reintentos configurables"""
    retries_left = MAX_RETRIES_FOR_IMAGES
    while retries_left > 0:
        try:
            # Asegurarse de que no hay espacios en la ruta
            safe_folder = folder.replace(' ', '_')
            
            # Reutilizar la sesión global con configuración específica para yupoo
            session.headers.update({'referer': 'https://photo.yupoo.com/'})
            
            print(f"Descargando: {url} (intentos restantes: {retries_left})")
            res = session.get(url, timeout=20)
            
            if res.status_code != 200:
                raise Exception(f"Error HTTP: {res.status_code}")
            
            # Generar un nombre de archivo seguro basado en la última parte de la URL
            parts = url.split("/")
            if len(parts) >= 3:
                file_name = parts[-2]
            else:
                file_name = f"image_{img_index}"
            
            # Usar Path para manejar rutas de manera más segura
            output_dir = Path('./dump') / safe_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = output_dir / f"{file_name}.jpg"
            
            # Escribir contenido
            with open(file_path, 'wb') as f:
                f.write(res.content)
                
            print(f"Guardado como: {file_path}")
            return True
            
        except Exception as e:
            retries_left -= 1
            print(f"Error al descargar {url}: {str(e)}")
            if retries_left > 0:
                # Esperar antes de reintentar (tiempo en segundos)
                wait_time = RETRY_DELAY_MS / 1000
                print(f"Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                print(f"Se agotaron los reintentos para {url}")
                return False

def imageDownloader(x):
    try:
        def create_directory(directory):
            # Reemplazar espacios con guiones bajos para evitar problemas con las rutas
            safe_directory = directory.replace(' ', '_')
            
            # Crear directorio base dump si no existe
            dump_dir = Path('./dump')
            dump_dir.mkdir(exist_ok=True)
            
            album_dir = dump_dir / safe_directory
            album_dir.mkdir(exist_ok=True)
            print(f"Directorio listo: {album_dir}")
            
            return safe_directory
                
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
            
            # Leer URLs de imágenes
            df = pd.read_csv(file_path)
            
            # Función para procesar una imagen en paralelo
            def process_image(args):
                url, idx = args
                if isinstance(url, str) and url.startswith("http"):
                    return download_image_with_retry(url, safe_folder_name, idx)
                return False
            
            # Preparar lista de trabajos (URL, índice)
            image_jobs = []
            for col in df.columns:
                for idx, url in enumerate(df[col].tolist()):
                    if isinstance(url, str) and url.startswith("http"):
                        image_jobs.append((url, idx))
            
            # Descargar imágenes en paralelo
            successful_downloads = 0
            if image_jobs:
                print(f"Iniciando {len(image_jobs)} descargas en paralelo con {MAX_WORKERS} trabajadores")
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    # Realizar descargas en paralelo
                    results = list(executor.map(process_image, image_jobs))
                    successful_downloads = sum(1 for r in results if r)
                
                print(f"Descargadas {successful_downloads} de {len(image_jobs)} imágenes.")
                
                # Renombrar archivos secuencialmente
                if successful_downloads > 0:
                    try:
                        path = Path(f'./dump/{safe_folder_name}')
                        if path.exists():
                            files = list(path.glob('*.jpg'))
                            for index, file_path in enumerate(files):
                                new_name = path / f"{index}_big.jpg"
                                try:
                                    file_path.rename(new_name)
                                except Exception as e:
                                    print(f"Error al renombrar {file_path}: {e}")
                    except Exception as e:
                        print(f"Error al renombrar archivos: {str(e)}")
                    
            return successful_downloads > 0
        
        except Exception as e:
            print(f"Error al procesar el archivo CSV: {str(e)}")
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"Error en imageDownloader({x}): {str(e)}")
        traceback.print_exc()
        return False

# Función para procesar un álbum completo
def process_album(album_index):
    print(f"\n--- Procesando álbum {album_index+1} de {state['productCount']} ---")
    success = False
    
    try:
        if createHandler(album_index):
            if imageDownloader(album_index):
                success = True
        
        # Limpiar archivo CSV temporal
        try:
            csv_file = str(album_index) + '.csv'
            if os.path.exists(csv_file):
                os.remove(csv_file)
        except Exception as e:
            print(f"Error al eliminar archivo temporal {csv_file}: {e}")
            
        return success
    except Exception as e:
        print(f"Error procesando álbum {album_index}: {e}")
        traceback.print_exc()
        return False

def main():
    # Obtener URLs de álbumes
    album_count = getAlbumURLS()
    print(f"\nSe procesarán {album_count} álbumes en total")
    
    if album_count <= 0:
        print("No se encontraron álbumes para procesar.")
        return
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    # Procesar álbumes secuencialmente (podría ser paralelizado, pero con cuidado)
    for x in range(int(state['productCount'])):
        if process_album(x):
            success_count += 1
        else:
            fail_count += 1
    
    elapsed_time = time.time() - start_time
    
    print(f"\n=== Resumen ===")
    print(f"Total de álbumes procesados: {int(state['productCount'])}")
    print(f"Álbumes descargados correctamente: {success_count}")
    print(f"Álbumes con errores: {fail_count}")
    print(f"Tiempo total de ejecución: {elapsed_time:.2f} segundos")
    print(f"Promedio por álbum: {elapsed_time/max(album_count,1):.2f} segundos")

if __name__ == "__main__":
    main()