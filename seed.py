"""
Dados iniciais da base de dados (utilizadores e objetos de exemplo).

Os dados não são reais, mas foram escritos para parecerem reais, como pedem
as regras de avaliação. As coordenadas são aproximadas e correspondem à zona
do campus de Tomar (Quinta do Contador) — ajustem-nas se quiserem maior rigor.
"""

from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

# (nome, email, password, papel)
# Nota: estas contas são criadas diretamente na BD, por isso não passam pela
# regra "palavra-passe com pelo menos 6 caracteres" do registo.
UTILIZADORES = [
    ("Administrador", "admin@ipt.pt", "admin", "admin"),           # id 1
    ("Diogo Santos", "dfpds2005@gmail.com", "diogo", "utilizador"),  # id 2
    ("Gabriel Vital", "vital.gabriel2006@gmail.com", "gabriel", "utilizador"),  # id 3
]

# dono = id do utilizador (2 = Diogo, 3 = Gabriel)
# (dono, tipo, titulo, descricao, categoria, local, lat, lon, dias_atras, estado)
OBJETOS = [
    (2, "perdido", "Carteira castanha em pele",
     "Carteira castanha com cartão de cidadão, cartão de estudante e cartão multibanco. "
     "Perdi-a entre a cantina e o parque de estacionamento.",
     "Documentos", "Cantina", 39.59985, -8.39120, 1, "ativo"),
    (3, "achado", "Chaves com porta-chaves do Sporting",
     "Molho de três chaves com porta-chaves verde do Sporting. Estava em cima de uma "
     "mesa da biblioteca, no piso 1.",
     "Chaves", "Biblioteca, piso 1", 39.60012, -8.39065, 1, "ativo"),
    (2, "perdido", "Auriculares Bluetooth pretos",
     "Auriculares sem fios JBL pretos, dentro de uma caixa de carregamento com um "
     "autocolante azul. Devem ter ficado na sala depois da aula de DAM.",
     "Eletrónica", "Bloco O, sala O107", 39.60055, -8.39010, 2, "ativo"),
    (2, "achado", "Pen USB Kingston 32 GB",
     "Pen USB vermelha da Kingston esquecida num computador do laboratório de "
     "informática. Tem uma pasta chamada 'Projeto BD'.",
     "Eletrónica", "Bloco O, laboratório O120", 39.60061, -8.39002, 2, "ativo"),
    (3, "perdido", "Casaco de ganga azul",
     "Casaco de ganga azul-escuro, tamanho M, com um pin amarelo na gola. Ficou no "
     "cabide do bar da associação de estudantes.",
     "Roupa", "Bar da Associação de Estudantes", 39.59960, -8.39090, 3, "ativo"),
    (3, "achado", "Calculadora Casio fx-991",
     "Calculadora científica Casio com o nome 'R. Santos' escrito a caneta na tampa. "
     "Encontrada no anfiteatro depois do teste de Matemática.",
     "Material escolar", "Bloco B, anfiteatro B128", 39.59940, -8.39030, 4, "ativo"),
    (2, "achado", "Garrafa térmica cinzenta",
     "Garrafa térmica de inox cinzenta, 500 ml, com autocolantes de bandas. Estava no "
     "banco em frente à secretaria.",
     "Outros", "Serviços Académicos", 39.59975, -8.39150, 5, "ativo"),
    (3, "perdido", "Óculos graduados com armação preta",
     "Óculos graduados de armação preta retangular, dentro de um estojo rígido azul. "
     "Penso que os deixei na sala de estudo.",
     "Acessórios", "Biblioteca, sala de estudo", 39.60015, -8.39070, 6, "ativo"),
    (2, "achado", "Cartão de estudante",
     "Cartão de estudante em nome de 'Beatriz M.', do curso de Gestão. Entregue na "
     "portaria do bloco A.",
     "Documentos", "Bloco A, portaria", 39.59925, -8.39075, 7, "resolvido"),
    (2, "perdido", "Carregador de portátil Lenovo",
     "Carregador Lenovo de 65 W com ponta USB-C e uma fita de velcro vermelha no cabo. "
     "Ficou ligado numa tomada da sala.",
     "Eletrónica", "Bloco I, sala I184", 39.60035, -8.38960, 8, "ativo"),
    (3, "achado", "Guarda-chuva preto pequeno",
     "Guarda-chuva dobrável preto, com cabo de madeira. Esquecido à entrada da cantina "
     "num dia de chuva.",
     "Acessórios", "Cantina, entrada", 39.59988, -8.39112, 10, "ativo"),
    (3, "perdido", "Caderno A4 de capa verde",
     "Caderno A4 quadriculado de capa verde com apontamentos de Sistemas Operativos. "
     "Tem o meu nome na primeira página.",
     "Material escolar", "Bloco O, sala O105", 39.60050, -8.39015, 12, "resolvido"),
]


def inserir_dados_iniciais(bd):
    """Insere utilizadores e objetos de exemplo, apenas se a BD estiver vazia."""
    if bd.execute("SELECT COUNT(*) FROM utilizadores").fetchone()[0] > 0:
        return

    for nome, email, password, papel in UTILIZADORES:
        bd.execute(
            "INSERT INTO utilizadores (nome, email, password_hash, papel) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(password), papel),
        )

    hoje = date.today()
    agora = datetime.now()
    for (dono, tipo, titulo, descricao, categoria, local,
         lat, lon, dias_atras, estado) in OBJETOS:
        bd.execute(
            """INSERT INTO objetos (tipo, titulo, descricao, categoria, local, latitude,
                                    longitude, data_ocorrencia, estado, foto,
                                    utilizador_id, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
            (
                tipo, titulo, descricao, categoria, local, lat, lon,
                (hoje - timedelta(days=dias_atras)).isoformat(), estado, dono,
                (agora - timedelta(days=dias_atras)).isoformat(timespec="seconds"),
            ),
        )
