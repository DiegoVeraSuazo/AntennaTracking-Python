"""This is a python interface to the Alfa ROT2Prog Controller.
"""
import logging
import serial
import time
from threading import Lock, Thread

class ReadTimeout(Exception):

	"""A serial read timed out.
	"""
	
	pass

class PacketError(Exception):

	"""A received packet contained an error.
	"""
	
	pass

class ROT2Prog:

	"""Sends commands and receives responses from the ROT2Prog controller.
	"""
	_log = logging.getLogger(__name__)

	_ser = None

	_pulses_per_degree_lock = Lock()
	_pulses_per_degree = 1

	_limits_lock = Lock()

	def __init__(self, port, baudrate = 9600, timeout = 5):
		"""Creates object and opens serial connection.
		
		Args:
		    port (str): Name of serial port to connect to.
		    baudrate (int, optional): measure of the number of changes to the signal (per second) from the controller.
		    timeout (int, optional): Maximum response time from the controller.
		"""
		# open serial port
		self._ser = serial.Serial(
			port = port,
			baudrate = baudrate,
			bytesize = 8,
			parity = 'N',
			stopbits = 1,
			timeout = timeout,
			inter_byte_timeout = 0.1) # inter_byte_timeout allows continued operation after a bad packet

		self._log.debug('\'' + str(self._ser.name) + '\' opened with ' + str(timeout) + "s timeout")

		# get resolution from controller
		self.status()
		# set the limits to default values
		self.set_limits()

	def _send_command(self, command_packet):
		"""Sends a command packet.
		
		Args:
		    command_packet (list of int): Command packet queued.
		"""
		self._ser.write(bytearray(command_packet))
		self._log.debug('Command packet sent: ' + str(list(map(hex, list(command_packet)))))
		
	def _recv_response(self):
		"""Receives a response packet.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		
		Raises:
		    PacketError: The response packet is incomplete or contains bad values.
		    ReadTimeout: The controller was unresponsive.
		"""
		# read with timeout
		response_packet = list(self._ser.read(12))

		# attempt to receive 12 bytes, the length of response packet
		self._log.debug('Response packet received: ' + str(list(map(hex, list(response_packet)))))
		if len(response_packet) != 12:
			if len(response_packet) == 0:
				raise ReadTimeout('Response timed out')
			else:
				raise PacketError('Incomplete response packet')
		else:
			# convert from byte values
			az = (response_packet[1] * 100) + (response_packet[2] * 10) + response_packet[3] + (response_packet[4] / 10.0) - 360.0
			el = (response_packet[6] * 100) + (response_packet[7] * 10) + response_packet[8] + (response_packet[9] / 10.0) - 360.0
			PH = response_packet[5]
			PV = response_packet[10]

			az = float(round(az, 1))
			el = float(round(el, 1))

			# check resolution value
			valid_pulses_per_degree = [1, 2, 4, 10]
			if PH != PV or PH not in valid_pulses_per_degree:
				raise PacketError('Invalid controller resolution received (PH = ' + str(PH) + ', PV = ' + str(PV) + ')')
			else:
				with self._pulses_per_degree_lock:
					self._pulses_per_degree = PH

			self._log.debug('Received response')
			self._log.debug('-> Azimuth:   ' + str(az) + '°')
			self._log.debug('-> Elevation: ' + str(el) + '°')
			self._log.debug('-> PH:        ' + str(PH))
			self._log.debug('-> PV:        ' + str(PV))

			return (az, el)

