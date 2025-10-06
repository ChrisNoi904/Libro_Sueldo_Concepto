import csv
import io
import zipfile
from flask import Flask, request, send_file, render_template_string, redirect, url_for

# =========================================================================
# 1. LÓGICA DEL NEGOCIO (Adaptada para usar cadenas de texto en memoria)
# =========================================================================

# --- Configuración de Archivos y Codificación ---
DELIMITADOR = ';' 
ENCODING = 'latin-1' 

# POSICIONES y Constantes para RelacionONVIO.txt (Delimitado)
COL_CODIGO_EMPLEADOR_ALIAS = 0 
COL_ALIAS = 2 

# POSICIONES y Constantes para Relacion_de_Conceptos.TXT (Ancho Fijo)
POS_START = 6 
POS_END = 16 
CODIGO_LENGTH = 10 

def limpiar_clave(texto):
    """Limpia la cadena de texto de espacios, saltos de línea y caracteres invisibles."""
    if texto is None:
        return ""
    # Se usa .strip() para eliminar espacios/saltos de línea al inicio/fin
    return texto.strip().replace('\x00', '').upper()


def procesar_archivos_de_texto(alias_content, conceptos_content):
    """
    Ejecuta toda la lógica de los 3 pasos usando el contenido de los archivos 
    como cadenas de texto (strings) y retorna los 3 archivos de salida.
    """
    
    # Variables de almacenamiento (locales a esta función)
    mapeo_alias = {}
    mapeo_filas_originales = {} 
    codigos_utilizados = set()
    
    # Búferes de salida (cadenas de texto para los 3 archivos de reporte)
    registros_coincidentes_out = ""
    registros_no_coincidentes_out = ""
    codigos_no_usados_out = ""

    # ----------------------------------------------------
    # 1. PASO: Crear el Mapeo de Alias (Leyendo alias_content)
    # ----------------------------------------------------
    try:
        # Convertimos la cadena de texto (string) en un objeto IO para que csv.reader lo lea
        alias_stream = io.StringIO(alias_content) 
        reader = csv.reader(alias_stream, delimiter=DELIMITADOR)
        
        for fila in reader:
            # Recreamos la línea original para el reporte de no utilizados
            linea_original_alias = DELIMITADOR.join(fila) + '\n'
            
            if len(fila) > COL_ALIAS:
                codigo_empleador_limpio = limpiar_clave(fila[COL_CODIGO_EMPLEADOR_ALIAS])
                alias = fila[COL_ALIAS].strip()
                
                if codigo_empleador_limpio:
                    mapeo_alias[codigo_empleador_limpio] = alias
                    mapeo_filas_originales[codigo_empleador_limpio] = linea_original_alias
    except Exception as e:
        raise Exception(f"Error en Paso 1 (Mapeo): {e}")

    # ----------------------------------------------------
    # 2. PASO: Modificar, Filtrar y Separar Registros (Leyendo conceptos_content)
    # ----------------------------------------------------
    try:
        # splitlines(True) mantiene los saltos de línea originales
        for linea_original in conceptos_content.splitlines(True):
            
            if len(linea_original) >= POS_END:
                codigo_empleador_raw = linea_original[POS_START:POS_END]
                codigo_empleador_limpio = limpiar_clave(codigo_empleador_raw)

                if codigo_empleador_limpio in mapeo_alias:
                    # --- CÓDIGO COINCIDENTE ---
                    codigos_utilizados.add(codigo_empleador_limpio)
                    nuevo_alias = mapeo_alias[codigo_empleador_limpio]
                    
                    # Formateo del nuevo alias para el ancho fijo
                    alias_formateado = nuevo_alias.ljust(CODIGO_LENGTH)
                    
                    linea_modificada = (
                        linea_original[:POS_START] +
                        alias_formateado +
                        linea_original[POS_END:]
                    )
                    
                    # Escribimos al búfer de coincidentes
                    registros_coincidentes_out += linea_modificada 
                    
                else:
                    # --- CÓDIGO NO COINCIDENTE ---
                    # Escribimos al búfer de no coincidentes
                    registros_no_coincidentes_out += linea_original
                    
    except Exception as e:
        raise Exception(f"Error en Paso 2 (Procesamiento): {e}")

    # ----------------------------------------------------
    # 3. PASO: Generar el Reporte de Códigos de Mapeo NO utilizados
    # ----------------------------------------------------
    try:
        codigos_no_encontrados = set(mapeo_alias.keys()) - codigos_utilizados
        
        for codigo_no_usado in sorted(list(codigos_no_encontrados)):
            # Escribimos la fila original del mapeo no utilizado al búfer
            codigos_no_usados_out += mapeo_filas_originales[codigo_no_usado]
            
    except Exception as e:
        raise Exception(f"Error en Paso 3 (Reporte): {e}")

    # Retornamos los 3 resultados finales en el formato esperado
    return {
        "Relacion_de_Conceptos_COINCIDENTES.TXT": registros_coincidentes_out,
        "Relacion_de_Conceptos_NO_COINCIDENTES.TXT": registros_no_coincidentes_out,
        "Codigos_De_Mapeo_NO_ENCONTRADOS.TXT": codigos_no_usados_out,
    }


