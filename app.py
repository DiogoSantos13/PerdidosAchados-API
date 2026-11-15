"""
API REST da aplicação "Perdidos e Achados" (trabalho de DAM 2026/27).

Tecnologias: Python + Flask + SQLite (um único ficheiro de base de dados).
Todas as respostas são em JSON. Em caso de erro devolve-se sempre
    {"erro": "mensagem em português"}
com o código HTTP adequado (400, 401, 403, 404, 409...).

Endpoints:
    POST   /api/auth/registar      cria uma conta e devolve token
    POST   /api/auth/login         autentica e devolve token
    POST   /api/auth/logout        invalida o token atual
    GET    /api/objetos            lista objetos (filtros: tipo, q, estado)
    GET    /api/objetos/meus       lista os objetos do utilizador autenticado
    GET    /api/objetos/<id>       devolve um objeto
    POST   /api/objetos            cria um objeto            (requer login)
    PUT    /api/objetos/<id>       altera um objeto          (dono ou admin)
    DELETE /api/objetos/<id>       elimina um objeto         (dono ou admin)
    GET    /api/fotos/<ficheiro>   devolve a fotografia de um objeto

Autenticação: cabeçalho HTTP  "Authorization: Bearer <token>".

Para correr localmente:
    pip install flask
    python app.py
"""

import base64
import binascii
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from seed import inserir_dados_iniciais

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
FICHEIRO_BD = os.path.join(PASTA_BASE, "perdidos_achados.db")
PASTA_FOTOS = os.path.join(PASTA_BASE, "fotos")

TIPOS_VALIDOS = ("perdido", "achado")
ESTADOS_VALIDOS = ("ativo", "resolvido")
CATEGORIAS_VALIDAS = (
    "Eletrónica", "Documentos", "Chaves", "Roupa",
    "Material escolar", "Acessórios", "Outros",
)
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# um token deixa de ser válido ao fim deste tempo (obriga a novo login)
VALIDADE_SESSAO = timedelta(days=30)

app = Flask(__name__)
# limita o tamanho dos pedidos (as fotografias chegam em Base64 dentro do JSON)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
# devolve os acentos tal e qual, em vez de é
app.json.ensure_ascii = False


# ----------------------------------------------------------------------------
# Base de dados
# ----------------------------------------------------------------------------
def obter_bd():
    """Devolve a ligação à BD associada ao pedido atual (abre-a se necessário)."""
    if "bd" not in g:
        g.bd = sqlite3.connect(FICHEIRO_BD)
        g.bd.row_factory = sqlite3.Row
        g.bd.execute("PRAGMA foreign_keys = ON")
    return g.bd


@app.teardown_appcontext
def fechar_bd(_erro):
    """Fecha a ligação à BD no fim de cada pedido."""
    bd = g.pop("bd", None)
    if bd is not None:
        bd.close()


def criar_tabelas():
    """Cria as tabelas (se não existirem) e insere os dados iniciais."""
    os.makedirs(PASTA_FOTOS, exist_ok=True)
    bd = sqlite3.connect(FICHEIRO_BD)
    bd.executescript(
        """
        CREATE TABLE IF NOT EXISTS utilizadores (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            papel         TEXT NOT NULL DEFAULT 'utilizador'   -- 'utilizador' ou 'admin'
        );

        CREATE TABLE IF NOT EXISTS sessoes (
            token         TEXT PRIMARY KEY,
            utilizador_id INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
            criado_em     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS objetos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT NOT NULL,      -- 'perdido' ou 'achado'
            titulo          TEXT NOT NULL,
            descricao       TEXT NOT NULL,
            categoria       TEXT NOT NULL,
            local           TEXT NOT NULL,      -- descrição textual do local
            latitude        REAL,               -- coordenadas GPS (opcionais)
            longitude       REAL,
            data_ocorrencia TEXT NOT NULL,      -- AAAA-MM-DD
            estado          TEXT NOT NULL DEFAULT 'ativo',
            foto            TEXT,               -- nome do ficheiro em /fotos
            utilizador_id   INTEGER NOT NULL REFERENCES utilizadores(id) ON DELETE CASCADE,
            criado_em       TEXT NOT NULL
        );
        """
    )
    inserir_dados_iniciais(bd)
    bd.commit()
    bd.close()


