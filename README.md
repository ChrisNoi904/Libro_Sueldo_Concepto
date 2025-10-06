# Libro_Sueldo_Concepto
Libro sueldo conversor de conceptos 
1- Emito desde ONVIO Relacion_de_Conceptos (TXT)

2-Emito desde ONVIO un "Cubo informe de liquidación" 

3-Tomo solo los códigos uso en las liquidaciones y Armo un txt RelacionONVIO.txt
OJOOOO !!! Que en los casos que tiene alias, usa el Alias y no el Código. Así revisar los que poseen alias.

4-hago correr el Procesador.py y queda armado el nuevo archivo de conceptos para 
ARCA llamado "Relacion_de_Conceptos_COINCIDENTES.TXT" se usará para importar en la web

5-Codigos_De_Mapeo_NO_ENCONTRADOS.TXT son los conceptos que deben configurarse en ONVIO para importar (si queda vacío es porque encontró todos)

6- Emitir un "LibroDeSueldosDigital.txt" desde ONVIO y hacer correr el archivo LibroSueldo.py este modifica el archivo y sustituye el código onvio por el alias.
 