# =========================================================================
# 2. APLICACIÓN FLASK (Rutas y Lógica Web)
# =========================================================================

app = Flask(__name__)

# Plantilla HTML para el formulario
HTML_FORM = """
<!doctype html>
<html>
<head>
    <title>Procesador de Archivos TXT</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        h1 { color: #333; }
        .error { color: red; font-weight: bold; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Herramienta de Mapeo y Procesamiento de Conceptos</h1>
    {% if error %}
        <p class="error">Error: {{ error }}</p>
    {% endif %}
    <p>Por favor, sube los dos archivos de texto para comenzar el procesamiento.</p>
    
    <form method=post enctype=multipart/form-data action="/process">
        <p>1. Archivo de Alias (RelacionONVIO.txt): <input type=file name=alias_file required></p>
        <p>2. Archivo a Modificar (Relacion_de_Conceptos.TXT): <input type=file name=conceptos_file required></p>
        <p><input type=submit value=Procesar Archivos></p>
    </form>
    <hr>
    <p>La herramienta generará un archivo ZIP con los 3 reportes en tu carpeta de Descargas.</p>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Muestra el formulario inicial, incluyendo mensajes de error si hay."""
    error_message = request.args.get('error', None)
    return render_template_string(HTML_FORM, error=error_message)

@app.route('/process', methods=['POST'])
def process():
    # 1. Obtener los archivos subidos
    alias_file = request.files.get('alias_file')
    conceptos_file = request.files.get('conceptos_file')

    if not alias_file or not conceptos_file:
        # Si falta un archivo, redirigir con un mensaje de error
        return redirect(url_for('index', error="Debe subir ambos archivos (Alias y Conceptos)."))

    # 2. Leer y decodificar el contenido de los archivos
    try:
        alias_content = alias_file.read().decode(ENCODING)
        conceptos_content = conceptos_file.read().decode(ENCODING)
    except UnicodeDecodeError:
        return redirect(url_for('index', error="Error de codificación. Asegúrese de que los archivos sean 'latin-1' (ISO-8859-1)."))
    except Exception as e:
        return redirect(url_for('index', error=f"Error al leer los archivos: {e}"))

    # 3. Llamar a la lógica de procesamiento
    try:
        archivos_salida = procesar_archivos_de_texto(alias_content, conceptos_content)
    except Exception as e:
        # Captura cualquier error ocurrido dentro de tu lógica de negocio
        return redirect(url_for('index', error=f"Error durante el procesamiento de datos: {e}"))

    # 4. Crear un archivo ZIP en memoria (buffer)
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for nombre, contenido in archivos_salida.items():
            # Codificamos el contenido de nuevo a 'latin-1' para guardarlo en el ZIP
            zf.writestr(nombre, contenido.encode(ENCODING))
    
    mem_zip.seek(0) # Mueve el puntero al inicio del archivo en memoria

    # 5. Forzar la descarga del ZIP
    return send_file(
        mem_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name='Reportes_Procesados.zip'
    )

# =========================================================================
# 3. EJECUCIÓN DEL SERVIDOR
# =========================================================================

if __name__ == '__main__':
    # Esto es solo para pruebas locales. Render usará Gunicorn.
    app.run(debug=True)
