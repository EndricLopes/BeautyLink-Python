from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS, cross_origin
from werkzeug.security import ( generate_password_hash, check_password_hash )
import re
from datetime import datetime,timedelta, time
import os
import pytz

app = Flask(__name__)
CORS(app, origins=['https://beauty-link-react.vercel.app/' ], supports_credentials=True)

# Configuração do banco de dados
# Configuração do banco de dados
conexao = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database='BEAUTY_LINK'
)


@app.route('/', methods=['GET'])
@cross_origin()
def home():
    return "Hello, World!"


@app.route('/Cadastro', methods=['GET'])
@cross_origin()
def get_usuarios():
    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM USUARIO')
    usuarios = cursor.fetchall()
    cursor.close()
    return jsonify(usuarios)



@app.route('/Usuarios', methods=['GET'])
@cross_origin()
def get_usuario(id):
    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM USUARIO WHERE id = %s', (id,))
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
        cursor.execute("SELECT * FROM USUARIO WHERE LOGIN=%s OR EMAIL=%s", (usuario, email))
        account = cursor.fetchone()
        if account:
            return jsonify({'message' : 'Usuário ou email já existem.'}), 400

        add_user = ("INSERT INTO USUARIO "
                   "(NOME, LOGIN, EMAIL, SENHA) "
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

#COMENTARIO

@app.route('/Login', methods=['POST'])
@cross_origin()
def login():
    dados = request.get_json()
    usuario = dados['usuario']
    senha = dados['senha']

    cursor = conexao.cursor(dictionary=True)
    cursor.execute('SELECT * FROM USUARIO WHERE LOGIN = %s', (usuario,))
    usuario_existente = cursor.fetchone()
    cursor.close()

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

    # Verificar se todos os campos necessários foram fornecidos
    if not all([tipo_servico, data_atendimento, data_marcacao, status_agendamento, fk_id_funcionario, fk_id_usuario_cliente]):
        return jsonify({'message': 'Todos os campos são obrigatórios'}), 400

    # Obter a hora atual
    fuso = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso)

    cursor = conexao.cursor(dictionary=True)

    try:
        comando = '''
            INSERT INTO AGENDA (TIPO_SERVICO, DATA_ATENDIMENTO, DATA_MARCACAO, STATUS_AGENDAMENTO, OBSERVACAO, FK_ID_FUNCIONARIO, FK_ID_USUARIO_CLIENTE)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        valores = (tipo_servico, data_atendimento, data_marcacao, status_agendamento, observacao, fk_id_funcionario, fk_id_usuario_cliente)

        cursor.execute(comando, valores)
        conexao.commit()

        return jsonify({'message': 'Atendimento cadastrado com sucesso'}), 201

    except Exception as e:
        print("Falha ao cadastrar atendimento: ", e)
        conexao.rollback()
        return jsonify({'message': 'Falha ao cadastrar atendimento'}), 500


@app.route('/Atendimento')
def get_atendimentos():
    usuario = request.args.get('usuario')  # Obtemos o tipo de serviço da query string
    cursor = conexao.cursor(dictionary=True)
    query = '''
        SELECT DATA_ATENDIMENTO
        FROM AGENDA
        WHERE FK_ID_USUARIO = %s AND STATUS_AGENDAMENTO = 'CADASTRADO'
    '''
    cursor.execute(query, (usuario,))
    atendimentos = cursor.fetchall()
    cursor.close()

    if atendimentos:
        return jsonify(atendimentos)
    else:
        return jsonify([])  # Retorna uma lista vazia se nenhum atendimento for encontrado




from flask import request

@app.route('/Espelho', methods=['GET'])
@cross_origin()
def get_horas_trabalhadas():
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')

    cursor = conexao.cursor(dictionary=True)
    cursor.execute(f"SELECT SEC_TO_TIME(SUM(TIME_TO_SEC(TIMEDIFF(hora_saida3, hora_entrada3)))) AS 'Horas Extras no Mês' FROM controle_ponto WHERE fk_id_login_ponto = 27 AND dia BETWEEN '{inicio}' AND '{fim}';")
    Horas_extra = cursor.fetchall()[0]['Horas Extras no Mês']

    cursor.execute(f"SELECT hora_entrada1, hora_saida2, dia FROM controle_ponto WHERE fk_id_login_ponto = 26 AND dia BETWEEN '{inicio}' AND '{fim}';")    
    results = cursor.fetchall()

    response = []
    for result in results:
        Hora_entrada = result['hora_entrada1']
        Hora_saida = result['hora_saida2']
        Dia = result['dia']

        cursor.execute(f"SELECT SEC_TO_TIME(SUM(IF(hora_saida1 < hora_entrada1, TIME_TO_SEC(TIMEDIFF(hora_saida1 + INTERVAL 24 HOUR, hora_entrada1)), TIME_TO_SEC(TIMEDIFF(hora_saida1, hora_entrada1))) +IF(hora_saida2 < hora_entrada2, TIME_TO_SEC(TIMEDIFF(hora_saida2 + INTERVAL 24 HOUR, hora_entrada2)), TIME_TO_SEC(TIMEDIFF(hora_saida2, hora_entrada2)))) - 6*60*60) AS 'Saldo Diário'FROM  controle_ponto WHERE fk_id_login_ponto = 26 AND dia = '{Dia}';")    
        saldo = cursor.fetchall()[0]['Saldo Diário']

        if saldo is not None:
            saldo_str = str(saldo.total_seconds())
        else:
            saldo_str = 'N/A'

        response.append({**{'Saldo Diário': saldo_str}, **{'Horario entrada': str(Hora_entrada)}, **{'Horario saida': str(Hora_saida)}, **{'Data': str(Dia)}, **{'Horas extra': str(Horas_extra)}})

    return jsonify(response)

    result = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    data = [
        dict(zip(col_names, row))
        for row in result
    ]

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)


