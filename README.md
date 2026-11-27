# Perdidos e Achados — API REST

API REST da aplicação Android **Perdidos e Achados**, trabalho prático de
Desenvolvimento de Aplicações Móveis (DAM 2026/27), Licenciatura em Engenharia Informática — IPT.

**Autores:** Diogo Santos (n.º 27223) e Gabriel Vital (n.º 27217)
**App Android:** https://github.com/DiogoSantos13/PerdidosAchados

Python + Flask + SQLite (um único ficheiro de base de dados, criado no primeiro arranque com dados de exemplo).

## Correr no computador

```bash
pip install -r requirements.txt
python app.py
```

Fica em `http://localhost:5000`. **A janela tem de ficar aberta** enquanto se usa a app.
No emulador Android a app usa `http://localhost:5000/`, depois de correr UMA vez `adb reverse tcp:5000 tcp:5000`
(ver o README da app). Alternativa: `http://10.0.2.2:5000/` (o computador visto pelo emulador).

Teste rápido no browser: http://localhost:5000/api/objetos deve mostrar a lista em JSON.

Para repor os dados iniciais: parar a API, apagar `perdidos_achados.db` e a pasta `fotos/`.

## Alojar online (Render, gratuito)

1. Em https://render.com: **New + → Blueprint** e escolher este repositório (usa o `render.yaml`).
2. No fim, o Render dá um endereço `https://perdidosachados-api.onrender.com`.
3. Na app, mudar `BASE_URL` em `retrofit/RetrofitInitializer.kt` para esse endereço (terminado em `/`).

Nota: no plano gratuito a base de dados SQLite é reposta quando o serviço reinicia,
e o primeiro pedido depois de um período parado pode demorar ~1 minuto.

## Contas iniciais

| Papel | E-mail | Palavra-passe |
|---|---|---|
| Administrador | admin@ipt.pt | admin |
| Utilizador | dfpds2005@gmail.com | diogo |
| Utilizador | vital.gabriel2006@gmail.com | gabriel |

## Endpoints

| Método | Caminho | Descrição | Acesso |
|---|---|---|---|
| POST | `/api/auth/registar` | Criar conta | livre |
| POST | `/api/auth/login` | Iniciar sessão (devolve um token JWT) | livre |
| POST | `/api/auth/logout` | Terminar sessão (invalida o token) | login |
| GET | `/api/objetos?tipo=&q=&estado=` | Listar/pesquisar objetos | livre |
| GET | `/api/objetos/meus` | Objetos do utilizador | login |
| GET | `/api/objetos/{id}` | Um objeto | livre |
| POST | `/api/objetos` | Publicar objeto | login |
| PUT | `/api/objetos/{id}` | Alterar objeto | dono ou admin |
| DELETE | `/api/objetos/{id}` | Eliminar objeto | dono ou admin |
| GET | `/api/fotos/{ficheiro}` | Fotografia | livre |

Autenticação: **JWT** (JSON Web Token) assinado, enviado no cabeçalho `Authorization: Bearer <token>`.
Os tokens expiram ao fim de 30 dias e são apagados no servidor ao terminar sessão. Erros devolvem sempre `{"erro": "mensagem"}`.

## Bibliotecas

- [Flask](https://flask.palletsprojects.com/) (BSD) e Werkzeug (hash das palavras-passe)
- [PyJWT](https://pyjwt.readthedocs.io/) (MIT) — criar e validar os tokens JWT
- [Gunicorn](https://gunicorn.org/) (MIT) — servidor para produção