# ----------------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------------
def erro(mensagem, codigo):
    """Constrói uma resposta de erro uniforme."""
    return jsonify({"erro": mensagem}), codigo


def token_do_pedido():
    """Devolve o token enviado no cabeçalho Authorization (ou None)."""
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    return cabecalho[len("Bearer "):].strip() or None


def utilizador_autenticado():
    """Devolve o utilizador dono do token enviado no pedido, ou None.

    Tokens com mais de VALIDADE_SESSAO são recusados (sessão expirada).
    """
    token = token_do_pedido()
    if token is None:
        return None
    limite = (datetime.now() - VALIDADE_SESSAO).isoformat(timespec="seconds")
    return obter_bd().execute(
        """SELECT u.* FROM utilizadores u
           JOIN sessoes s ON s.utilizador_id = u.id
           WHERE s.token = ? AND s.criado_em >= ?""",
        (token, limite),
    ).fetchone()


def utilizador_para_json(u):
    return {"id": u["id"], "nome": u["nome"], "email": u["email"], "papel": u["papel"]}


def objeto_para_json(linha, com_contacto):
    """Converte uma linha da BD em JSON.

    O e-mail de contacto do autor só é devolvido a utilizadores autenticados
    (controlo de acesso aos dados pessoais).
    """
    return {
        "id": linha["id"],
        "tipo": linha["tipo"],
        "titulo": linha["titulo"],
        "descricao": linha["descricao"],
        "categoria": linha["categoria"],
        "local": linha["local"],
        "latitude": linha["latitude"],
        "longitude": linha["longitude"],
        "data_ocorrencia": linha["data_ocorrencia"],
        "estado": linha["estado"],
        "foto_url": f"api/fotos/{linha['foto']}" if linha["foto"] else None,
        "utilizador_id": linha["utilizador_id"],
        "utilizador_nome": linha["utilizador_nome"],
        "contacto": linha["utilizador_email"] if com_contacto else None,
        "criado_em": linha["criado_em"],
    }


SQL_OBJETOS = """
    SELECT o.*, u.nome AS utilizador_nome, u.email AS utilizador_email
    FROM objetos o JOIN utilizadores u ON u.id = o.utilizador_id
"""


def criar_sessao(utilizador_id):
    """Gera um token aleatório e regista-o na tabela de sessões."""
    token = secrets.token_hex(32)
    obter_bd().execute(
        "INSERT INTO sessoes (token, utilizador_id, criado_em) VALUES (?, ?, ?)",
        (token, utilizador_id, datetime.now().isoformat(timespec="seconds")),
    )
    return token


