# File Transfer UDP

## Requisitos

- Python 3.12 o superior.
- Sistema Operativo GNU/Linux.

## Como correr parado sobre el directorio /tp1

-  Arranca el servidor en tu terminal así:

`python3 src/start-server.py -H 0.0.0.0 -p 9000 -s ./storage`


- Ahora, abre otra terminal y puedes correr el cliente como  download/upload así:

`python3 src/upload.py -H 127.0.0.1 -p 9000 -s ~/Documents/fileToUpload.txt -n prueba.txt -r stop_and_wait`

`python3 src/download.py -H 127.0.0.1 -p 9000 -d ~/Documents/fileToDownload.txt -n prueba.txt -r stop_and_wait`

`python3 src/upload.py -H 127.0.0.1 -p 9000 -s ~/Documents/fileToUpload.txt -n prueba.txt -r selective_repeat`

`python3 src/download.py -H 127.0.0.1 -p 9000 -d ~/Documents/fileToDownload.txt -n prueba.txt -r selective_repeat`


## Monitoreo de paquetes con Wireshark

Creamos un plugin de Wireshak que permite filtrar los paquetes de este proyecto, para abrir Wireshark con el plugin:

`wireshark -i lo -X  lua_script:plugin-wireshark/protocol.lua`

Luego en la barra de filtros de Wireshark tipea `protocologrupo5` y se deberian empezar a filtrar los paquetes. 

## MININET

- Limpiar cualquier estado previo de Mininet
`sudo mn -c`

- Ejecutar la topologia de mininet -> abre 2 terminales, la primera es el server y la segunda el client.
`sudo python3 topology-mininet/topology.py`

- Capturar con wireshark
`wireshark -i s1-eth1 -X lua_script:plugin-wireshark/protocol.lua`

- En la terminal server ejecutar
`python3 src/start-server.py -H 10.0.0.1 -p 9000 -s ./storage`

- En la terminal cliente ejecutar
`python3 src/upload.py -H 10.0.0.1 -p 9000 -s ~/Documents/fileToUpload.txt -n prueba.txt -r stop_and_wait`
`python3 src/download.py -H 10.0.0.1 -p 9000 -d ~/Documents/fileToDownload.txt -n prueba.txt -r stop_and_wait`

`python3 src/upload.py -H 10.0.0.1 -p 9000 -s ~/Documents/fileToUpload.txt -n prueba.txt -r selective_repeat`
`python3 src/download.py -H 10.0.0.1 -p 9000 -d ~/Documents/fileToDownload.txt -n prueba.txt -r selective_repeat`


### Verificación de Integridad
Al finalizar, verificar que el archivo no se haya corrompido comparando los hashes MD5 en ambas máquinas:

- En la terminal server
`md5sum ./server_storage/file.pdf`

- En la terminal client
`md5sum ~/Documents/file.pdf`

