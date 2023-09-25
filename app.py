import mysql.connector

conexao = mysql.connector.connect(
    host= 'localhost',
    user= 'root',
    password='joojerablack',
    database='db_ponto',
)

cursor = conexao.cursor()

# CRUD

#CREATE 
nome = "Claudio Castro Ferrez"
usuario = "claudinho"
email = "claudinho@outlook.com"
senha = "1a2b3c4d"
comando = f'INSERT INTO cadastro (nome, usuario,email, senha) VALUES ("{nome}", "{usuario}", "{email}", "{senha}")'
cursor.execute(comando)
conexao.commit() # edita o banco


# READ
comando = f'SELECT * FROM cadastro'
cursor.execute(comando)
resultado = cursor.fetchall()
print (resultado)

# UPDATE
usuario_atual = "claudinho"
usuario_novo = "claudinhoferrez"
comando = f'UPDATE cadastro SET usuario = "{usuario_novo}" WHERE usuario = "{usuario_atual}"'
cursor.execute(comando)
conexao.commit()

# DELETE
usuario = "claudinhoferrez"
comando = f'DELETE FROM cadastro WHERE usuario = "{usuario}"'
cursor.execute(comando)
conexao.commit()

# DELETE
usuario = "claudinho"
comando =f'DELETE FROM controle_login WHERE l_usuario = "{usuario}"'
cursor.execute(comando)
conexao.commit()

cursor.close()
conexao.close()