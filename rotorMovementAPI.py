from datetime import datetime
import threading
import time
import rot2ProgInteractor

from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

rotConnectionStatus = False


# Loop que revisa la conexión a través del Serial.
while rotConnectionStatus is False: 
    try:
        rot = rot2ProgInteractor.ROT2Prog('/dev/ttyUSB0', baudrate=9600,timeout=10)
        estado_actual = rot.status()
        rotConnectionStatus = True
    except:
        print("No se pudo conectar con el rotor, intentando de nuevo")
        time.sleep(5)
        rotConnectionStatus = False

stop_event = threading.Event()
status_stop_event = threading.Event()

# Manejo conexión de clientes
@socketio.on('connect')
def handle_connection_status():
    """API call that handles an async connection as an example

    Returns:
    Status of the connection.
    """
    print('Cliente conectado')
    emit('connection_status', {'status': 'connected'})

def send_status():
    """Method that obtains the status of the rotor and sends it to the client every time there is a change.

    Returns:
    Status of the rotor - The position.
    """
    prevAzimuth = None
    prevElevation = None
    while not status_stop_event.is_set():
        estado_actual = rot.status()
        azimuth = estado_actual[0]
        elevation = estado_actual[1]
        if azimuth != prevAzimuth and elevation != prevElevation:
            print(azimuth, elevation)
            prevAzimuth = azimuth
            prevElevation = elevation
            socketio.emit('estado_actual', {'azimuth': azimuth, 'elevation': elevation})
            time.sleep(1)
        else:
            time.sleep(1)

@socketio.on('get_status')
def handle_get_status():
    """SocketIO Event that obtains the status of the rotor and sends it to the client.

    Returns:
    Status of the rotor.
    """
    status_stop_event.clear()
    send_status()

@socketio.on('stop_status')
def handle_stop_status():
    """SocketIO Event that stops the continuous status updates."""
    status_stop_event.set()
   
@app.route('/limits', methods=['GET'])
def getLimits():
    """API Call that obtains the limits of the rotor.

    Returns:
        JSON with the limits of the rotor.
    """
    limits_rot = rot.get_limits()
    return jsonify({'limite': limits_rot})

@app.route('/pulses', methods=['GET'])
def getPulsesPerDegree():
    """API Call that obtains the pulses per degree of the rotor.
    
    Returns:
    JSON with the pulses per degree of the rotor.
    """
    pulses_per_degree = rot.get_pulses_per_degree()
    return jsonify({'pulsos_por_grado': pulses_per_degree})

@app.route('/status', methods=['GET'])
def getStatus():
    """API Call that obtains the status of the rotor.

    Returns:
    JSON with the status of the rotor.
    """
    estado_actual = rot.status()
    azimuth = estado_actual[0]
    elevation = estado_actual[1]
    return jsonify({'azimuth': azimuth, 'elevation': elevation})

@app.route('/stop', methods=['GET'])
def getStop():
    """API call that stops the rotor.

    Returns:
    JSON with the status of the rotor.
    """
    rot.stop()
    return jsonify({'status': 'stop'})

@app.route('/moveToPosition', methods=['POST'])
def setPosition():
    """API call that sets the position of the rotor.
    
    Parameters:
    azimuth (float): Azimuth position to move using the rotor.
    elevation (float): Elevation position to move using the rotor.
    Returns:
    NONE
    """
    post_position_data = request.get_json()
    print(post_position_data)
    rot.set(post_position_data['data']['azimuth'], post_position_data['data']['elevation'])
    return jsonify({'azimuth': post_position_data['data']['azimuth'], 'elevation': post_position_data['data']['azimuth']})

@app.route('/moveLeft', methods=['GET'])
def moveRotorLeft():
    """API call that moves the rotor left.

    Returns:
    JSON with the status of the rotor.
    """
    rot.move_left_motor_1()
    return jsonify({'status': 'Moving Left'})

@app.route('/moveRight', methods=['GET'])
def moveRotorRight():
    """API call that moves the rotor right.

    Returns:
    JSON with the status of the rotor.
    """
    rot.move_right_motor_1()
    return jsonify({'status': 'Moving '})

@app.route('/moveUp', methods=['GET'])
def moveRotorUp():
    """API call that moves the rotor up.

    Returns:
    JSON with the status of the rotor.
    """
    rot.move_up_motor_2
    return jsonify({'status': 'Moving '})

@app.route('/moveDown', methods=['GET'])
def moveRotorDown():
    """API call that moves the rotor down.

    Returns:
    JSON with the status of the rotor.
    """
    rot.move_down_motor_2()
    return jsonify({'status': 'Moving '})

@app.route('/moveLeftUp', methods=['GET'])
def moveRotorLeftUp():
    """API call that moves the rotor left and up.
    
    Returns:
    JSON with the status of the rotor.
    """
    rot.move_left_up_motor()
    return jsonify({'status': 'Moving '})

@app.route('/moveRightUp', methods=['GET'])
def moveRotorRightUp():
    """API call that moves the rotor right and up.
    
    Returns:
    JSON with the status of the rotor.
    """
    rot.move_right_up_motor()
    return jsonify({'status': 'Moving '})

