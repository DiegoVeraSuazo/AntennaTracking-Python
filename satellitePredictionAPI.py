from apiSatNogsAllSatelliteNORADId import getSatellitesData
from satellitePrediction import prediccionPasadaSatelite, prediccionRutaSatelite, predictionCelestialBody
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app)
   
@app.route('/satelliteData', methods=['GET'])
def getSatelliteData():
    """ API Call that obtains he list of Satellites from the database of Satnogs through an API request.

        Returns:
        JSON file with a list of all the satellites that are alive
    """
    satelite_data = getSatellitesData()
    return jsonify({'Satellite Data': satelite_data})

@app.route('/pasadaSatelite', methods=['POST'])
def getPasadaSatelite():
    """ Computes the route and position of the choseen satellite, and the direction in azimuth and elevation that the antenna has to aim to obtain data from the satellite.

        Returns: JSON object with the following data:
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
                                                "elev": Elevación del satelite en una instancia de tiempo },
                                                }
    """
    post_data = request.get_json()
    print(post_data)
    satellite_id = post_data.get('satelliteNoradCatId')
    print(satellite_id)
    pasada_satelite = prediccionPasadaSatelite(satellite_id)
    print('Rocogida la ruta')
    return jsonify({'Pasada Satelite': pasada_satelite})

@app.route('/rutaSatelite', methods=['POST'])
def getRutaSatelite():
    """ Computes the route and position of the choseen satellite.

        Returns: JSON object with the following data:
                        "Satelite" : Nombre del Satellite,
                        "Ultima_Actulizacion" : Ultimo perido de tiempo en el que fue Actualizado de la tle,
                        "Pasadas_predecidas" : {
                                                "Tiempo_Cordenada": "Tiempo de la cordenada en una instancia de tiempo",
                                                "lat": Posicicón Latitud del satelite en una instancia de tiempo,
                                                "long": Posicicón Longitud del satelite en una instancia de tiempo,
                                                "elev": Elevación del satelite en una instancia de tiempo,
                                                }
    """
    post_data = request.get_json()
    print(post_data)
    satellite_id = post_data.get('satelliteNoradCatId')
    print(satellite_id)
    ruta_satelite = prediccionRutaSatelite(satellite_id)
    print('Rocogida la ruta')
    return jsonify({'Ruta Satelite': ruta_satelite})

@app.route('/pasadaCuerpoCeleste', methods=['POST'])
def getPasadaCuerpoCeleste():
    """ Computes the route and position of a choseen celestial object.

        Returns: JSON object with the following data:
                        "Cuerpo Celeste" : Nombre del Satellite,
                        "Pasadas_predecidas" : {
                                                "Tiempo_Cordenada": "Tiempo de la cordenada en una instancia de tiempo",
                                                "az": Posicicón Azimuth que debe estar la antena en una instancia de tiempo,
                                                "el": Posicicón Elevación que debe estar la antena en una instancia de tiempo,
                                                }
    """
    post_data = request.get_json()
    print(post_data)
    celestial_object = post_data.get('selectedObject')
    print(celestial_object)
    ruta_satelite = predictionCelestialBody(celestial_object)
    print('Rocogida la pasada del cuerpo escogida')
    return jsonify({'Pasada_Cuerpo': ruta_satelite})

# Manejar conexión de clientes
@socketio.on('connect')
def handle_connection_status():
    """API call that handles an async connection as an example

    Returns:
    JSON with the status of the rotor.
    """
    print('Cliente conectado')
    # Envía el estado actual al cliente cuando se conecta
    emit('Estado Conexion', 'conectado')

if __name__ == '__main__':
    # Production
    http_server = WSGIServer(('192.168.1.18', 5018), app)
    http_server.serve_forever()