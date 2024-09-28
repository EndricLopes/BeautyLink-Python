from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime
import os
import pytz
import logging
import time

app = Flask(__name__)
CORS(app, origins=['https://beauty-link-react.vercel.app/'], supports_credentials=True)

# Configuração do banco de dados com pool de conexões
from mysql.connector import pooling

dbconfig = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": 'BEAUTY_LINK',
}
connection_pool = pooling.MySQLConnectionPool(pool_name="mypool",
                                              pool_size=10,
                                              **dbconfig)

# Função para obter conexão do pool
def get_connection():
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as e:
        logging.error(f"Erro ao conectar no banco de dados: {e}")
        return None

# Log de tempo
logging.basicConfig(level=logging.INFO)


@app.route('/', methods=['GET'])
@cross_origin()
def home():
    return "Hello, World!"


@app.route('/Cadastro', methods=['GET'])
@cross_origin()
def get_usuarios():
    connection = get_connection()
    if not connection:
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    with connection.cursor(dictionary=True) as cursor:
        start_time = time.time()  # Início da medição de tempo
        cursor.execute('SELECT * FROM USUARIO')
        usuarios = cursor.fetchall()
        logging.info(f"Tempo de execução de get_usuarios: {time.time() - start_time} segundos")
    
    connection.close()
    return jsonify(usuarios)


@app.route('/Usuarios', methods=['GET'])
@cross_origin()
def get_usuario():
    usuario_id = request.args.get('id')
    if not usuario_id:
        return jsonify({'message': 'ID de usuário não fornecido'}), 400

    connection = get_connection()
    if not connection:
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    with connection.cursor(dictionary=True) as cursor:
        start_time = time.time()  # Início da medição de tempo
        cursor.execute('SELECT * FROM USUARIO WHERE ID_USUARIO = %s', (usuario_id,))
        usuario = cursor.fetchone()
        logging.info(f"Tempo de execução de get_usuario: {time.time() - start_time} segundos")
    
    connection.close()

    if usuario:
        return jsonify(usuario)
    else:
        return jsonify({'message': 'Usuário não encontrado'}), 404


@app.route('/Login', methods=['POST'])
@cross_origin()
def login():
    dados = request.get_json()
    usuario = dados['usuario']
    senha = dados['senha']

    connection = get_connection()
    if not connection:
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT * FROM USUARIO WHERE LOGIN = %s', (usuario,))
        usuario_existente = cursor.fetchone()

    connection.close()

    if usuario_existente and check_password_hash(usuario_existente['SENHA'], senha):
        return jsonify({
            'message': 'Login bem-sucedido',
            'id_usuario': usuario_existente['ID_USUARIO']
        })
    else:
        return jsonify({'message': 'Nome de usuário ou senha inválidos'}), 401


@app.route('/Ponto', methods=['POST'])
@cross_origin()
def cadastrar_atendimento():
    dados = request.get_json()

    tipo_servico = dados.get('tipo_servico')
    data_atendimento = dados.get('data_atendimento')
    data_marcacao = dados.get('data_marcacao')
    status_agendamento = dados.get('status_agendamento')
    observacao = dados.get('observacao')
    fk_id_funcionario = dados.get('fk_id_funcionario')
    fk_id_usuario_cliente = dados.get('fk_id_usuario_cliente')

    if not all([tipo_servico, data_atendimento, data_marcacao, status_agendamento, fk_id_funcionario, fk_id_usuario_cliente]):
        return jsonify({'message': 'Todos os campos são obrigatórios'}), 400

    connection = get_connection()
    if not connection:
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    with connection.cursor() as cursor:
        try:
            comando = '''
                INSERT INTO AGENDA (TIPO_SERVICO, DATA_ATENDIMENTO, DATA_MARCACAO, STATUS_AGENDAMENTO, OBSERVACAO, FK_ID_FUNCIONARIO, FK_ID_USUARIO_CLIENTE)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            valores = (tipo_servico, data_atendimento, data_marcacao, status_agendamento, observacao, fk_id_funcionario, fk_id_usuario_cliente)
            cursor.execute(comando, valores)
            connection.commit()

            return jsonify({'message': 'Atendimento cadastrado com sucesso'}), 201

        except mysql.connector.Error as e:
            logging.error(f"Erro ao cadastrar atendimento: {e}")
            connection.rollback()
            return jsonify({'message': 'Falha ao cadastrar atendimento'}), 500

        finally:
            connection.close()


@app.route('/Atendimento', methods=['GET'])
@cross_origin()
def get_atendimentos():
    usuario = request.args.get('usuario')

    if not usuario:
        return jsonify({'message': 'ID do usuário não fornecido'}), 400

    connection = get_connection()
    if not connection:
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    with connection.cursor(dictionary=True) as cursor:
        start_time = time.time()  # Início da medição de tempo
        query = '''
            SELECT DATA_ATENDIMENTO
            FROM AGENDA
            WHERE FK_ID_USUARIO_CLIENTE = %s AND STATUS_AGENDAMENTO = 'CADASTRADO'
        '''
        cursor.execute(query, (usuario,))
        atendimentos = cursor.fetchall()
        logging.info(f"Tempo da consulta get_atendimentos: {time.time() - start_time} segundos")

    connection.close()

    if atendimentos:
        return jsonify(atendimentos)
    else:
        return jsonify([])


import mercadopago  # Importando o SDK do Mercado Pago

# Configurar o Mercado Pago com suas credenciais de produção ou sandbox
mercadopago_access_token = 'SUA_ACCESS_TOKEN_DO_MERCADO_PAGO'
sdk = mercadopago.SDK(mercadopago_access_token)

@app.route('/processar-pagamento', methods=['POST'])
@cross_origin()
def processar_pagamento():
    dados = request.get_json()
    
    # Verifica se todos os campos obrigatórios estão presentes
    if not all([dados.get('amount'), dados.get('description'), dados.get('email')]):
        return jsonify({'message': 'Campos obrigatórios ausentes'}), 400

    payment_data = {
        "transaction_amount": float(dados['amount']),
        "description": dados['description'],
        "payment_method_id": "pix",  # Utilizando o método de pagamento PIX
        "payer": {
            "email": dados['email'],
        }
    }

    # Tenta criar um pagamento utilizando o SDK do Mercado Pago
    try:
        payment_response = sdk.payment().create(payment_data)
        payment_info = payment_response["response"]

        # Verifica se o pagamento foi criado com sucesso
        if payment_info.get('status') == 'pending':
            return jsonify({
                "message": "Pagamento criado com sucesso",
                "qr_code": payment_info['point_of_interaction']['transaction_data']['qr_code'],
                "qr_code_base64": payment_info['point_of_interaction']['transaction_data']['qr_code_base64'],
                "status": payment_info['status']
            }), 201
        else:
            return jsonify({
                "message": "Falha ao criar o pagamento",
                "error": payment_info
            }), 400
    except Exception as e:
        logging.error(f"Erro ao processar pagamento: {e}")
        return jsonify({'message': 'Erro ao processar pagamento'}), 500



if __name__ == '__main__':
    app.run(debug=True)