@app.route('/moveLeftDown', methods=['GET'])
def moveRotorLeftDown():
    """API call that moves the rotor left and down.
    
    Returns:
    JSON with the status of the rotor.
    """
    rot.move_left_down_motor()
    return jsonify({'status': 'Moving '})

@app.route('/moveRightDown', methods=['GET'])
def moveRotorRightDown():
    """API call that moves the rotor right and down.
    
    Returns:
    JSON with the status of the rotor.
    """
    rot.move_right_down_motor()
    return jsonify({'status': 'Moving '})

@app.route('/stopMovementRotor', methods=['GET'])
def stopMovementRotor():
    """API call that stops the rotor motor movement.
    
    Returns:
    JSON with the status of the rotor.
    """
    rot.stop_Movement_motor()
    return jsonify({'status': 'Stoping Movement of Rotor '})

@app.route('/setPowerMotor', methods=['POST'])
def setPowerMotor():
    """API call that sets the power of the motor in percetage.
    
    Returns:
    JSON with the status of the rotor.
    """
    powerInput = request.get_json()
    print(f'{powerInput}')
    rot.set_power_motor(powerInput)
    return jsonify({'status': 'Setting Power of Motor'})

@app.route('/cleanSettings', methods=['GET'])
def getCleanAllSettings():
    """API Call that clean all settings of the rotor.

    Returns:
    JSON with the status of the rotor.
    """
    rot.clean_all_settings()
    return jsonify({'status': 'Cleaning all settings'})

def track_prediction_task(prediction_data):
    """
    Method that moves the Antena to the position given in the prediction.
    
    Parameters(Given via request.get_json): 
    jsonFile: JSON file with the prediction. 
    Returns:
    None: Moves the Antena to the position given the time.
    """
    print('Empezando Tracking')
    rot.set(prediction_data[0]['az'], prediction_data[0]['el'])
    while prediction_data:
        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        for data in prediction_data[:]:  
            prediction_time = data['Tiempo_Cordenada']
            if current_time >= prediction_time:
                az = data['az']
                el = data['el']
                print(f"Ejecutando rot.set() con az={az} y el={el}")
                rot.set(az, el)

                # Eliminar el dato procesado
                prediction_data.remove(data)
            if stop_event.is_set():
                print('Se detuvo el seguimiento')
                return
        time.sleep(1)
    
    print('Se concluyo el seguimiento')

@app.route('/trackPrediction', methods=['POST'])
def trackPrediction():
    """
    API call that start the tracking process using the given prediction.
    
    Parameters(Given via request.get_json): 
    jsonFile: JSON file with the prediction. 
    Returns:
    JSON with the status of the rotor.
    """
    print('Empezando Tracking')
    post_prediction_sat_data = request.get_json()

    prediction_sat_data = post_prediction_sat_data.get('postDataPred')
    
    prediction_data = prediction_sat_data.get('Pasadas_predecidas')

    stop_event.clear()
    tracking_thread = threading.Thread(target=track_prediction_task, args=(prediction_data,))
    tracking_thread.start()

    return jsonify({'status': 'Tracking started'})

def track_celestial_object_task(prediction_cel_obj_data):
    """
    Method that moves the Antena to the position given in the prediction.
    
    Parameters(Given via request.get_json): 
    jsonFile: JSON file with the prediction. 
    Returns:
    None: Moves the Antena to the position given the time.
    """
    print('Empezando Tracking')
    print(prediction_cel_obj_data)
    while prediction_cel_obj_data:
        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        for data in prediction_cel_obj_data[:]:
            prediction_time = data['Tiempo_Cordenada']
            if current_time >= prediction_time:
                az = data['az']
                el = data['el']
                print(f"Ejecutando rot.set() con az={az} y el={el}")
                rot.set(az, el)
                prediction_cel_obj_data.remove(data)
            if stop_event.is_set():
                print('Se detuvo el seguimiento')
                return
        time.sleep(1)
    print('Se concluyo el seguimiento')

@app.route('/trackCelestialObject', methods=['POST'])
def trackCelestialObject():
    """
    API call that starts the tracking process using the given prediction.
    
    Parameters(Given via request.get_json): 
    jsonFile: JSON file with the prediction. 
    Returns:
    JSON with the status of the rotor.
    """
    global stop_event
    print('Empezando Tracking')
    post_prediction_sat_data = request.get_json()

    print(post_prediction_sat_data)

    prediction_cel_obj_data = post_prediction_sat_data.get('trackPredictionCelestial')

    print(prediction_cel_obj_data)

    stop_event.clear()
    tracking_thread = threading.Thread(target=track_celestial_object_task, args=(prediction_cel_obj_data,))
    tracking_thread.start()
    return jsonify({'status': 'Tracking started'})

@app.route('/stopTracking', methods=['get'])
def stopTracking():
    stop_event.set()
    return jsonify({'status': 'Tracking stopped'})

if __name__ == '__main__':
    http_server = WSGIServer(('192.168.1.18', 5019), app, handler_class=WebSocketHandler)
    http_server.serve_forever()
