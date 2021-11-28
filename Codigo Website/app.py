from flask import Flask, render_template, flash ,url_for, request, redirect, jsonify, session, logging
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import Form, StringField, IntegerField, TextAreaField, PasswordField, SelectMultipleField, FileField, validators
from flask_mysqldb import MySQL
import re

app = Flask(__name__)

## Mapeamento da Base dados SQL
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "projetofinal"

mysql = MySQL(app)

# Formulario de Registo
class RegisterForm(Form):
    nome = StringField('Nome', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4,max=25)])
    email = StringField('Email',[validators.Length(min=6,max=50)])
    password = PasswordField('Senha',[validators.DataRequired(), validators.EqualTo('confirm',message='Passwords do not match.'),])

# Função de Registo
@app.route('/registar',methods=['POST','GET'])
def registar():
    form = RegisterForm(request.form)

    #Invocação do Formulário de Registo
    if request.method == 'POST':
        
        nome = form.nome.data
        email = form.email.data
        username = form.username.data
        password = str(form.password.data)
        
        #Criar cursor para gerir a base de dados
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO utilizadores(nome, username, email, password) VALUES (%s,%s,%s,%s)",(nome,username,email,password))
        mysql.connection.commit()
        cur.close()

        flash('Cadastro efetuado.', 'success')
        return redirect(url_for('login'))

    return render_template('registar.html',form=form)

# Função de Login
@app.route('/', methods=['POST','GET'])
def login():
    if 'logged_in' in session:
        return redirect('/main')
    else:
        if request.method == 'POST':
            #Buscar valores de formulario
            username = request.form['username']
            password_recebida = request.form['password']

            # Criar cursor para verificar base de dados
            cur = mysql.connection.cursor()
            result = cur.execute("SELECT * FROM Utilizadores WHERE username = %s",[username])
            
            if result > 0:
                data = cur.fetchone()
                password = data[4]


                #Veriricar senha registada com senha inserida
                if password_recebida == password:
                    #Credenciais validadas
                    session['logged_in'] = True
                    session['username'] = username
                    session['idUtilizador'] = data[0]
                    session['nSerie'] = "NONE"

                    flash("Sistema acessado.","success")
                    
                    #Fechar conexao com MYSQL
                    cur.close()

                    return redirect(url_for('index'))
                else:
                    flash("Senha Incorreta")
                    #Fechar conexao com MYSQL
                    cur.close()
                    return render_template('login.html')
                    
            else:
                
                flash("Utilizador Nao Encontrado")
                #Fechar conexao com MYSQL
                cur.close()
                return render_template('login.html')

        return render_template('login.html')

# Confirmar se o utilizador esta logado
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Acesso não autorizado.', 'danger')
            return redirect(url_for('login'))
    return wrap

# Função de Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('Sessão finalizada.','success')
    return redirect(url_for('login'))

# Funçao de Registo de dispositivos
@app.route('/registarDispositivo',methods=['POST','GET'])
@is_logged_in
def registarDispositivo():
    if request.method == 'POST':

        #Buscar valores de formulario
        designacao = request.form['designacao']
        nSerie = request.form['nSerie']

        # Criar cursor para verificar base de dados
        cur = mysql.connection.cursor()
        cur.execute ( "INSERT INTO device (idUtilizadores,nSerie,designacao) VALUES (%s,%s,%s)", (int(session['idUtilizador']),nSerie,designacao))

        num_rows = cur.execute ( "SELECT nSerie FROM projetofinal.device  ORDER BY idDevice DESC LIMIT 1" )
        if num_rows > 0:
            nSerie = cur.fetchone() 
            
        cur.execute ( "INSERT INTO tirarFotos (nSerie,numeroFotos) VALUES (%s,%s)", (nSerie,0) )
        mysql.connection.commit()

        #Fechar conexao com MYSQL
        cur.close()
        return redirect('/main')

    return render_template('RegistarDispositivo.html')

# Funçao de Listar os Dispositivos do utilizador
@app.route('/listarDispositivos')
@is_logged_in
def listarDispositivos():

     # Criar cursor para verificar base de dados
    cur = mysql.connection.cursor()
    num_rows = cur.execute ("SELECT d.idDevice, d.nSerie, d.designacao FROM device d join utilizadores u on d.idUtilizadores = u.idUtilizadores where u.idUtilizadores = %s",[int(session['idUtilizador'])])
        
    if num_rows > 0:
        devices = cur.fetchall()
        #Fechar conexao com MYSQL
        cur.close()
        return render_template('listarDevices.html', devices=devices, device= session['nSerie'])
    return render_template('listarDevices.html')

