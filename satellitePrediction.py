import json
import requests
import math
import ephem
from datetime import datetime, timedelta
import pytz

with open('config.json') as config_file:
    config = json.load(config_file)

api_key = config.get('api_key')
longitude = config.get('long')
latitude = config.get('lat')
elevation = config.get('elev')

if api_key is None:
    raise ValueError("No API key found in config file.")
# else:
#     print(f"API Key: {api_key}")
#     print(f"Longitude: {longitude}")
#     print(f"Latitude: {latitude}")
#     print(f"Elevation: {elevation}")

def prediccionPasadaSatelite(norad_cat_id, numero_de_pasadas = 1, computeCycle = 2):
    """Computes the route and position of the choseen satellite, and the direction in azimuth and elevation 
    that the antenna has to aim to obtain data from the satellite.

    Returns:
    JSON object with the following data:
                    "Satelite" : Nombre del Satellite,
                    "Ultima_Actulizacion" : Ultimo perido de tiempo en el que fue Actualizado de la tle,
                    "Numero_Pasada" : Numro de la pasada calculada, 
                    "Tiempo_Inicio" : Tiempo en la inicia la observacion del satellite, 
                    "Tiempo_Termino" : Tiempo en la que termina la observacion del satelite,
                    "Ciclo_computo" : Tiempo de cada posición,  
                    "Pasadas_predecidas" : {
                                            "Tiempo_Cordenada": "Tiempo de la cordenada en una instancia de tiempo",
                                            "az": Posicicón Azimuth que debe estar la antena en una instancia de tiempo,
                                            "el": Posicicón Elevación que debe estar la antena en una instancia de tiempo,
                                            "lat": Posicicón Latitud del satelite en una instancia de tiempo,
                                            "long": Posicicón Longitud del satelite en una instancia de tiempo,
                                            "elev": Elevación del satelite en una instancia de tiempo
                                            },
    """

    # URL
    url = f'https://db.satnogs.org/api/tle/?norad_cat_id={norad_cat_id}&tle_source=&sat_id='

    headers = {'Authorization': f'Token {api_key}','Content-Type': 'application/json',}

    response = requests.get(url, headers)

    if response.status_code == 200:
        print(f'Conexion con la API exitosa: {response.status_code}\nEmpezando con el computo de la orbita de:')
        telescope_data = response.json()
        json_data = telescope_data;

        tle_data = [{'tle0': item['tle0'], 'tle1': item['tle1'], 'tle2': item['tle2'], 'Updated': item['updated']} for item in json_data]
        
        if not tle_data:
            print(f'No hay datos del satelite disponibles')
            predictionPasada = {
                "Error" : "No existen datos del satelite",
            }
            return predictionPasada

        nombre_satellite = f"{tle_data[0]['tle0']}"
        if '0' in nombre_satellite: nombre_satellite = nombre_satellite.replace('0 ', '')
        print(nombre_satellite)

        nombre_satellite = nombre_satellite.replace("/","-")

        tle1 = f"{tle_data[0]['tle1']}"
        tle2 = f"{tle_data[0]['tle2']}"
        Updated = f"{tle_data[0]['Updated']}"
        Updated = Updated[:-5]

        ultimoActualizado = datetime.strptime(Updated, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Chile/Continental'))
        fechaUltimoActualizado= ultimoActualizado.strftime('%Y-%m-%dT%H:%M:%S')

        now_time = datetime.now(pytz.timezone('Chile/Continental'))

        time_difference = (now_time - ultimoActualizado)

        # Condición que ocurre si la TLE esta muy desactualizada, puede significar un error con el satelite.
        if time_difference > timedelta(days=3):
            predictionData = {
                "Satelite" : nombre_satellite,
                "Satelite_Norad_Cat_ID" : norad_cat_id,
                "Ultima_Actulizacion" : fechaUltimoActualizado,
                "Predicción" : {
                    "Error" : "La tle no se encuentra actualizada, por lo que no se puede realizar la predicción."
                },
            }
            
            return predictionData

        satellite = ephem.readtle(nombre_satellite, tle1, tle2)

        obs = ephem.Observer()
        obs.lat = latitude
        obs.long = longitude
        obs.elev = elevation

        tempPredictionPasada = []
        predictionData = []
        tempPred = []

        # seleccion = click.prompt('Iniciando Computo.\nIngrese el los segundos en ciclo que quiere que se computen para la predicción',type=float)
        # computeCycle = seleccion

        # Este *for* realiza un predicción para los futuros pasos del satelite, si el range es 1 hara para la primera pasada, 
        # si es 2 para la primera y segunda pasada y así sucesivamente.
        for p in range(numero_de_pasadas):
            
            try:
                tr, azr, tt, altt, ts, azs = obs.next_pass(satellite)
        
                if tr is None or ts is None:
                    predictionData = {
                        "Error" : "Error de Computo, objeto nunca pasa por el area"
                    }
                    tempPredictionPasada.append(predictionData)

                localTimeStart = ephem.localtime(tr).strftime('%Y-%m-%dT%H:%M:%S')
                localTimeEnd = ephem.localtime(ts).strftime('%Y-%m-%dT%H:%M:%S')

                while tr < ts:
                    obs.date = tr
                    satellite.compute(obs)

                    pasadas_predecidas = {
                        "Tiempo_Cordenada" : ephem.localtime(tr).strftime('%Y-%m-%dT%H:%M:%S'),
                        "az" : round(math.degrees(satellite.az), 1),
                        "el" : round(math.degrees(satellite.alt), 1),
                        "lat" : round(math.degrees(satellite.sublat), 6),
                        "long" : round(math.degrees(satellite.sublong), 6),
                        "elev" : round(satellite.elevation, 2),
                    }

                    tempPred.append(pasadas_predecidas)
                    
                    # Tiempo para el siguiente calculo
                    tr = ephem.Date(tr + computeCycle * ephem.second)
                
                print(f'Registradas {len(tempPred)} inputs para cada {computeCycle} segundos.')

                predictionData = {
                    "Numero_Pasada" : p+1, 
                    "Tiempo_Inicio" : localTimeStart, 
                    "Tiempo_Termino" : localTimeEnd,
                    "Ciclo_computo" : computeCycle,  
                    "Pasadas_predecidas" : tempPred,
                }

                tempPredictionPasada.append(predictionData)

            except ValueError:
                print(f'Error en el computo: {ValueError}')
                
                predictionData = {
                    "Error" : "Error de Computo, objeto nunca pasa por el area"
                }
                tempPredictionPasada.append(predictionData)

        predictionPasada = {
            "Satelite" : nombre_satellite,
            "Satelite_Norad_Cat_ID" : norad_cat_id,
            "Ultima_Actulizacion" : fechaUltimoActualizado,
            "Predicción" : tempPredictionPasada
            }

        """Escribe los datos a un archivo"""
        # dir = os.path.dirname(__file__)
        # newDir = os.path.join(dir, 'resources', nombre_tle)
        # os.makedirs(os.path.dirname(newDir), exist_ok=True)

        # with open(newDir, 'w', encoding="utf-8") as file:
        #     json.dump(predictionPasada, file, ensure_ascii=False, indent=4)
        # print(f"Datos guardados en {newDir}")
        
        return predictionPasada

    else:
        print(f'Error en la solicitud: {response.status_code}')

def prediccionRutaSatelite(norad_cat_id):
    """Computes the route and position of the choseen satellite.

    Returns:
    JSON object with the following data:
                    "Satelite" : Nombre del Satellite,
                    "Ultima_Actulizacion" : Ultimo perido de tiempo en el que fue Actualizado de la tle,
                    "Ruta_predecida" : {
                                            "Tiempo_Cordenada": "Tiempo de la cordenada en una instancia de tiempo",
                                            "lat": Posicicón Latitud del satelite en una instancia de tiempo,
                                            "long": Posicicón Longitud del satelite en una instancia de tiempo,
                                            "elev": Elevación del satelite en una instancia de tiempo
                                            },
    """

    # URL
    url = f'https://db.satnogs.org/api/tle/?norad_cat_id={norad_cat_id}&tle_source=&sat_id='

    headers = {'Authorization': f'Token {api_key}','Content-Type': 'application/json',}

    response = requests.get(url, headers)

    if response.status_code == 200:
        print(f'Conexion con la API exitosa: {response.status_code}\nEmpezando con el computo de la orbita de:')
        telescope_data = response.json()

        json_data = telescope_data;

        tle_data = [{'tle0': item['tle0'], 'tle1': item['tle1'], 'tle2': item['tle2'], 'Updated': item['updated']} for item in json_data]
        
        if not tle_data:
            print(f'No hay datos del satelite disponibles')
            predictionPasada = {
                "Error" : "No existen datos del satelite",
            }
            return predictionPasada

        nombre_satellite = f"{tle_data[0]['tle0']}"
        if '0' in nombre_satellite: nombre_satellite = nombre_satellite.replace('0 ', '')
        print(nombre_satellite)

        nombre_satellite = nombre_satellite.replace("/","-")

        tle1 = f"{tle_data[0]['tle1']}"
        tle2 = f"{tle_data[0]['tle2']}"
        Updated = f"{tle_data[0]['Updated']}"
        Updated = Updated[:-5]

        ultimoActualizado = datetime.strptime(Updated, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Chile/Continental'))
        fechaUltimoActualizado= ultimoActualizado.strftime('%Y-%m-%dT%H:%M:%S')

        now_time = datetime.now(pytz.timezone('Chile/Continental'))

        time_difference = (now_time - ultimoActualizado)

        # Condición que ocurre si la TLE esta muy desactualizada, puede significar un error con el satelite.
        if time_difference > timedelta(days=3):
            predictionData = {
                "Satelite" : nombre_satellite,
                "Satelite_Norad_Cat_ID" : norad_cat_id,
                "Ultima_Actulizacion" : fechaUltimoActualizado,
                "Ruta_predecida" : {
                    "Error" : "La tle no se encuentra actualizada, por lo que no se puede realizar la predicción."
                },
            }
            
            """Escribe los datos a un archivo"""
            # dir = os.path.dirname(__file__)
            # newDir = os.path.join(dir, 'resources', nombre_tle)
            # os.makedirs(os.path.dirname(newDir), exist_ok=True)

            # with open(newDir, 'w', encoding="utf-8") as file:
            #     json.dump(predictionData, file, ensure_ascii=False, indent=4)
            # print(f"Datos guardados en {newDir}")
            
            return predictionData

        
        satellite = ephem.readtle(nombre_satellite, tle1, tle2)

        start_time = now_time - timedelta(minutes=1)
        end_time = now_time + timedelta(hours=5)
        step_seconds = 1

        current_time = start_time

        obs = ephem.Observer()
        obs.lat = latitude
        obs.long = longitude
        obs.elev = elevation

        tempPred = []
        predictionData = []

        """Este *while* realiza un predicción de la ruta por la que pasara el satelite entre *start_time* y *end_time*, con step_seconds como
            paso de tiempo entre cada predicción.
        """
        while current_time <= end_time:

            try:
                obs.date = current_time
                satellite.compute(obs)

                posición_predecida = {
                    "Tiempo_Cordenada" : current_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    "lat" : round(math.degrees(satellite.sublat), 6),
                    "long" : round(math.degrees(satellite.sublong), 6),
                    "elev" : round(satellite.elevation, 2),
                }

                tempPred.append(posición_predecida)

                current_time += timedelta(seconds=step_seconds)
            
            except ValueError:
                print(f'Error en el computo: {ValueError}')
                posición_predecida = {
                    "Error" : ValueError
                }

        predictionData = {
            "Satelite" : nombre_satellite,
            "Satelite_Norad_Cat_ID" : norad_cat_id,
            "Ultima_Actulizacion" : fechaUltimoActualizado,
            "Ruta_predecida" : tempPred,
            }
            
        """Escribe los datos a un archivo"""
        # dir = os.path.dirname(__file__)
        # newDir = os.path.join(dir, 'resources', nombre_tle)
        # os.makedirs(os.path.dirname(newDir), exist_ok=True)

        # with open(newDir, 'w', encoding="utf-8") as file:
        #     json.dump(predictionData, file, ensure_ascii=False, indent=4)
        # print(f"Datos guardados en {newDir}")
        
        return predictionData

    else:
        print(f'Error en la solicitud: {response.status_code}')

def predictionCelestialBody(CelestialBodyOption):
    """Computes the route and position of the choseen satellite.
    
    Returns:
    JSON object with the following data:
        "Cuerpo Celeste": El nombre del cuerpo celeste a predecir,
        "Pasadas_predecidas": [{
            "Tiempo_Cordenada": "Tiempo de la cordenada en una instancia de tiempo",
            "az": Posicicón Azimuth que debe estar la antena en una instancia de tiempo,
            "el": Posicicón Elevación que debe estar la antena en una instancia de tiempo,
    """
    # Configuración de la ubicación
    observador = ephem.Observer()
    observador.lat = latitude
    observador.long = longitude
    observador.elev = elevation

    # Lista de cuerpos celestes disponibles
    cuerpos_celestes = {
        "Luna": ephem.Moon(),
        "Sol": ephem.Sun(),
        "Mercurio": ephem.Mercury(),
        "Venus": ephem.Venus(),
        "Marte": ephem.Mars(),
        "Júpiter": ephem.Jupiter(),
        "Saturno": ephem.Saturn(),
        "Urano": ephem.Uranus(),
        "Neptuno": ephem.Neptune(),
        "Plutón": ephem.Pluto()
    }

    opcion = CelestialBodyOption - 1
    nombre_cuerpo_celeste = list(cuerpos_celestes.keys())[opcion]
    
    print(f"Seleccionado el cuerpo celeste {nombre_cuerpo_celeste}")
    
    cuerpo_celeste = cuerpos_celestes[nombre_cuerpo_celeste]

    # Rango de fechas y horas
    start_time = datetime.now(pytz.timezone('Chile/Continental'))
    end_time = start_time + timedelta(hours=6)
    step_seconds = 1

    current_time = start_time

    # Crear listas para almacenar los resultados
    tempPred = []
    predictionData = []

    # Variables para almacenar los valores previos de azimuth y elevación
    prev_az = None
    prev_el = None

    # Calcular las posiciones del cuerpo celeste
    while current_time < end_time:
        observador.date = current_time
        cuerpo_celeste.compute(observador)

        az = round(math.degrees(cuerpo_celeste.az), 1)
        el = round(math.degrees(cuerpo_celeste.alt), 1)

        # Comprobar si hay un cambio en el azimuth o la elevación
        if el >= 0.0:
            if az != prev_az or el != prev_el:
                posición_predecida = {
                    "Tiempo_Cordenada": current_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    "az": az,
                    "el": el,
                }
                tempPred.append(posición_predecida)
                prev_az = az
                prev_el = el
            
        current_time += timedelta(seconds=step_seconds)

    predictionData = {
        "Cuerpo Celeste": nombre_cuerpo_celeste,
        "Pasadas_predecidas": tempPred
        }

    """Escribe los datos a un archivo"""
    # dir = os.path.dirname(__file__)
    # newDir = os.path.join(dir, 'resources', f'{nombre_cuerpo_celeste}_pred.json')
    # os.makedirs(os.path.dirname(newDir), exist_ok=True)

    # with open(newDir, 'w', encoding="utf-8") as file:
    #     json.dump(predictionData, file, ensure_ascii=False, indent=4)
    # print(f"Datos guardados en {newDir}")

    return predictionData
                
if __name__ == '__main__':
    # prediccionRutaSatelite(24278)
    # prediccionPasadaSatelite(24278, 1, 1)
    predictionCelestialBody(2)