import os
import time
import keyboard
from colorama import Fore, Back, Style, init
import utilidades
from utilidades import mapa_original
import strategy

def pacman(usuario, dificuldade):
    init(autoreset=True)
    def limpar_tela():
        os.system('cls' if os.name == 'nt' else 'clear')

    def desenhar_mapa(matriz, substituicoes, fantasmas):
        """Desenha o mapa, aplicando fundos dinâmicos para os fantasmas."""
        # Cria um dicionário para acesso rápido à posição dos fantasmas
        posicoes_fantasmas = {(f['y'], f['x']): f for f in fantasmas}
        
        mapa_para_imprimir = ""
        for y, linha in enumerate(matriz):
            for x, char in enumerate(linha):
                if (y, x) in posicoes_fantasmas:
                    fantasma_atual = posicoes_fantasmas[(y, x)]
                    string_fantasma = substituicoes[fantasma_atual['char']]

                    if fantasma_atual['deixou_para_tras'] == '*':
                        mapa_para_imprimir += Back.WHITE + string_fantasma
                    else:
                        mapa_para_imprimir += Back.RESET + string_fantasma
                else:
                    mapa_para_imprimir += substituicoes.get(char, char)
            mapa_para_imprimir += '\n'
            
        print(mapa_para_imprimir, end="")

    def encontrar_todas_posicoes(matriz, char):
        """Encontra todas as ocorrências de um caractere na matriz e retorna uma lista de coordenadas."""
        posicoes = []
        for i, linha in enumerate(matriz):
            for j, celula in enumerate(linha):
                if celula == char:
                    posicoes.append({'y': i, 'x': j})
        return posicoes

    substituicoes_cores = {
        '#': Back.RESET + Fore.YELLOW + '\u2588',
        '.': Back.RESET + Fore.WHITE + '.',
        '+': Back.RESET + Fore.YELLOW + '\u1A27',
        '*': Back.WHITE + ' ',

        '8': Fore.RED + '\u03A9',
        '7': Fore.CYAN + '\u03A9',
        '6': Fore.GREEN + '\u03A9',
        '5': Fore.MAGENTA + '\u03A9',
    }

    mapa_string = mapa_original
    mapa_matriz = [list(linha) for linha in mapa_string.strip().split('\n')]

    pacman_y, pacman_x = -1, -1
    for i, linha in enumerate(mapa_matriz):
        if '+' in linha:
            pacman_y = i
            pacman_x = linha.index('+')
            break

    fantasmas = []
    codigos_fantasmas = ['8', '7', '6', '5']

    for codigo in codigos_fantasmas:
        posicoes = encontrar_todas_posicoes(mapa_matriz, codigo)
        for pos in posicoes:
            fantasmas.append({
                'y': pos['y'],
                'x': pos['x'],
                'char': codigo,
                'deixou_para_tras': '*'
            })

    inicio_tempo = utilidades.iniciar_cronometro()
    pontuacao = 0
    alimentos_restantes = 0

    for linha in mapa_matriz:
        alimentos_restantes += linha.count('.')

    if dificuldade == 'facil':
        velocidade_jogo = 0.15
    elif dificuldade == 'medio':
        velocidade_jogo = 0.10
    elif dificuldade == 'dificil':
        velocidade_jogo = 0.05
    else:
        velocidade_jogo = 0.10

    while True:
        limpar_tela()
        utilidades.logo("PacMan Py")
        tempo = utilidades.tempo_passado(inicio_tempo)

        print(f"Você está jogando no modo {dificuldade}")
        print("Para acessar o Menu aperte a tecla ESC")

        print(f"""\nUsuário: {usuario}          Tempo: {tempo}s         Pontuação: {pontuacao}
        """)

        desenhar_mapa(mapa_matriz, substituicoes_cores, fantasmas)

        time.sleep(velocidade_jogo)

        for fantasma in fantasmas:
            dy, dx = 0, 0
            pacman_atual_y, pacman_atual_x = pacman_y, pacman_x

            if fantasma['char'] == '8':
                dy, dx = strategy.fantasma_blinky(mapa_matriz, fantasma, pacman_atual_y, pacman_atual_x)
            
            elif fantasma['char'] == '7':
                dy, dx = strategy.fantasma_pinky(mapa_matriz, fantasma, pacman_atual_y, pacman_atual_x)

            elif fantasma['char'] == '6':
                dy, dx = strategy.fantasma_inky(mapa_matriz, fantasma, pacman_atual_y, pacman_atual_x)
            
            elif fantasma['char'] == '5':
                dy, dx = strategy.fantasma_clyde(mapa_matriz, fantasma, pacman_atual_y, pacman_atual_x)

            proximo_y, proximo_x = fantasma['y'] + dy, fantasma['x'] + dx

            # --- ADICIONE ESTA VERIFICAÇÃO ---
            if proximo_y == pacman_y and proximo_x == pacman_x:
                return ('game_over', pontuacao, tempo)
            # --- FIM DA ADIÇÃO ---

            # Verifica se a próxima posição é válida (não é uma parede)
            if mapa_matriz[proximo_y][proximo_x] not in ['#', '8', '7', '6', '5']:
                    mapa_matriz[fantasma['y']][fantasma['x']] = fantasma['deixou_para_tras']
                    fantasma['deixou_para_tras'] = mapa_matriz[proximo_y][proximo_x]
                    fantasma['y'], fantasma['x'] = proximo_y, proximo_x
                    mapa_matriz[fantasma['y']][fantasma['x']] = fantasma['char']

        # Posição futura, começa igual à atual
        proximo_y, proximo_x = pacman_y, pacman_x

        if keyboard.is_pressed('up') or keyboard.is_pressed('w'):
            proximo_y -= 1
        elif keyboard.is_pressed('down') or keyboard.is_pressed('s'):
            proximo_y += 1
        elif keyboard.is_pressed('left') or keyboard.is_pressed('a'):
            proximo_x -= 1
        elif keyboard.is_pressed('right') or keyboard.is_pressed('d'):
            proximo_x += 1
        elif keyboard.is_pressed('esc'):
            utilidades.limpar_tela()
            utilidades.logo("Jogo Pausado")

            acao = utilidades.menu()
            if acao == 'continuar':
                limpar_tela()
                pass

            elif acao == 'resetar':
                return 'resetar'
            
            elif isinstance(acao, tuple) and acao[0] == 'mudar':
                return acao


        # Verifica se a próxima posição é válida (não é uma parede '#')
        if mapa_matriz[proximo_y][proximo_x] != '#':

            destino = mapa_matriz[proximo_y][proximo_x]
            if destino == '.':
                pontuacao += 10
                alimentos_restantes -= 1

                if alimentos_restantes == 0:
                    return ('vitoria', pontuacao, tempo)

            if destino in ['8', '7', '6', '5']:
                return ('game_over', pontuacao, tempo)
            

            # Apaga o Pac-Man da posição antiga
            mapa_matriz[pacman_y][pacman_x] = ' '
            # Atualiza as coordenadas
            pacman_y, pacman_x = proximo_y, proximo_x
            # Coloca o Pac-Man na nova posição
            mapa_matriz[pacman_y][pacman_x] = '+'