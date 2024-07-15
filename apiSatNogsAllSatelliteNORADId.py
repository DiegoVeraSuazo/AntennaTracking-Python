import requests
import json
import os
from datetime import datetime, timedelta
import pytz
import ephem
from concurrent.futures import ThreadPoolExecutor, as_completed

def computoSatelite(tle_data):
    """Computes the time of rising and setting of the Satellite.

    Returns:
    The time of rising and setting of the satellite and the last updated time of the TLE data.
    """
    tle_data_parsed = [{'tle0': item['tle0'], 'tle1': item['tle1'], 'tle2': item['tle2'], 'Updated': item['updated']} for item in tle_data]
    
    if not tle_data_parsed:
        Tiempo_Inicio = "No existen datos TLE del satelite, imposible hacer computo de la orbita"
        Tiempo_Fin = "No existen datos TLE del satelite, imposible hacer computo de la orbita"
        fechaUltimoActualizado = "No existen datos TLE del satelite, imposible hacer computo de la orbita"
        return Tiempo_Inicio, Tiempo_Fin, fechaUltimoActualizado

    nombre_satellite = f"{tle_data_parsed[0]['tle0']}"
    if '0' in nombre_satellite: nombre_satellite = nombre_satellite.replace('0 ', '')
    nombre_satellite = nombre_satellite.replace("/", "-")
    tle1 = f"{tle_data_parsed[0]['tle1']}"
    tle2 = f"{tle_data_parsed[0]['tle2']}"
    Updated = f"{tle_data_parsed[0]['Updated']}"
    Updated = Updated[:-5]
    
    ultimoActualizado = datetime.strptime(Updated, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Chile/Continental'))
    now_time = datetime.now(pytz.timezone('Chile/Continental'))
    time_difference = (now_time - ultimoActualizado)
    fechaUltimoActualizado= ultimoActualizado.strftime('%Y-%m-%dT%H:%M:%S')

    if time_difference > timedelta(days=3):
        Tiempo_Inicio = "La TLE esta muy desactualizada para realizar un calculo conciso de la orbita del satelite"
        Tiempo_Fin = "La TLE esta muy desactualizada para realizar un calculo conciso de la orbita del satelite"
        return Tiempo_Inicio, Tiempo_Fin, fechaUltimoActualizado

    satellite = ephem.readtle(nombre_satellite, tle1, tle2)
    obs = ephem.Observer()
    obs.lat = '-38.7487032'
    obs.long = '-72.6174925'
    obs.elev = 107
        
    try:
        tr, azr, tt, altt, ts, azs = obs.next_pass(satellite)
        
        if tr is None or ts is None:
            Tiempo_Inicio = "Error de Computo, objeto nunca pasa por el area"
            Tiempo_Fin = "Error de Computo, objeto nunca pasa por el area"
            fechaUltimoActualizado = "Error de Computo, objeto nunca pasa por el area"
            return Tiempo_Inicio, Tiempo_Fin, fechaUltimoActualizado
        
        Tiempo_Inicio = ephem.localtime(tr).strftime('%Y-%m-%dT%H:%M:%S')
        Tiempo_Fin = ephem.localtime(ts).strftime('%Y-%m-%dT%H:%M:%S')
        return Tiempo_Inicio, Tiempo_Fin, fechaUltimoActualizado
    
    except ValueError:
        Tiempo_Inicio = "Error de Computo, objeto nunca pasa por el area"
        Tiempo_Fin = "Error de Computo, objeto nunca pasa por el area"
        fechaUltimoActualizado = "Error de Computo, objeto nunca pasa por el area"
        return Tiempo_Inicio, Tiempo_Fin, fechaUltimoActualizado

def getTLESatelite():
    """Gets the TLE data from the SatNogs Database using their API

    Returns:
    The TLE data of all the available satellites in the database of SatNogs.
    """
    api_key = '7ccf8dd1b0060eaf8f11a63e6505fdf2ab431494'
    url = 'https://db.satnogs.org/api/tle/?norad_cat_id=&tle_source=&sat_id='
    headers = {'Authorization': f'Token {api_key}','Content-Type': 'application/json',}
    response = requests.get(url, headers)
    if response.status_code == 200:
        print(f'Conexion con la API exitosa: {response.status_code}\nObteniendo el listado de los TLE de los satelites')
        tle_data = response.json()
        if not tle_data:
            tle_data = "No hay datos de transmisores registrados en SatNogs"
        return tle_data
    else:
        print(f'Error en la solicitud: {response.status_code}')
        return None

def getTransmitterSatellite():
    """Gets the transmitter data from the SatNogs Database using their API

    Returns:
    The transmitter data of all the available satellites in the database of SatNogs.
    """
    api_key = '7ccf8dd1b0060eaf8f11a63e6505fdf2ab431494'
    url = f'https://db.satnogs.org/api/transmitters/?uuid=&mode=&uplink_mode=&type=&satellite__norad_cat_id=&alive=&status=&service=&sat_id='
    headers = {'Authorization': f'Token {api_key}','Content-Type': 'application/json',}
    response = requests.get(url, headers)
    if response.status_code == 200:
        print(f'Conexion con la API exitosa: {response.status_code}\nObteniendo el listado de los tranmisores de disponibles de los satelites')
        transmitter_data = response.json()
        if not transmitter_data:
            transmitter_data = "No hay datos de transmisores registrados en SatNogs"
        return transmitter_data
    else:
        print(f'Error en la solicitud: {response.status_code}')
        return None

def getSatellitesData():
    """Gets a list of all satellite that are alive from the SatNogs Database using their API, 
    and transforms the data to add aditional data.

    Returns:
    The data of all the available satellites in the database of SatNogs.
    """
    api_key = '7ccf8dd1b0060eaf8f11a63e6505fdf2ab431494'
    url = 'https://db.satnogs.org/api/satellites/?norad_cat_id=&status=alive&in_orbit=true&sat_id='
    headers = {'Authorization': f'Token {api_key}','Content-Type': 'application/json',}
    response = requests.get(url, headers)
    if response.status_code == 200:
        print(f'Conexion con la API exitosa: {response.status_code}\nObteniendo el listado de los satelites vivos')
        satellite_data = response.json()
        transmitters = getTransmitterSatellite()
        tle_data_all = getTLESatelite()

        def process_satellite(satellite):
            norad_cat_id = satellite["norad_cat_id"]

            matching_tle_data = [t for t in tle_data_all if t["norad_cat_id"] == norad_cat_id]
            if matching_tle_data:
                return satellite, computoSatelite(matching_tle_data)
            else:
                return satellite, None

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(process_satellite, sat): sat for sat in satellite_data}
            for future in as_completed(futures):
                sat, result = future.result()
                if result and isinstance(result, tuple):
                    tiempo_inicio, tiempo_fin, ultimo_actualizado = result
                    sat["Tiempo_Inicio"] = tiempo_inicio
                    sat["Tiempo_Fin"] = tiempo_fin
                    sat["Ultimo_actualizado"] = ultimo_actualizado

                norad_cat_id = sat["norad_cat_id"]
                matching_transmitters = [t for t in transmitters if t["norad_cat_id"] == norad_cat_id]
                sat["transmitters"] = matching_transmitters
            

        satelliteInOrbit_available_file = "SatelliteDataSatNogsAliveInOrbit.json"
        dir = os.path.dirname(__file__)
        newDir = os.path.join(dir, 'resources', satelliteInOrbit_available_file)
        os.makedirs(os.path.dirname(newDir), exist_ok=True)
        with open(newDir, 'w', encoding="utf-8") as file:
            json.dump(satellite_data, file, ensure_ascii=False, indent=4)
        print(f'Se han guardado los satelites disponibles en SatNogs en la direccion:')
        print(f'{newDir}')
        return satellite_data
    else:
        print(f'Error en la solicitud: {response.status_code}')
        return None

if __name__ == '__main__':
    getSatellitesData()
