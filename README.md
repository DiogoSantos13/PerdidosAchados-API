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

1. Em https://render.com criar conta (pode ser com o GitHub ou com um email).
2. **New + → Blueprint** e escolher este repositório (usa o `render.yaml`). Se o Render não listar o
   repositório, usar **New + → Web Service → Public Git Repository** e colar o endereço do repositório;
   *Build Command* `pip install -r requirements.txt` e *Start Command* `gunicorn app:app --bind 0.0.0.0:$PORT`.
3. No fim, o Render dá um endereço `https://<nome>.onrender.com`. Confirmar em
   `https://<nome>.onrender.com/api/objetos` que aparece a lista em JSON.
4. Na app, mudar `BASE_URL` em `retrofit/RetrofitInitializer.kt` para esse endereço (terminado em `/`).
5. Em *Environment* do serviço deve existir `JWT_SEGREDO` (o `render.yaml` gera-o automaticamente);
   é com ele que se assinam os tokens de autenticação.

Notas sobre o plano gratuito:
- A base de dados SQLite e as fotografias ficam no disco do serviço, que é reposto quando este reinicia:
  voltam os dados de exemplo e perdem-se as contas e os objetos criados entretanto.
- Depois de ~15 minutos sem pedidos o serviço adormece e o primeiro pedido pode demorar cerca de 1 minuto
  (a app já espera até 60 segundos). Convém abrir o endereço no browser pouco antes de uma demonstração.

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
