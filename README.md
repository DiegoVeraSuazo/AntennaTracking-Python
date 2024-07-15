# AntennaTracking-Python
Repositorio del Backend realizado en Python para realizar el control de la Antena, perteneciente al CEMCC, además de recoger los datos de SatNogs y hacer predicciones con estas. 

Proyecto relacionado con el proyecto AntennaTracking-React: [AntennaTracking-React](https://github.com/DiegoVeraSuazo/AntennaTracking-React)

Las bibliotecas utilizadas se encuentran en requirements.txt: 

```
    pip install -r requirements.txt
```

Para ejecutar este codigo hay que utilizar satellitePredictionAPI.py y rotorMovementAPI.py de forma separada

```
    py satellitePredictionAPI.py
    py satellitePredictionAPI.py
```

El codigo que ejecuta la API está dirigida a una IP estatica que se configura para comunicarse con el codigo de AntennaTracking-React.
Este puede modificarse, pero hay que tomar en cuenta en modificar la dirección en el codigo de React. 

Se puede configurar dentro de Ubuntu o Ubuntu Server un servicio que ejecute el codigo cada vez que se inicie y utilizar el comando de
journalctl para monitorear.