def validar_objeto(dados, parcial):
    """Valida os campos de um objeto.

    parcial=False -> criação (todos os campos obrigatórios têm de existir)
    parcial=True  -> edição (só se validam os campos enviados)
    Devolve (campos_validos, mensagem_de_erro).
    """
    campos = {}

    def texto(nome, minimo, maximo, etiqueta):
        if nome not in dados:
            return f"O campo '{etiqueta}' é obrigatório." if not parcial else None
        valor = str(dados[nome] or "").strip()
        if len(valor) < minimo or len(valor) > maximo:
            return f"O campo '{etiqueta}' deve ter entre {minimo} e {maximo} caracteres."
        campos[nome] = valor
        return None

    for args in (
        ("titulo", 3, 60, "título"),
        ("descricao", 10, 500, "descrição"),
        ("local", 3, 100, "local"),
    ):
        mensagem = texto(*args)
        if mensagem:
            return None, mensagem

    if "tipo" in dados or not parcial:
        if dados.get("tipo") not in TIPOS_VALIDOS:
            return None, "O tipo deve ser 'perdido' ou 'achado'."
        campos["tipo"] = dados["tipo"]

    if "categoria" in dados or not parcial:
        if dados.get("categoria") not in CATEGORIAS_VALIDAS:
            return None, "Categoria inválida."
        campos["categoria"] = dados["categoria"]

    if "estado" in dados:
        if dados["estado"] not in ESTADOS_VALIDOS:
            return None, "O estado deve ser 'ativo' ou 'resolvido'."
        campos["estado"] = dados["estado"]

    if "data_ocorrencia" in dados or not parcial:
        try:
            dia = date.fromisoformat(str(dados.get("data_ocorrencia")))
        except ValueError:
            return None, "A data deve ter o formato AAAA-MM-DD."
        if dia > date.today():
            return None, "A data não pode ser no futuro."
        campos["data_ocorrencia"] = dia.isoformat()

    # as coordenadas são opcionais, mas têm de vir as duas e ser válidas
    if dados.get("remover_localizacao") is True:
        # pedido explícito para apagar as coordenadas (usado na edição)
        campos["latitude"], campos["longitude"] = None, None
    elif "latitude" in dados or "longitude" in dados:
        lat, lon = dados.get("latitude"), dados.get("longitude")
        if lat is None and lon is None:
            campos["latitude"], campos["longitude"] = None, None
        else:
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                return None, "Coordenadas GPS inválidas."
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return None, "Coordenadas GPS inválidas."
            campos["latitude"], campos["longitude"] = lat, lon

    return campos, None


def guardar_foto(foto_base64):
    """Grava em disco uma fotografia JPEG recebida em Base64.

    Devolve (nome_do_ficheiro, mensagem_de_erro).
    """
    try:
        conteudo = base64.b64decode(foto_base64, validate=True)
    except (binascii.Error, ValueError):
        return None, "A fotografia enviada não é válida."
    # todos os ficheiros JPEG começam pelos bytes FF D8
    if not conteudo.startswith(b"\xff\xd8"):
        return None, "A fotografia tem de estar em formato JPEG."
    nome = secrets.token_hex(12) + ".jpg"
    with open(os.path.join(PASTA_FOTOS, nome), "wb") as ficheiro:
        ficheiro.write(conteudo)
    return nome, None


def apagar_foto(nome):
    """Remove do disco a fotografia de um objeto (se existir)."""
    if nome:
        caminho = os.path.join(PASTA_FOTOS, nome)
        if os.path.exists(caminho):
            os.remove(caminho)