# Methods that interact with the controller.

	def stop(self):
		"""Sends a stop command to stop the rotator in the current position.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Stop command queued')

		cmd = [0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0f, 0x20]
		self._send_command(cmd)
		return self._recv_response()

	def status(self):
		"""Sends a status command to determine the current position of the rotator.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Status command queued')

		cmd = [0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1f, 0x20]
		self._send_command(cmd)
		return self._recv_response()

	def set(self, az, el):
		"""Sends a set command to turn the rotator to the specified position.
		
		Args:
		    az (float): Azimuth angle to turn rotator to.
		    el (float): Elevation angle to turn rotator to.
		
		Raises:
		    ValueError: The inputs cannot be sent to the controller.
		"""
		# make sure the inputs are within limits
		az = float(az)
		el = float(el)

		with self._limits_lock:
			if az > self._max_az or az < self._min_az:
				raise ValueError('Azimuth of ' + str(az) + '° is out of range [' + str(self._min_az) + '°, ' + str(self._max_az) + '°]')
			if el > self._max_el or el < self._min_el:
				raise ValueError('Elevation of ' + str(el) + '° is out of range [' + str(self._min_el) + '°, ' + str(self._max_el) + '°]')

		self._log.debug('Set command queued')
		self._log.debug('-> Azimuth:   ' + str(az) + '°')
		self._log.debug('-> Elevation: ' + str(el) + '°')

		# encode with resolution
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree

		H = int(resolution * (float(az) + 360))
		V = int(resolution * (float(el) + 360))

		# convert to ascii characters
		H = "0000" + str(H)
		V = "0000" + str(V)

		# build command
		cmd = [
			0x57,
			int(H[-4]) + 0x30, int(H[-3]) + 0x30, int(H[-2]) + 0x30, int(H[-1]) + 0x30,
			resolution,
			int(V[-4]) + 0x30, int(V[-3]) + 0x30, int(V[-2]) + 0x30, int(V[-1]) + 0x30,
			resolution,
			0x2f,
			0x20]

		self._send_command(cmd)

	def get_limits(self):
		"""Returns the minimum and maximum limits for azimuth and elevation.
		
		Returns:
		    min_az (float), max_az (float), min_el (float), max_el (float): Tuple of minimum and maximum azimuth and elevation.
		"""
		self._log.debug('Get Limits Command queued')
		with self._limits_lock:
			return (self._min_az, self._max_az, self._min_el, self._max_el)

	def set_limits(self, min_az = -180, max_az = 540, min_el = -15, max_el = 195):
		"""Sets the minimum and maximum limits for azimuth and elevation.
		
		Args:
		    min_az (int, optional): Minimum azimuth. Defaults to -180.
		    max_az (int, optional): Maximum azimuth. Defaults to 540.
		    min_el (int, optional): Minimum elevation. Defaults to -21.
		    max_el (int, optional): Maximum elevation. Defaults to 180.
		"""
		self._log.debug('Set Limits Command queued')
		with self._limits_lock:
			self._min_az = min_az
			self._max_az = max_az
			self._min_el = min_el
			self._max_el = max_el

	def get_pulses_per_degree(self):
		"""Returns the number of pulses per degree.
		
		Returns:
		    int: Pulses per degree defining the resolution of the controller.
		"""
		self._log.debug('Get Pulses per Degree Command queued')
		with self._pulses_per_degree_lock:
			return self._pulses_per_degree
		    
	def move_left_motor_1(self):
		"""Sends a motor command to move the rotator to the left.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move left command queued')
		
		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x01, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def move_right_motor_1(self):
		"""Sends a motor command to move the rotator to the right.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move right command queued')
		
		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x02, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def move_up_motor_2(self):
		"""Sends a motor command to move the rotator up.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move up command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x04, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def move_down_motor_2(self):
		"""Sends a motor command to move the rotator down.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move down command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x08, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def move_left_up_motor(self):
		"""Sends a motor command to move the rotator left+up.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move left+up command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x05, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()

	def move_right_up_motor(self):
		"""Sends a motor command to move the rotator right+up.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move right+up command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x06, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def move_left_down_motor(self):
		"""Sends a motor command to move the rotator left+down.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move left+down command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x0A, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()

	def move_right_down_motor(self):
		"""Sends a motor command to move the rotator right+down.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Move right+down command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x09, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()

	def stop_movement_motor(self):
		"""Sends a motor command to stop the move.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Stop movement command queued')

		# encode with resolution, it doesn't matter but self._recv_response() needs it to process.
		with self._pulses_per_degree_lock:
			resolution = self._pulses_per_degree
		cmd = [0x57, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x00, 0x00, 0x00, 0x00, resolution, 
		 0x14, 0x20]
		self._send_command(cmd)
		return self._recv_response()
	
	def set_power_motor(self, power_motor_1, power_motor_2):
		"""Sends a command to set the power of the motor to the specified percentage. 
		
		Returns:
			
		"""
		self._log.debug('Set Power command queued')
		
		limitPowerMotor1 = max(0, min(100, power_motor_1))
		limitPowerMotor2 = max(0, min(100, power_motor_2))
		hexStrPowMot1 = hex(limitPowerMotor1)[2:]
		hexStrPowMot2 = hex(limitPowerMotor2)[2:]
		powerMotor1 = hexStrPowMot1.zfill(2)
		powerMotor2 = hexStrPowMot2.zfill(2)

		self._log.debug(f'Motor 1: {power_motor_1}, Power 2: {power_motor_2}')

		cmd = [0x57, 
		 0x00, 0x00, 0x00, 0x00, int(powerMotor1) + 0x00, 
		 0x00, 0x00, 0x00, 0x00, int(powerMotor2) + 0x00, 
		 0xF7, 0x20]
		self._send_command(cmd)
		return f"{cmd} Packet received, Setting Power to: Motor 1: {powerMotor1}, Motor 2: {powerMotor2}"
	
	def clean_all_settings(self):
		"""Sends a command that clean all settings.
		
		Returns:
		    az (float), el (float): Tuple of current azimuth and elevation.
		"""
		self._log.debug('Clean all settings command queued')

		cmd = [0x57, 
		 0x00, 0x00, 0x00, 0x00, 0x00, 
		 0x00, 0x00, 0x00, 0x00, 0x00, 
		 0xF8, 0x20]
		self._send_command(cmd)
		return f"{cmd} Packet received: All settings cleaned"