from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS, cross_origin
import logging
import os
import time
from werkzeug.security import check_password_hash

app = Flask(__name__)
CORS(app, origins=['https://beauty-link-react.vercel.app/'], supports_credentials=True)

# Configuração do banco de dados com pool de conexões
from mysql.connector import pooling

# Configurando o pool de conexões com pool_size reduzido e timeout para conexões ociosas
dbconfig = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": 'BEAUTY_LINK',
    "connection_timeout": 10  # Timeout para conexões ociosas
}

# Ajuste do pool de conexões para evitar o excesso de conexões simultâneas
connection_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, pool_reset_session=True, **dbconfig)

# Função para obter conexão do pool
def get_connection():
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as e:
        app.logger.error(f"Erro ao conectar no banco de dados: {e}")
        return None

# Configuração de logs para debug
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET'])
@cross_origin()
def home():
    app.logger.info('Página inicial acessada.')
    return "Hello, World!"


@app.route('/Cadastro', methods=['POST'])
@cross_origin()
def cadastrar_usuario():
    dados = request.get_json()
    nome = dados.get('nome')
    usuario = dados.get('usuario')
    email = dados.get('email')
    senha = dados.get('senha')

    if not all([nome, usuario, email, senha]):
        app.logger.warning("Todos os campos são obrigatórios.")
        return jsonify({'message': 'Todos os campos são obrigatórios'}), 400

    connection = get_connection()
    if not connection:
        app.logger.error("Falha ao conectar ao banco de dados.")
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor() as cursor:
            comando = '''
                INSERT INTO USUARIO (NOME, LOGIN, EMAIL, SENHA)
                VALUES (%s, %s, %s, %s)
            '''
            valores = (nome, usuario, email, senha)  # Supondo que a senha esteja sem hash, é recomendável usar hash
            cursor.execute(comando, valores)
            connection.commit()

        app.logger.info("Usuário cadastrado com sucesso.")
        return jsonify({'message': 'Usuário cadastrado com sucesso'}), 201
    except mysql.connector.Error as e:
        app.logger.error(f"Erro ao cadastrar usuário: {e}")
        connection.rollback()
        return jsonify({'message': 'Falha ao cadastrar usuário', 'error': str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()


@app.route('/Usuarios', methods=['GET'])
@cross_origin()
def get_usuario():
    usuario_id = request.args.get('id')
    if not usuario_id:
        app.logger.warning("ID de usuário não fornecido.")
        return jsonify({'message': 'ID de usuário não fornecido'}), 400

    connection = get_connection()
    if not connection:
        app.logger.error("Falha ao conectar ao banco de dados.")
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor(dictionary=True) as cursor:
            start_time = time.time()
            cursor.execute('SELECT * FROM USUARIO WHERE ID_USUARIO = %s', (usuario_id,))
            usuario = cursor.fetchone()
            app.logger.info(f"Tempo de execução de get_usuario: {time.time() - start_time} segundos")
    except Exception as e:
        app.logger.error(f"Erro ao buscar usuário: {e}")
        return jsonify({"message": "Erro ao buscar usuário", "error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()

    if usuario:
        return jsonify(usuario)
    else:
        app.logger.warning("Usuário não encontrado.")
        return jsonify({'message': 'Usuário não encontrado'}), 404

@app.route('/Login', methods=['POST'])
@cross_origin()
def login():
    dados = request.get_json()
    usuario = dados['usuario']
    senha = dados['senha']

    connection = get_connection()
    if not connection:
        app.logger.error("Falha ao conectar ao banco de dados.")
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM USUARIO WHERE LOGIN = %s', (usuario,))
            usuario_existente = cursor.fetchone()

        if usuario_existente and check_password_hash(usuario_existente['SENHA'], senha):
            return jsonify({
                'message': 'Login bem-sucedido',
                'id_usuario': usuario_existente['ID_USUARIO']
            })
        else:
            app.logger.warning("Nome de usuário ou senha inválidos.")
            return jsonify({'message': 'Nome de usuário ou senha inválidos'}), 401
    except Exception as e:
        app.logger.error(f"Erro no login: {e}")
        return jsonify({"message": "Erro no login", "error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()

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
        app.logger.warning("Todos os campos são obrigatórios.")
        app.logger.info(f"Data de atendimento recebida: {data_atendimento}")
        return jsonify({'message': 'Todos os campos são obrigatórios'}), 400

    connection = get_connection()
    if not connection:
        app.logger.error("Falha ao conectar ao banco de dados.")
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor() as cursor:
            comando = '''
                INSERT INTO AGENDA (TIPO_SERVICO, DATA_ATENDIMENTO, DATA_MARCACAO, STATUS_AGENDAMENTO, OBSERVACAO, FK_ID_FUNCIONARIO, FK_ID_USUARIO_CLIENTE)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            valores = (tipo_servico, data_atendimento, data_marcacao, status_agendamento, observacao, fk_id_funcionario, fk_id_usuario_cliente)
            cursor.execute(comando, valores)
            connection.commit()

        app.logger.info("Atendimento cadastrado com sucesso.")
        return jsonify({'message': 'Atendimento cadastrado com sucesso'}), 201
    except mysql.connector.Error as e:
        app.logger.error(f"Erro ao cadastrar atendimento: {e}")
        connection.rollback()
        return jsonify({'message': 'Falha ao cadastrar atendimento', 'error': str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()

@app.route('/MeusAtendimentos', methods=['GET'])
@cross_origin()
def get_meus_atendimentos():
    usuario_id = request.args.get('id_usuario')  # Obtém o ID do usuário logado a partir dos parâmetros da query
    if not usuario_id:
        app.logger.warning("ID de usuário não fornecido.")
        return jsonify({'message': 'ID de usuário não fornecido'}), 400

    connection = get_connection()
    if not connection:
        app.logger.error("Falha ao conectar ao banco de dados.")
        return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor(dictionary=True) as cursor:
            # Atualizando a consulta para buscar o nome do funcionário da tabela USUARIO
            query = '''
                SELECT 
                    A.ID_AGENDA, 
                    A.TIPO_SERVICO, 
                    DATE_FORMAT(A.DATA_ATENDIMENTO, '%Y-%m-%d %H:%i') AS DATA_ATENDIMENTO, 
                    A.STATUS_AGENDAMENTO,
                    U.NOME AS FUNCIONARIO  -- Buscando o nome do funcionário da tabela USUARIO
                FROM AGENDA A
                JOIN USUARIO U ON A.FK_ID_FUNCIONARIO = U.ID_USUARIO  -- Ligando a FK_ID_FUNCIONARIO com a tabela USUARIO
                WHERE A.FK_ID_USUARIO_CLIENTE = %s AND U.FUNCIONARIO = 1  -- Verificando se o usuário é funcionário
                ORDER BY A.DATA_ATENDIMENTO ASC
            '''
            cursor.execute(query, (usuario_id,))
            atendimentos = cursor.fetchall()

        if atendimentos:
            return jsonify(atendimentos)
        else:
            app.logger.info("Nenhum atendimento encontrado para o usuário.")
            return jsonify([])
    except Exception as e:
        app.logger.error(f"Erro ao buscar atendimentos: {e}")
        return jsonify({"message": "Erro ao buscar atendimentos", "error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()




@app.route('/Atendimento', methods=['GET'])
@cross_origin()
def get_atendimentos():
    try:
        connection = get_connection()
        if not connection:
            app.logger.error("Falha ao conectar ao banco de dados.")
            return jsonify({"message": "Falha ao conectar ao banco de dados"}), 500

        with connection.cursor(dictionary=True) as cursor:
            query = '''
                SELECT ID_AGENDA, FK_ID_USUARIO_CLIENTE, DATE_FORMAT(DATA_ATENDIMENTO, '%Y-%m-%dT%H:%i:%sZ') AS DATA_ATENDIMENTO
                FROM AGENDA
                WHERE STATUS_AGENDAMENTO = 'CADASTRADO'
            '''
            cursor.execute(query)
            atendimentos = cursor.fetchall()

        if atendimentos:
            return jsonify(atendimentos)
        else:
            app.logger.info("Nenhum atendimento encontrado.")
            return jsonify([])
    except Exception as e:
        app.logger.error(f"Erro ao buscar atendimentos: {e}")
        return jsonify({"message": "Erro ao processar a solicitação", "error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()


if __name__ == '__main__':
    app.run(debug=True)