# Função para remover dispositivo selecionado pelo utilizador
@app.route('/deleteDispositivo/<int:nSerie>')
@is_logged_in
def deleteDispositivo(nSerie):
    nSerie= int(nSerie)
    # Criar cursor para verificar base de dados
    cur = mysql.connection.cursor()
    cur.execute ("DELETE FROM device WHERE nSerie = %s",[nSerie])
    cur.execute ("DELETE FROM tirarFotos WHERE nSerie = %s",[nSerie])
    mysql.connection.commit()
    #Fechar conexao com MYSQL
    cur.close()
    session['nSerie'] = "NONE"
    return redirect('/listarDispositivos')

# Função para selecionar o dispositivo que pretende utilizar para tirar as fotografias
@app.route('/selecionarDispositivo/<int:nSerie>')
@is_logged_in
def selecionarDispositivo(nSerie):
    nSerie = int(nSerie)
    session['nSerie'] = nSerie
    return redirect('/listarDispositivos')

# Funçao principal que retira as fotografias ja existentes da Base de dados e recebe o pedido do numero de fotografias a tirar pelo utilizador
@app.route('/main', methods=['POST','GET'])
@is_logged_in
def index():
    if request.method == 'GET':
        # Criar cursor para verificar base de dados
        cur = mysql.connection.cursor()
        num_rows = cur.execute ("Select idfotografias,foto,data from fotografias where idUtilizadores = %s order by idfotografias DESC",[int(session['idUtilizador'])])
        
        if num_rows > 0:
            fotografias = cur.fetchall() 
            #Fechar conexao com MYSQL
            cur.close()
            
            return render_template('index.html', fotografias=fotografias, device=session['nSerie'] )
        return render_template('index.html', device=session['nSerie'])
    
    if request.method == 'POST':
        numPhotos = request.form['numeroFotos']
        cur = mysql.connection.cursor()
        cur.execute ("UPDATE tirarfotos SET numeroFotos = %s where nSerie = %s",(numPhotos,int(session['nSerie'])))
        mysql.connection.commit()
        cur.close()
        return redirect('/main')
        
# Função que chamada pelo ESP32 que retorna o numero de fotografias a capturar
@app.route('/tirarfotos/<int:nSerie>')
def fotos(nSerie):
    nSerie = int(nSerie)
    # Criar cursor para verificar base de dados
    cur = mysql.connection.cursor()
    cur.execute("SELECT numeroFotos FROM tirarfotos where nSerie = %s",[nSerie])
    valor = cur.fetchall()
    #Fechar conexao com MYSQL
    cur.close()
    valor2 = (int(re.search(r'\d+', str(valor)).group()))
    return str(valor2)

# Função que recebe do ESP32 as fotografias retiradas e armazena na base de dados
@app.route('/armazenar/<int:nSerie>', methods=['POST'])
def armazenar(nSerie):
    nSerie = int(nSerie)
    if request.method == 'POST':
        foto = request.data
        # Criar cursor para verificar base de dados
        cur = mysql.connection.cursor()
        cur.execute ("INSERT INTO fotografias (nSeriedevice,foto,data) VALUES (%s,%s,CURDATE())", (nSerie,foto,))

        num_rows = cur.execute ("Select f.idfotografias from fotografias f join device d on f.nSeriedevice = d.nSerie where f.nSeriedevice = %s order by f.idfotografias DESC LIMIT 1",[nSerie])
        
        if num_rows > 0:
            respostaSQL = cur.fetchone() 
            idFotoInserida = (int(re.search(r'\d+', str(respostaSQL)).group()))
            

        num_rows = cur.execute ("Select idUtilizadores from device where nSerie = %s",[nSerie])
        
        if num_rows > 0:
            respostaSQL = cur.fetchone()
            idUtilizadorDevice = (int(re.search(r'\d+', str(respostaSQL)).group())) 
           
        
        cur.execute ("UPDATE fotografias SET idUtilizadores = %s where idfotografias = %s",(idUtilizadorDevice,idFotoInserida))

        mysql.connection.commit()

        #Fechar conexao com MYSQL
        cur.close()
        return redirect('/')

# Função que é chamada no final do processo de tirar as fotografias para atualizar o pedido de fotografias de novo para 0
@app.route('/atualizar/<int:nSerie>')
def atualizar(nSerie):
    nSerie = int(nSerie)
    # Criar cursor para verificar base de dados
    cur = mysql.connection.cursor()
    cur.execute ("UPDATE tirarfotos SET numeroFotos = 0 where nSerie = %s", [nSerie])
    mysql.connection.commit()
    #Fechar conexao com MYSQL
    cur.close()
    return redirect('/')
   
# Função de que remove as fotografias da base de dados
@app.route('/delete/<int:id>')
@is_logged_in
def delete(id):
    id= int(id)
    # Criar cursor para verificar base de dados
    cur = mysql.connection.cursor()
    cur.execute ( "DELETE FROM fotografias WHERE idFotografias = %s",[id])
    mysql.connection.commit()
    #Fechar conexao com MYSQL
    cur.close()
    
    return redirect('/main')

if __name__ == "__main__":
    app.secret_key='Sender@2bebot##'
app.run(host="0.0.0.0",port=8080, debug=True)

    
