from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
import csv
from flask import send_file
from flask import jsonify
from pydub import AudioSegment

app = Flask(__name__)
app.secret_key = 'clave_secreta'
app.config['UPLOAD_FOLDER'] = 'static/audios'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializa la base de datos
def init_db():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        # Tabla del administrador
        c.execute('''CREATE TABLE IF NOT EXISTS administrador (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT UNIQUE,
                        contrasena_hash TEXT
                    )''')
        # Inserta administrador por defecto si no existe
        c.execute('SELECT * FROM administrador WHERE usuario=?', ('admin',))
        if not c.fetchone():
            c.execute('INSERT INTO administrador (usuario, contrasena_hash) VALUES (?, ?)', 
                      ('admin', generate_password_hash('admin123')))
        
        # Tabla de usuarios normales
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        correo TEXT,
                        permisos TEXT,
                        ruta_audio TEXT
                    )''')
        conn.commit()

init_db()

# Función: crear carpeta y guardar audio original
def crear_carpeta_y_guardar_audio(nombre_usuario, archivo):
    carpeta_usuario = os.path.join(app.config['UPLOAD_FOLDER'], nombre_usuario)
    os.makedirs(carpeta_usuario, exist_ok=True)

    filename = secure_filename(archivo.filename)
    ruta_completa = os.path.join(carpeta_usuario, filename)
    archivo.save(ruta_completa)

    # Ruta relativa desde la carpeta 'static' para que funcione en HTML
    ruta_relativa = os.path.relpath(ruta_completa, 'static').replace(os.sep, '/')
    ruta_relativa = f'static/{ruta_relativa}'  # Para que funcione con el atributo  de <audio>

    return ruta_relativa, carpeta_usuario


# aumento de datos (20 versiones)
def aumentar_audio_gan_simulado(ruta_original, carpeta_destino):
    audio = AudioSegment.from_file(ruta_original)
    base_nombre = os.path.splitext(os.path.basename(ruta_original))[0]

    for i in range(20):
        modificado = audio

        if i % 3 == 0:
            modificado = modificado.speedup(playback_speed=1.1)
        elif i % 3 == 1:
            modificado = modificado.low_pass_filter(3000)
        else:
            modificado = modificado.reverse()

        nuevo_nombre = f"{base_nombre}_aug_{i}.wav"
        ruta_nueva = os.path.join(carpeta_destino, nuevo_nombre)
        modificado.export(ruta_nueva, format="wav")

# --- Rutas ---

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/identificar')
def identificar():
    return render_template('identificar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute('SELECT contrasena_hash FROM administrador WHERE usuario=?', (usuario,))
            resultado = c.fetchone()
            if resultado and check_password_hash(resultado[0], contrasena):
                session['admin'] = usuario
                return redirect('/dashboard')
            else:
                flash('Credenciales incorrectas')
                return redirect('/login')
    else:
        return render_template('login.html')  # <- Mostrar formulario en GET

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/')
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM usuarios')
        usuarios = c.fetchall()
    return render_template('dashboard.html', usuarios=usuarios)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if 'admin' not in session:
        return redirect('/')
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        permisos = ', '.join(request.form.getlist('permisos'))
        archivo = request.files['audio']
        if archivo:
            ruta_audio, carpeta_usuario = crear_carpeta_y_guardar_audio(nombre, archivo)
            aumentar_audio_gan_simulado(ruta_audio, carpeta_usuario)
        else:
            ruta_audio = ''
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO usuarios (nombre, correo, permisos, ruta_audio) VALUES (?, ?, ?, ?)',
                      (nombre, correo, permisos, ruta_audio))
            conn.commit()
        return redirect('/dashboard')
    return render_template('agregar_usuario.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'admin' not in session:
        return redirect('/')
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        if request.method == 'POST':
            nombre = request.form['nombre']
            correo = request.form['correo']
            permisos = ', '.join(request.form.getlist('permisos'))
            archivo = request.files['audio']
            if archivo:
                ruta_audio, carpeta_usuario = crear_carpeta_y_guardar_audio(nombre, archivo)
                aumentar_audio_gan_simulado(ruta_audio, carpeta_usuario)
                c.execute('UPDATE usuarios SET nombre=?, correo=?, permisos=?, ruta_audio=? WHERE id=?',
                          (nombre, correo, permisos, ruta_audio, id))
            else:
                c.execute('UPDATE usuarios SET nombre=?, correo=?, permisos=? WHERE id=?',
                          (nombre, correo, permisos, id))
            conn.commit()
            return redirect('/dashboard')
        else:
            c.execute('SELECT * FROM usuarios WHERE id=?', (id,))
            usuario = c.fetchone()
            return render_template('editar_usuario.html', usuario=usuario)

@app.route('/eliminar/<int:id>')
def eliminar(id):
    if 'admin' not in session:
        return redirect('/')
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM usuarios WHERE id=?', (id,))
        conn.commit()
    return redirect('/dashboard')

@app.route('/exportar_csv')
def exportar_csv():
    if 'admin' not in session:
        return redirect('/')
    
    archivo_csv = 'usuarios_exportados.csv'

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, nombre, correo, permisos, ruta_audio FROM usuarios")
        usuarios = c.fetchall()

    # Crear archivo CSV
    with open(archivo_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Nombre', 'Correo', 'Permisos', 'Ruta de Audio'])
        writer.writerows(usuarios)

    # Enviar archivo como descarga
    return send_file(archivo_csv, as_attachment=True)

@app.route('/exportar_json')
def exportar_json():
    if 'admin' not in session:
        return redirect('/')

    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row  # Permite obtener los datos como diccionarios
        c = conn.cursor()
        c.execute("SELECT id, nombre, correo, permisos, ruta_audio FROM usuarios")
        usuarios = c.fetchall()

    # Convertir filas a lista de diccionarios
    lista_usuarios = [dict(u) for u in usuarios]

    return jsonify(lista_usuarios)


if __name__ == '__main__':
    app.run(debug=True)
