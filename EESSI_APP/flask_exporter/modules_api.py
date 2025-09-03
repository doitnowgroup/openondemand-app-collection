from flask import Flask, jsonify
import subprocess
from flask_cors import CORS  # Importar CORS

app = Flask(__name__)

# Habilitar CORS para todos los orígenes (permitir que cualquier dominio pueda hacer solicitudes)
CORS(app)

@app.route('/modules', methods=['GET'])
def get_modules():
    try:
        # Ejecutar el comando source seguido de module avail para obtener la lista completa
        command = "source /cvmfs/software.eessi.io/versions/2023.06/init/bash > /dev/null 2>&1 && module --nx avail 2>&1"

        # Ejecutar el comando en una sola shell
        result = subprocess.run(command, shell=True, executable="/bin/bash", stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        # Filtrar y obtener solo las líneas relevantes de la salida (módulos disponibles)
        modules_list = []
        skip_lines = False  # Variable para indicar cuándo empezar a omitir líneas
        line_counter = 0  # Contador de líneas para omitir las primeras tres líneas

        # Usamos el resultado de stdout, pero saltamos la primera línea
        lines = result.stdout.splitlines()[2:]  # Omitir la primera línea

        for line in lines:

            if '-----------------' in line:
                break  # Salimos del bucle y dejamos de procesar las demás líneas

            # Si no estamos omitiendo líneas, procesamos normalmente
            if not skip_lines and line.strip() and not line.startswith('('):
                # Dividir la línea por espacios y agregar todos los módulos a la lista
                modules = line.split()  # Esto dividirá la línea en partes por los espacios
                for module in modules:
                    if not module.startswith('('):  # Ignorar módulos que tengan (D) o (E)
                        modules_list.append(module.strip())

        # Verificar si los módulos fueron capturados correctamente
        if len(modules_list) == 0:
            return jsonify({
                'success': False,
                'error': 'No se encontraron módulos disponibles.'
            }), 404

        # Devolver la lista completa de módulos
        return jsonify({
            'success': True,
            'modules': modules_list
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))