# ----------------------------------------------------------------------------
# Autenticação
# ----------------------------------------------------------------------------
@app.post("/api/auth/registar")
def registar():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome") or "").strip()
    email = str(dados.get("email") or "").strip().lower()
    password = str(dados.get("password") or "")

    if len(nome) < 3 or len(nome) > 60:
        return erro("O nome deve ter entre 3 e 60 caracteres.", 400)
    if not REGEX_EMAIL.match(email):
        return erro("O e-mail não é válido.", 400)
    if len(password) < 6:
        return erro("A palavra-passe deve ter pelo menos 6 caracteres.", 400)

    bd = obter_bd()
    if bd.execute("SELECT 1 FROM utilizadores WHERE email = ?", (email,)).fetchone():
        return erro("Já existe uma conta com este e-mail.", 409)

    cursor = bd.execute(
        "INSERT INTO utilizadores (nome, email, password_hash) VALUES (?, ?, ?)",
        (nome, email, generate_password_hash(password)),
    )
    token = criar_sessao(cursor.lastrowid)
    bd.commit()
    utilizador = bd.execute(
        "SELECT * FROM utilizadores WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify({"token": token, "utilizador": utilizador_para_json(utilizador)}), 201


@app.post("/api/auth/login")
def login():
    dados = request.get_json(silent=True) or {}
    email = str(dados.get("email") or "").strip().lower()
    password = str(dados.get("password") or "")

    bd = obter_bd()
    utilizador = bd.execute(
        "SELECT * FROM utilizadores WHERE email = ?", (email,)
    ).fetchone()
    if utilizador is None or not check_password_hash(utilizador["password_hash"], password):
        return erro("E-mail ou palavra-passe incorretos.", 401)

    token = criar_sessao(utilizador["id"])
    bd.commit()
    return jsonify({"token": token, "utilizador": utilizador_para_json(utilizador)})


@app.post("/api/auth/logout")
def logout():
    """Termina a sessão no servidor: o token deixa de funcionar."""
    token = token_do_pedido()
    if token is None:
        return erro("É necessário iniciar sessão.", 401)
    bd = obter_bd()
    bd.execute("DELETE FROM sessoes WHERE token = ?", (token,))
    bd.commit()
    return jsonify({"code": "200", "description": "Sessão terminada."})


# ----------------------------------------------------------------------------
# Objetos perdidos e achados
# ----------------------------------------------------------------------------
@app.get("/api/objetos")
def listar_objetos():
    """Lista objetos, do mais recente para o mais antigo.

    Parâmetros opcionais: tipo (perdido|achado), estado (ativo|resolvido),
    q (texto a procurar no título, descrição ou local).
    """
    condicoes, valores = [], []
    tipo = request.args.get("tipo")
    if tipo:
        if tipo not in TIPOS_VALIDOS:
            return erro("O tipo deve ser 'perdido' ou 'achado'.", 400)
        condicoes.append("o.tipo = ?")
        valores.append(tipo)
    estado = request.args.get("estado")
    if estado:
        if estado not in ESTADOS_VALIDOS:
            return erro("O estado deve ser 'ativo' ou 'resolvido'.", 400)
        condicoes.append("o.estado = ?")
        valores.append(estado)
    pesquisa = (request.args.get("q") or "").strip()
    if pesquisa:
        condicoes.append("(o.titulo LIKE ? OR o.descricao LIKE ? OR o.local LIKE ?)")
        valores += [f"%{pesquisa}%"] * 3

    sql = SQL_OBJETOS
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY o.criado_em DESC, o.id DESC"

    com_contacto = utilizador_autenticado() is not None
    linhas = obter_bd().execute(sql, valores).fetchall()
    return jsonify([objeto_para_json(l, com_contacto) for l in linhas])


@app.get("/api/objetos/meus")
def listar_meus_objetos():
    utilizador = utilizador_autenticado()
    if utilizador is None:
        return erro("É necessário iniciar sessão.", 401)
    linhas = obter_bd().execute(
        SQL_OBJETOS + " WHERE o.utilizador_id = ? ORDER BY o.criado_em DESC, o.id DESC",
        (utilizador["id"],),
    ).fetchall()
    return jsonify([objeto_para_json(l, True) for l in linhas])


def procurar_objeto(objeto_id):
    return obter_bd().execute(SQL_OBJETOS + " WHERE o.id = ?", (objeto_id,)).fetchone()


@app.get("/api/objetos/<int:objeto_id>")
def obter_objeto(objeto_id):
    linha = procurar_objeto(objeto_id)
    if linha is None:
        return erro("Objeto não encontrado.", 404)
    return jsonify(objeto_para_json(linha, utilizador_autenticado() is not None))


@app.post("/api/objetos")
def criar_objeto():
    utilizador = utilizador_autenticado()
    if utilizador is None:
        return erro("É necessário iniciar sessão para publicar.", 401)

    dados = request.get_json(silent=True) or {}
    campos, mensagem = validar_objeto(dados, parcial=False)
    if mensagem:
        return erro(mensagem, 400)

    foto = None
    if dados.get("foto_base64"):
        foto, mensagem = guardar_foto(dados["foto_base64"])
        if mensagem:
            return erro(mensagem, 400)

    bd = obter_bd()
    cursor = bd.execute(
        """INSERT INTO objetos (tipo, titulo, descricao, categoria, local, latitude,
                                longitude, data_ocorrencia, estado, foto,
                                utilizador_id, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ativo', ?, ?, ?)""",
        (
            campos["tipo"], campos["titulo"], campos["descricao"], campos["categoria"],
            campos["local"], campos.get("latitude"), campos.get("longitude"),
            campos["data_ocorrencia"], foto, utilizador["id"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    bd.commit()
    return jsonify(objeto_para_json(procurar_objeto(cursor.lastrowid), True)), 201


def verificar_permissao(objeto_id):
    """Confirma que o pedido vem do dono do objeto ou de um administrador.

    Devolve (utilizador, linha_do_objeto, resposta_de_erro).
    """
    utilizador = utilizador_autenticado()
    if utilizador is None:
        return None, None, erro("É necessário iniciar sessão.", 401)
    linha = procurar_objeto(objeto_id)
    if linha is None:
        return None, None, erro("Objeto não encontrado.", 404)
    if linha["utilizador_id"] != utilizador["id"] and utilizador["papel"] != "admin":
        return None, None, erro("Não tem permissão para alterar este objeto.", 403)
    return utilizador, linha, None


@app.put("/api/objetos/<int:objeto_id>")
def alterar_objeto(objeto_id):
    _utilizador, linha, resposta = verificar_permissao(objeto_id)
    if resposta:
        return resposta

    dados = request.get_json(silent=True) or {}
    campos, mensagem = validar_objeto(dados, parcial=True)
    if mensagem:
        return erro(mensagem, 400)

    if dados.get("foto_base64"):
        foto, mensagem = guardar_foto(dados["foto_base64"])
        if mensagem:
            return erro(mensagem, 400)
        apagar_foto(linha["foto"])       # substitui a fotografia antiga
        campos["foto"] = foto

    if campos:
        atribuicoes = ", ".join(f"{nome} = ?" for nome in campos)
        bd = obter_bd()
        bd.execute(
            f"UPDATE objetos SET {atribuicoes} WHERE id = ?",
            list(campos.values()) + [objeto_id],
        )
        bd.commit()
    return jsonify(objeto_para_json(procurar_objeto(objeto_id), True))


@app.delete("/api/objetos/<int:objeto_id>")
def eliminar_objeto(objeto_id):
    _utilizador, linha, resposta = verificar_permissao(objeto_id)
    if resposta:
        return resposta
    bd = obter_bd()
    bd.execute("DELETE FROM objetos WHERE id = ?", (objeto_id,))
    bd.commit()
    apagar_foto(linha["foto"])
    return jsonify({"code": "200", "description": "Objeto eliminado."})


@app.get("/api/fotos/<path:ficheiro>")
def obter_foto(ficheiro):
    return send_from_directory(PASTA_FOTOS, ficheiro)


# ----------------------------------------------------------------------------
# Erros genéricos, também em JSON
# ----------------------------------------------------------------------------
@app.errorhandler(404)
def nao_encontrado(_e):
    return erro("Recurso não encontrado.", 404)


@app.errorhandler(405)
def metodo_nao_permitido(_e):
    return erro("Método não permitido.", 405)


@app.errorhandler(413)
def demasiado_grande(_e):
    return erro("A fotografia é demasiado grande.", 413)


@app.errorhandler(500)
def erro_interno(_e):
    return erro("Erro interno do servidor.", 500)


# as tabelas são criadas quando o módulo é carregado (python app.py ou WSGI)
criar_tabelas()

if __name__ == "__main__":
    # 0.0.0.0 para ser acessível a partir do emulador (10.0.2.2) e da rede local
    app.run(host="0.0.0.0", port=5000, debug=False)
