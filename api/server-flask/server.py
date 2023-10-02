from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS, cross_origin
from werkzeug.security import ( generate_password_hash, check_password_hash )
import re
from datetime import datetime
import os

app = Flask(__name__)
CORS(app, origins=['https://pontomidas.vercel.app/' ], supports_credentials=True)

# Configuração do banco de dados
# Configuração do banco de dados
conexao = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
)


@app.route('/', methods=['GET'])
@cross_origin()
def home():
    return "Hello, World!"


@app.route('/Cadastro', methods=['GET'])
@cross_origin()
def get_usuarios():
    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM cadastro')
    usuarios = cursor.fetchall()
    cursor.close()
    return jsonify(usuarios)



@app.route('/Usuarios', methods=['GET'])
@cross_origin()
def get_usuario(id):
    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM cadastro WHERE id = %s', (id,))
    usuario = cursor.fetchone()
    cursor.close()
    if usuario:
        return jsonify(usuario)
    else:
        return jsonify({'message': 'Usuário não encontrado'}), 404



@app.route('/cadastro', methods=['POST'])
@cross_origin()
def cadastro():
    if request.method == 'POST':
        userDetails = request.get_json()
        nome = userDetails['nome']
        usuario = userDetails['usuario']
        email = userDetails['email']
        senha = userDetails['senha']

        hashed_senha = generate_password_hash(senha)

        # Verifica se todos os campos estão preenchidos
        if not nome or not usuario or not email or not senha:
            return jsonify({'message' : 'Por favor, preencha todos os campos.'}), 400

        # Verifica se o email é válido
        email_regex = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, email):
            return jsonify({'message' : 'Por favor, insira um email válido.'}), 400
        
        cursor = conexao.cursor()

        # Verifica se o usuário ou email já existem
        cursor.execute("SELECT * FROM cadastro WHERE usuario=%s OR email=%s", (usuario, email))
        account = cursor.fetchone()
        if account:
            return jsonify({'message' : 'Usuário ou email já existem.'}), 400

        add_user = ("INSERT INTO cadastro "
                   "(nome, usuario, email, senha) "
                   "VALUES (%s, %s, %s, %s)")
        data_user = (nome, usuario, email, hashed_senha)
        
        # Insere nova entrada
        cursor.execute(add_user, data_user)

        # Confirma a inserção
        try:
            conexao.commit()
        except Exception as e:
            print("Falha ao fazer commit: ", e)

        cursor.close()
        
        return jsonify({'message' : 'Cadastro realizado com sucesso!'})



@app.route('/Login', methods=['POST'])
@cross_origin()
def login():
    dados = request.get_json()
    usuario = dados['usuario']
    senha = dados['senha']

    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM cadastro WHERE usuario = %s', (usuario,))
    usuario_existente = cursor.fetchone()
    cursor.close()
    # Verifica se esse usuario existe

    if usuario_existente and check_password_hash(usuario_existente['senha'], senha):
        # Aqui você poderia gerar e retornar um token de acesso
        return jsonify({'message': 'Login bem-sucedido'})
    else:
        return jsonify({'message': 'Nome de usuário ou senha inválidos'}), 401
    



from datetime import datetime, timedelta

@app.route('/Ponto', methods=['POST'])
@cross_origin(supports_credentials=True)
def bater_ponto():
    dados = request.get_json()
    usuario = dados['usuario']
    hora = datetime.strptime(dados['hora'], '%H:%M').time()  # converta a string de hora para um objeto time

    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM controle_login WHERE l_usuario = %s', (usuario,))
    usuario_existente = cursor.fetchone()
    # Viu se o usuario existe
    
    if usuario_existente:
        cursor.execute('SELECT * FROM controle_ponto WHERE fk_id_login_ponto = %s AND dia = CURDATE() ORDER BY id_cntrl_ponto DESC LIMIT 1', (usuario_existente['id_login'],))
        ponto_existente_hoje = cursor.fetchone()
        # Viu se ja tem um ponto registrado hoje atraves de uma lista, que é a coluna do id_cntrl_ponto

        ultima_hora_inserida = None

        if ponto_existente_hoje:
            ultima_hora_inserida = max([(datetime.min + v).time() if isinstance(v, timedelta) else datetime.strptime(v, '%H:%M').time() for k, v in ponto_existente_hoje.items() if 'hora' in k and v is not None])
                # Define uma lista, com os valores de id_cntrl_ponto de hj, somente considera a coluna que começa com hora e não é nulo.

            if ultima_hora_inserida is not None and hora <= ultima_hora_inserida:
                resp = jsonify({'message': 'A nova batida de ponto deve ser maior do que a última hora inserida'})
                return resp, 400

            if not ponto_existente_hoje['hora_saida1']:
                comando = 'UPDATE controle_ponto SET hora_saida1 = %s WHERE id_cntrl_ponto = %s'
                valores = (hora, ponto_existente_hoje['id_cntrl_ponto'])
            elif not ponto_existente_hoje['hora_entrada2']:
                comando = 'UPDATE controle_ponto SET hora_entrada2 = %s WHERE id_cntrl_ponto = %s'
                valores = (hora, ponto_existente_hoje['id_cntrl_ponto'])
            elif not ponto_existente_hoje['hora_saida2']:
                comando = 'UPDATE controle_ponto SET hora_saida2 = %s WHERE id_cntrl_ponto = %s'
                valores = (hora, ponto_existente_hoje['id_cntrl_ponto'])
            else:
                resp = jsonify({'message': 'Todos os pontos de hoje já foram usados'})
                return resp, 400
            
        else:
            comando = 'INSERT INTO controle_ponto (usuario, fk_id_login_ponto, hora_entrada1, dia) VALUES (%s, %s, %s, CURDATE())'
            valores = (usuario_existente['l_usuario'], usuario_existente['id_login'], hora)

        cursor.execute(comando, valores)
        
        try:
            conexao.commit()
            resp = jsonify({'message': 'Ponto batido com sucesso'})
            return resp, 201
        except Exception as e:
            print("Falha ao fazer commit: ", e)
            resp = jsonify({'message': 'Falha ao bater ponto'})
            return resp, 500

    else:
        resp = jsonify({'message': 'Usuário não encontrado'})
        return resp, 404





if __name__ == '__main__':
    app.run(debug=True)







#@app.route('/Update/<int:id>', methods=['PUT'])
#def atualizar_usuario(id):
#    dados = request.get_json()
#    nome = dados['nome']
#    usuario = dados['usuario']
#
#    cursor = conexao.cursor()
#    comando = 'UPDATE cadastro SET nome = %s, usuario = %s WHERE id = %s'
#    valores = (nome, usuario, id)
#    cursor.execute(comando, valores)
#    conexao.commit()
#    cursor.close()
#
 #   return jsonify({'message': 'Usuário atualizado com sucesso'})



#@app.route('/Excluir/<int:id>', methods=['DELETE'])
#def excluir_usuario(id):
#    cursor = conexao.cursor()
#    comando = 'DELETE FROM cadastro WHERE id = %s'
#    valores = (id,)
#    cursor.execute(comando, valores)
#    conexao.commit()
#    cursor.close()
#
#    return jsonify({'message': 'Usuário excluído com sucesso'})
