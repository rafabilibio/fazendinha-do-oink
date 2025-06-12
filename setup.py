import pygame
import sys
import random
import math
import sqlite3
from datetime import datetime


pygame.init()

# --- Configurações ---
W, H = 800, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Fazendinha do Oink")

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 205, 50)
RED = (255, 0, 0)
GRAY = (50, 50, 50)
SEMI_BLACK = (0,0,0,180)

# Botão start
BTN_BG = (50, 205, 50)

# Fontes
try:
    FONT_PIXEL = pygame.font.Font('recursos/pixel_font.ttf', 24)
except:
    FONT_PIXEL = pygame.font.SysFont('Arial', 24)

FONT_BIG = pygame.font.SysFont('Arial', 48)
FONT_SMALL = pygame.font.SysFont('Arial', 20)

clock = pygame.time.Clock()
FPS = 60

# Música
try:
    pygame.mixer.music.load('recursos/musica_jogo_mp3.mp3')
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Erro ao carregar musica:", e)

# Banco de dados
conn = sqlite3.connect("partidas.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS partidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    hora_inicio TEXT,
    pontuacao INTEGER,
    tempo TEXT
)
""")
conn.commit()

# --- Variáveis do jogo ---
game_state = "tela_inicial"
nome = ""
input_active = False
input_rect = pygame.Rect(300, 400, 200, 40)
input_color_active = (0, 255, 0)
input_color_inactive = (100, 100, 100)
input_color = input_color_inactive

# Fundo inicial
try:
    tela_inicial_img = pygame.image.load('recursos/tela_inicial.jpeg').convert()
    tela_inicial_img = pygame.transform.scale(tela_inicial_img, (W,H))
except:
    tela_inicial_img = None

try:
    tela_fundo_img = pygame.image.load('recursos/tela_fundo.jpeg').convert()
    tela_fundo_img = pygame.transform.scale(tela_fundo_img, (W,H))
except:
    tela_fundo_img = None

# Frutas
frutas_nomes = ['maca', 'morango', 'tomate', 'uva']
frutas_imgs = {}
for f in frutas_nomes:
    try:
        img = pygame.image.load(f'recursos/{f}.png').convert_alpha()
        frutas_imgs[f] = pygame.transform.scale(img, (40, 40))
    except:
        frutas_imgs[f] = None

# Porco
try:
    porco_img = pygame.image.load('recursos/porco_andando.png').convert_alpha()
    porco_img = pygame.transform.scale(porco_img, (80, 80))
except:
    porco_img = None

# Variáveis do porco
porco_x, porco_y = W//2, H - 100
porco_speed = 7
porco_dir = 1  # 1 para direita, -1 para esquerda

# Vidas e pontuação
vidas = 5
pontuacao = 0
start_ticks = 0  # para tempo do jogo em segundos

# Frutas caindo
frutas_lista = []

# Dificuldade
dificuldade_timer = 0
frutas_vel_inicial = 1
frutas_vel_max = 5
frutas_vel = frutas_vel_inicial
frutas_max_qtd = 1

# Partículas fundo (pontos brancos)
particulas = []
for _ in range(30):
    x = random.randint(0, W)
    y = random.randint(0, H)
    size = random.randint(1,3)
    speed = random.uniform(0.1, 0.3)
    particulas.append([x,y,size,speed])

# Histórico das partidas (5 últimas)
def get_ultimas_partidas():
    cur.execute("SELECT nome, hora_inicio, pontuacao, tempo FROM partidas ORDER BY id DESC LIMIT 5")
    return cur.fetchall()

# Salvar partida
def salva(nome, hora_inicio, pontuacao, tempo):
    cur.execute("INSERT INTO partidas(nome, hora_inicio, pontuacao, tempo) VALUES (?,?,?,?)",
                (nome, hora_inicio, pontuacao, tempo))
    conn.commit()

# Desenhar coracao (vidas)
def desenha_coracao(surface, x, y):
    points = [(x,y+10), (x+5,y), (x+10,y+10), (x+5,y+15)]
    pygame.draw.polygon(surface, RED, points)
    pygame.draw.circle(surface, RED, (x+3,y+5), 4)
    pygame.draw.circle(surface, RED, (x+7,y+5), 4)

# Desenhar trofeu (pontuação)
def desenha_trofeu(surface, x, y):
    pygame.draw.rect(surface, (212,175,55), (x+2,y+8,6,8))  # base
    pygame.draw.rect(surface, (255,215,0), (x,y,y+12,y))  # corpo
    pygame.draw.polygon(surface, (255,215,0), [(x,y+8),(x+6,y+2),(x+12,y+8)])  # topo
    pygame.draw.rect(surface, (212,175,55), (x-1,y+5,14,2))  # barra topo

# Desenhar relogio (tempo)
def desenha_relogio(surface, x, y):
    pygame.draw.circle(surface, (0,0,0), (x+7,y+7), 7, 2)
    pygame.draw.line(surface, (0,0,0), (x+7,y+7), (x+7,y+3), 2)  # ponteiro horas
    pygame.draw.line(surface, (0,0,0), (x+7,y+7), (x+10,y+7), 2)  # ponteiro minutos

# Texto do manual discreto
manual_text = [
    "Use ← e → para mover o porco",
    "Pegue as frutas para ganhar pontos",
    "Não deixe as frutas passarem, perde vidas",
    "Pressione Espaço para pausar"
]

# Botão arredondado
def desenha_botao(surface, rect, texto, cor_bg, cor_texto, raio=20):
    pygame.draw.rect(surface, cor_bg, rect, border_radius=raio)
    text_surf = FONT_PIXEL.render(texto, True, cor_texto)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

# Função para desenhar partículas em movimento
def atualiza_particulas():
    for p in particulas:
        p[1] += p[3]
        if p[1] > H:
            p[0] = random.randint(0, W)
            p[1] = 0

def desenha_particulas():
    for p in particulas:
        pygame.draw.circle(screen, WHITE, (int(p[0]), int(p[1])), p[2])

# Frutas caindo e dificultando
def cria_frutas():
    global frutas_lista
    if len(frutas_lista) < frutas_max_qtd:
        f = random.choice(frutas_nomes)
        x = random.randint(40, W-40)
        frutas_lista.append([f, x, -40, frutas_vel])

def atualiza_frutas():
    global frutas_lista, vidas, pontuacao
    frutas_novas = []
    for fruta in frutas_lista:
        f, x, y, v = fruta
        y += v
        # Se pegou porco (colisão simples)
        porco_rect = pygame.Rect(porco_x, porco_y, 80, 80)
        fruta_rect = pygame.Rect(x, y, 40, 40)
        if fruta_rect.colliderect(porco_rect):
            pontuacao += 1
            # Som ou efeito ao pegar pode ser colocado aqui
        else:
            if y > H:
                vidas -= 1
            else:
                frutas_novas.append([f, x, y, v])
    frutas_lista = frutas_novas

# Desenha frutas na tela
def desenha_frutas():
    for f,x,y,v in frutas_lista:
        img = frutas_imgs.get(f)
        if img:
            screen.blit(img, (x,y))

# Atualiza dificuldade a cada 11 segundos
def atualiza_dificuldade(tempo):
    global frutas_vel, frutas_max_qtd
    intervalos = tempo // 11
    frutas_vel = min(frutas_vel_inicial + intervalos * 0.5, frutas_vel_max)
    frutas_max_qtd = min(1 + intervalos, 10)

# Desenhar vidas, pontuação e tempo
def desenha_status():
    # Corações
    x = 10
    y = 10
    for i in range(vidas):
        desenha_coracao(screen, x + i*30, y)

    # Troféu e pontuação
    desenha_trofeu(screen, 150, y)
    pts_text = FONT_PIXEL.render(str(pontuacao), True, WHITE)
    screen.blit(pts_text, (180, y))

    # Relógio e tempo
    desenha_relogio(screen, 250, y)
    tempo_decorrido = (pygame.time.get_ticks() - start_ticks) // 1000
    mins = tempo_decorrido // 60
    segs = tempo_decorrido % 60
    tempo_text = FONT_PIXEL.render(f"{mins:02d}:{segs:02d}", True, WHITE)
    screen.blit(tempo_text, (280, y))

# Desenha porco virado para a direção
def desenha_porco():
    if porco_img:
        img = porco_img
        if porco_dir == -1:
            img = pygame.transform.flip(porco_img, True, False)
        screen.blit(img, (porco_x, porco_y))
    else:
        pygame.draw.rect(screen, GREEN, (porco_x, porco_y, 80, 80))

# Tela pause ou game over: desenha tabela das últimas 5 partidas
def desenha_tabela_partidas(titulo):
    partidas = get_ultimas_partidas()
    tabela_largura = 600
    tabela_altura = 200
    tabela_x = (W - tabela_largura) // 2
    tabela_y = (H - tabela_altura) // 2

    # Fundo preto com bordas arredondadas
    s = pygame.Surface((tabela_largura, tabela_altura), pygame.SRCALPHA)
    s.fill((0,0,0,200))
    pygame.draw.rect(s, BLACK, s.get_rect(), border_radius=15)
    screen.blit(s, (tabela_x, tabela_y))

    # Título
    titulo_surf = FONT_BIG.render(titulo, True, WHITE)
    screen.blit(titulo_surf, (tabela_x + 20, tabela_y + 10))

    # Cabeçalho da tabela
    cabeçalho = ["Nome", "Hora", "Pontos", "Tempo"]
    col_x = [tabela_x + 20, tabela_x + 180, tabela_x + 380, tabela_x + 520]
    for i, txt in enumerate(cabeçalho):
        h_surf = FONT_PIXEL.render(txt, True, GREEN)
        screen.blit(h_surf, (col_x[i], tabela_y + 70))

    # Dados
    for idx, partida in enumerate(partidas):
        y = tabela_y + 100 + idx * 20
        for i, val in enumerate(partida):
            val_str = str(val)
            val_surf = FONT_PIXEL.render(val_str, True, WHITE)
            screen.blit(val_surf, (col_x[i], y))

# Mensagem pause com fundo preto e bordas arredondadas
def desenha_pause_msg():
    msg = "PAUSADO - Pressione Espaço para continuar"
    s = pygame.Surface((W//2, 50), pygame.SRCALPHA)
    s.fill((0,0,0,180))
    pygame.draw.rect(s, BLACK, s.get_rect(), border_radius=15)
    screen.blit(s, (W//4, H//2 - 25))

    texto_surf = FONT_PIXEL.render(msg, True, WHITE)
    texto_rect = texto_surf.get_rect(center=(W//2, H//2))
    screen.blit(texto_surf, texto_rect)

# Desenha manual discreto na tela inicial
def desenha_manual():
    for i, linha in enumerate(manual_text):
        txt_surf = FONT_SMALL.render(linha, True, WHITE)
        screen.blit(txt_surf, (10, H - 20*(len(manual_text) - i)))

# Variáveis para o botão start arredondado
btn_start_rect = pygame.Rect(W//2 - 100, 450, 200, 50)

# Variável para controlar pausa
paused = False

# Marca início do jogo
hr_inicio = None

# Loop principal
running = True
while running:
    dt = clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == "tela_inicial":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_start_rect.collidepoint(event.pos) and nome.strip() != "":
                    game_state = "jogando"
                    start_ticks = pygame.time.get_ticks()
                    hr_inicio = datetime.now()
                    pygame.mixer.music.play(-1)
                    vidas = 5
                    pontuacao = 0
                    frutas_lista.clear()
                    frutas_vel = frutas_vel_inicial
                    frutas_max_qtd = 1
                    dificuldade_timer = 0
                    paused = False
                if input_rect.collidepoint(event.pos):
                    input_active = True
                    input_color = input_color_active
                else:
                    input_active = False
                    input_color = input_color_inactive
            if event.type == pygame.KEYDOWN and input_active:
                if event.key == pygame.K_BACKSPACE:
                    nome = nome[:-1]
                elif len(nome) < 15:
                    nome += event.unicode

        elif game_state == "jogando":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                    if paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()

        elif game_state in ("game_over", "pause"):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = "tela_inicial"

    # Desenho e lógica por estado do jogo
    if game_state == "tela_inicial":
        if tela_inicial_img:
            screen.blit(tela_inicial_img, (0,0))
        else:
            screen.fill(BLACK)

        desenha_manual()

        # Caixa de input do nome
        pygame.draw.rect(screen, input_color, input_rect, 2)
        nome_surf = FONT_PIXEL.render(nome, True, WHITE)
        screen.blit(nome_surf, (input_rect.x + 5, input_rect.y + 8))

        # Botão start arredondado
        cor_btn = BTN_BG if nome.strip() != "" else GRAY
        desenha_botao(screen, btn_start_rect, "START", cor_btn, BLACK, 25)

    elif game_state == "jogando":
        if tela_fundo_img:
            screen.blit(tela_fundo_img, (0,0))
        else:
            screen.fill((0,100,0))

        atualiza_particulas()
        desenha_particulas()

        keys = pygame.key.get_pressed()
        if not paused:
            # Movimenta porco e atualiza direção
            if keys[pygame.K_LEFT]:
                porco_x -= porco_speed
                porco_dir = -1
            if keys[pygame.K_RIGHT]:
                porco_x += porco_speed
                porco_dir = 1

            porco_x = max(0, min(W-80, porco_x))

            # Atualiza frutas
            atualiza_frutas()
            cria_frutas()

            # Atualiza dificuldade pelo tempo
            tempo_jogo = (pygame.time.get_ticks() - start_ticks) // 1000
            atualiza_dificuldade(tempo_jogo)

            # Verifica vidas
            if vidas <= 0:
                game_state = "game_over"
                tempo_final = f"{tempo_jogo//60:02d}:{tempo_jogo%60:02d}"
                pygame.mixer.music.stop()
                salva(nome, hr_inicio.strftime("%Y-%m-%d %H:%M:%S"), pontuacao, tempo_final)

        desenha_frutas()
        desenha_porco()
        desenha_status()

        if paused:
            desenha_pause_msg()
            # Mostrar tabela das últimas 5 partidas no pause
            desenha_tabela_partidas("Últimas Partidas")

    elif game_state == "game_over":
        screen.fill(BLACK)
        texto_go = FONT_BIG.render("GAME OVER", True, RED)
        screen.blit(texto_go, (W//2 - texto_go.get_width()//2, H//4))

        texto_score = FONT_PIXEL.render(f"Pontuação: {pontuacao}", True, WHITE)
        screen.blit(texto_score, (W//2 - texto_score.get_width()//2, H//4 + 60))

        texto_instr = FONT_PIXEL.render("Pressione ENTER para voltar", True, GRAY)
        screen.blit(texto_instr, (W//2 - texto_instr.get_width()//2, H//4 + 120))

        desenha_tabela_partidas("Últimas Partidas")

    pygame.display.flip()

pygame.quit()
conn.close()
sys.exit()