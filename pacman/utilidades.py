import pyfiglet 
from pyfiglet import Figlet 
from colorama import Fore, Back, Style, init 
import os
import time
import sys

init(autoreset=True)

f = Figlet()
fontes = f.getFonts()
uni = '\u1A27'
dificuldade_mapa = {"1": "facil", "2": "medio", "3": "dificil"}
dificuldade_view = {"1": "Fácil", "2": "Médio", "3": "Difícil"}

mapa_original = """
A ######################################################
B #............#............##.........................#
C #.#.##########.##########.##.##########.##########.#.#
D #.#.##########.##########.##.##########.##########.#.#
E #....................................................#
F #.#.##.##############.##########.##############.##.#.#
G #...##....##....###...##..##..##...###....##....##...#
H #...##....##....###...##..##..##...###....##....##...#
I #...##....##....###...##..##..##...###....##....##...#
J ######.##.##.###.##.##############.##.###.##.##.######
E #.........##.........................................#
K #.......####...........#******#.........#....#.......#
L #.......######.........#*8**7*#.........#....#.......#
M #.......#....#.........#*6**5*#.........######.......#
N #.......#....#.........########...........####.......#
O #.........................................##.........#
P ######.##.##.###.##.##.###########.##.###.##.##.######
Q #...##....##....###...##..##..##...###....##....##...#
R #...##....##....###...##..##..##...###....##....##...#
S #...##....##....###...##..##..##...###....##....##...#
T #.#.##.##########.###.##########.###.##########.##.#.#
U #.................#####........#####.................#
V #.......................#.+.#....................#...#
W #.#.##########.##########.#############.##########.#.#
X #.#.##########.##########.##.##########.##########.#.#
Y #............#............##.........................#
Z ######################################################
"""

def logo(texto: str, cor=Fore.YELLOW):
    ascii = pyfiglet.figlet_format(texto, font="slant")
    print(cor + ascii + Fore.RESET)

def descricao(texto: str, fonte="standard", cor=Fore.CYAN):
    print(cor + pyfiglet.figlet_format(texto, font=fonte) + Fore.RESET)

def descricao2(texto: str, cor=Fore.YELLOW) -> None:    
    print(cor + texto + Fore.RESET)

def infoAlunos() -> None:
    alunos = ["Tiago Lucas", "Bianca Milani", "Ana Beatriz", "Ágata Silverio", "Victor Ribeiro"]
    print(Fore.MAGENTA + "Desenvolvido por:" + Fore.RESET)
    for aluno in alunos:
        print(f" {uni} {aluno}")
    print()

def escolher_dificuldade():
    opcoes = {"1": "facil", "2": "medio", "3": "dificil"}
    while True:
        print("\nEscolha a dificuldade:")
        print("1. Fácil")
        print("2. Médio")
        print("3. Difícil")

        escolha = input("\nDigite o número da dificuldade desejada: ")
        if escolha in opcoes:
            return opcoes[escolha]
        else:
            print(Fore.RED + "Opção inválida. Tente novamente." + Fore.RESET)

def calcular_pontuacao(pontos: int, dificuldade:str) -> int:
    multiplicador = {"facil": 1, "medio": 1.5, "dificil": 2}
    return (pontos * multiplicador.get(dificuldade, 1))

def iniciar_cronometro() -> float:
    return time.time()

def tempo_passado(inicio: float) -> float:
    return round(time.time() - inicio, 1)

def limpar_tela():
    os.system('cls')

def loading(mensagem="Carregando", duracao=2, simbolo=".") -> None:
    print(Fore.YELLOW + mensagem, end="", flush=True)
    for _ in range(int(duracao * 3)):
        time.sleep(0.3)
        print(simbolo, end="", flush=True)
    print(Fore.RESET)
    time.sleep(0.5)
    limpar_tela()

def Game_Over():
    return logo("Game Over")

def Vitoria():
    return logo("Vitoria")

def iniciar_jogo():
    print("Hora de começar a jogar!")
    time.sleep(1)
    menu()

def fase_atual():
    print("O jogo continua.\n")

def menu():
    menu_texto = """
======== MENU ========
[1] - Pausar
[2] - Continuar
[3] - Resetar
[4] - Mudar a dificuldade
[5] - Sair
======================
"""
    print(menu_texto)

    opcoes_menu = {
        '1': pausar,
        '2': continuar,
        '3': resetar,
        '4': mudar_dificuldade,
        '5': sair
    }

    while True:
        escolha = input("Escolha uma opção do menu: ")

        if escolha == '1':
            opcoes_menu[escolha]()
            return 'continuar'
        
        elif escolha == '2':
            return opcoes_menu[escolha]()
        
        elif escolha == '3':
            return opcoes_menu[escolha]()
        
        elif escolha == '4':
            return opcoes_menu[escolha]()
        
        elif escolha == '5':
            opcoes_menu[escolha]()
            print(menu_texto)

        else:
            print("Opção inválida. Tente novamente.")

def pausar():
    print("\nJogo pausado. Aperte ENTER para continuar...")
    input()

def continuar():
    print("Retornando para fase... \n")
    return 'continuar'

def resetar():
    print("\nJogo resetado. Voltando ao início...") 
    time.sleep(1)
    return 'resetar'

def validacao_nome():
    while True: 
        usuario = input("Digite o seu nome de jogador(a): ")

        if not usuario:
            print("\nNenhum nome informado. Tente novamente.")

        elif len(usuario) < 3:
            print(f"\nO nome '{usuario}' é muito curto. Deve ter 3 ou mais caracteres.")
        
        else:
            print(f"\nBem vindo(a) '{usuario}'! Iniciando o Pacman, aguarde e tenha um bom jogo!")
            return usuario

dificuldade_type = """
______ Nível de Dificuldade ______

1. Fácil
2. Médio
3. Difícil
__________________________________
"""
def mudar_dificuldade():
    tipo_dificuldade = dificuldade_type
    print(tipo_dificuldade)

    while True:
        nivel = input("Informe o nº da dificuldade escolhida: ")

        if nivel in ['1', '2', '3']:
            print(f"\nA dificuldade foi alterada para {dificuldade_view[nivel]}")
            print("O jogo será resetado")
            time.sleep(1.5)

            return ('mudar', dificuldade_mapa[nivel])
        else:
            print("Opção indisponível. Tente novamente...")

def sair():
    while True:
        confirmacao = input("\nTem certeza que deseja sair? (S/N): ").strip().upper()

        if confirmacao == 'S':
            print("Você saiu do jogo. O seu progresso foi salvo.")
            print("Encerrando o programa...")
            sys.exit()

        elif confirmacao == 'N':
            print("Saída cancelada. Voltando ao menu principal.")
            menu()
            break

        else:
            print("Opção inválida. Use 'S' para Sim ou 'N' para Não.")

if __name__ == "__main__":
    limpar_tela()
    logo("PacMan in Python")
    descricao2("Bem-vindo!")
    infoAlunos()
    dificuldade = escolher_dificuldade()
    print(f"Sua dificuldade: {dificuldade}")
    loading("Iniciando o jogo")

