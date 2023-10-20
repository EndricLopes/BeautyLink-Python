from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS, cross_origin
from werkzeug.security import ( generate_password_hash, check_password_hash )
import re
from datetime import datetime,timedelta, time
import os
import pytz

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
        return jsonify({'message': 'Login bem-sucedido'})
    else:
        return jsonify({'message': 'Nome de usuário ou senha inválidos'}), 401
    



@app.route('/Ponto', methods=['POST'])
@cross_origin(supports_credentials=True)
def bater_ponto():
    dados = request.get_json()
    usuario = dados['usuario']

    # Obter a hora atual
    fuso = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso)
    
    hora = time(agora.hour, agora.minute)

    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM controle_login WHERE l_usuario = %s', (usuario,))
    usuario_existente = cursor.fetchone()
    # Viu se o usuario existe

    if usuario_existente:
        cursor.execute('SELECT * FROM controle_ponto WHERE fk_id_login_ponto = %s AND dia = CURDATE() ORDER BY id_cntrl_ponto DESC LIMIT 1', (usuario_existente['id_login'],))
        ponto_existente_hoje = cursor.fetchone()
        # Viu se ja tem um ponto registrado hoje com seu id atraves de uma lista, que é a coluna do id_cntrl_ponto

        ultima_hora_inserida = None


        if ponto_existente_hoje:
            ultima_hora_inserida = max([(datetime.min + v).time() for k, v in ponto_existente_hoje.items() if 'hora' in k and v is not None])
             # Define uma lista com os valores de id_cntrl_ponto de hj, só considera as colunas que começam com hora e não são nulo, pega o maior valor da lista.


            if ultima_hora_inserida is not None and hora <= ultima_hora_inserida:
                resp = jsonify({'message': 'A nova batida de ponto deve ser maior do que a última hora inserida'})
                return resp, 400
                # Não deixa bater ponto contrário a entropia temporal.


            campos_horas = ['hora_saida1', 'hora_entrada2', 'hora_saida2', 'hora_entrada3','hora_saida3']
            for campo in campos_horas:
                if not ponto_existente_hoje[campo]:
                    comando = f'UPDATE controle_ponto SET {campo} = %s WHERE id_cntrl_ponto = %s'
                    valores = (hora, ponto_existente_hoje['id_cntrl_ponto'])
                    break
            
            else:
                comando = 'INSERT INTO controle_ponto (usuario, fk_id_login_ponto, hora_entrada1, dia) VALUES (%s, %s, %s, CURDATE())'
                valores = (usuario_existente['l_usuario'], usuario_existente['id_login'], hora)
                # Se todas as colunas estão preenchidas, cria uma nova coluna.


        else:
            comando = 'INSERT INTO controle_ponto (usuario, fk_id_login_ponto, hora_entrada1, dia) VALUES (%s, %s, %s, CURDATE())'
            valores = (usuario_existente['l_usuario'], usuario_existente['id_login'], hora)
            # Se ainda não houver ponto hoje, adiciona na primeira coluna.


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
    


@app.route('/Hora', methods=['GET'])
@cross_origin()
def get_hora():
    # Obter a hora atual no fuso horário de Brasília
    fuso = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso)
    
    # Formatar a hora como uma string no formato HH:MM:SS
    hora_str = agora.strftime('%H:%M')
    
    # Retornar a hora como JSON
    return jsonify({'hora': hora_str})




@app.route('/Espelho', methods=['GET'])
@cross_origin()
def get_horas_trabalhadas():
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT SEC_TO_TIME(SUM(IF(hora_saida1 < hora_entrada1, TIME_TO_SEC(TIMEDIFF(hora_saida1 + INTERVAL 24 HOUR, hora_entrada1)), TIME_TO_SEC(TIMEDIFF(hora_saida1, hora_entrada1))) +IF(hora_saida2 < hora_entrada2, TIME_TO_SEC(TIMEDIFF(hora_saida2 + INTERVAL 24 HOUR, hora_entrada2)), TIME_TO_SEC(TIMEDIFF(hora_saida2, hora_entrada2)))) - 120*60*60) AS 'Saldo Mensal'FROM  controle_ponto WHERE     fk_id_login_ponto = 26 AND    dia BETWEEN '2023-08-10' AND '2023-09-10';")    
    saldo = cursor.fetchall()

    cursor.execute("SELECT SEC_TO_TIME(SUM(TIME_TO_SEC(TIMEDIFF(hora_saida3, hora_entrada3)))) AS 'Horas Extras no Mês' FROM controle_ponto WHERE fk_id_login_ponto = 27 AND dia BETWEEN '2023-09-01' AND '2023-10-07';")
    Horas_extra = cursor.fetchall()

    cursor.execute("SELECT hora_entrada1, hora_saida2, dia FROM controle_ponto WHERE fk_id_login_ponto = 26 AND dia BETWEEN '2023-09-10' AND '2023-10-10';")    
    results = cursor.fetchall()

    response = []
    for result in results:
        Hora_entrada = result['hora_entrada1']
        Hora_saida = result['hora_saida2']
        Dia = result['dia']
        response.append({'Saldo Mensal': str(saldo)}, {'Horario entrada': str(Hora_entrada)},{'Horario saida': str(Hora_saida)}, {'Data': str(Dia)}, {'Horas extra': str(Horas_extra)})

    return jsonify(response)


@app.route('/sua-rota')
@cross_origin()
def get_dados():
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            dia,
            hora_entrada1,
            hora_saida1,
            hora_entrada2,
            hora_saida2,
            hora_entrada3,
            hora_saida3,
            SEC_TO_TIME(
                IF(hora_saida1 < hora_entrada1, TIME_TO_SEC(TIMEDIFF(hora_saida1 + INTERVAL 24 HOUR, hora_entrada1)), TIME_TO_SEC(TIMEDIFF(hora_saida1, hora_entrada1))) +
                IF(hora_saida2 < hora_entrada2, TIME_TO_SEC(TIMEDIFF(hora_saida2 + INTERVAL 24 HOUR, hora_entrada2)), TIME_TO_SEC(TIMEDIFF(hora_saida2, hora_entrada2))) +
                IF(hora_saida3 < hora_entrada3, TIME_TO_SEC(TIMEDIFF(hora_saida3 + INTERVAL 24 HOUR, hora_entrada3)), TIME_TO_SEC(TIMEDIFF(hora_saida3, hora_entrada3))) -
                8*60*60
            ) AS 'Saldo',
            SEC_TO_TIME(
                IF(hora_saida3 < hora_entrada3, TIME_TO_SEC(TIMEDIFF(hora_saida3 + INTERVAL 24 HOUR, hora_entrada3)), TIME_TO_SEC(TIMEDIFF(hora_saida3, hora_entrada3)))
            ) AS 'Horas extra'
        FROM 
            controle_ponto
        WHERE 
            fk_id_login_ponto = 26 AND
            dia BETWEEN '2023-08-10' AND '2023-09-10';
    """)

    result = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    data = [
        dict(zip(col_names, row))
        for row in result
    ]

    return jsonify(data)

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
