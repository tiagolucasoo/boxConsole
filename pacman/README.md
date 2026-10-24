# 👻 Pac-Man em Python ᗧ•••
Desenvolvido para a disciplina de **Linguagem de Programação** do **IFPR Londrina** por **Tiago, Ana, Bianca, Vitor e Ágata**.
- Esse jogo roda diretamente no terminal e é uma recriação do clássico, trazendo movimentação fluida e inteligência artificial desafiadora, tudo implementado puramente em Python.

## 📋 Funcionalidades
### Implementação de estratégias: ###
Com base no jogo original, cada fantasma possui sua forma de perseguição.
- **Blinky (Vermelho):** Persegue o Pac-Man diretamente.
- **Pinky (Ciano):** Tenta antecipar o movimento posicionando-se à frente.
- **Inky (Verde):** Tenta cercar o jogador (lógica de flanqueamento).
- **Clyde (Magenta):** Persegue quando está longe, mas foge para o canto quando chega muito perto.
  
### Sistema de Dificuldade: ###
- **Fácil, Médio e Difícil**: Altera a velocidade do jogo e multiplicador de pontuação.
### Menus Interativos: ###
- Menu principal, Pausa, Resetar jogo e Mudança de Dificuldade durante a execução.
### Sistema de Pontuação e Tempo: ###
- Cronómetro em tempo real e cálculo de pontuação baseado nos pontos comidos.

## 🛠️ Pré-requisitos
Para executar este jogo, é necessário ter o **Python** instalado.
Além disso, o projeto depende das seguintes bibliotecas externas:
* `keyboard`: Para capturar as teclas pressionadas.
* `colorama`: Para as cores no terminal.
* `pyfiglet`: Para os títulos em ASCII art.

## 📦 Instalação
1.  Clone este repositório ou extraia os ficheiros.
   ```bash
   git clone https://www.github.com/tiagolucasoo/pacman.git
   ```
2.  Instale as dependências necessárias executando o comando abaixo no terminal:
   ```bash
   pip install keyboard colorama pyfiglet
   ```

## 🚀 Como Executar
Abra o terminal e dentro do diretório rode o arquivo main.py
  ```bash
  python main.py
  ```

## 🎮 Controle
### 🕹️ Movimentação
- **Cima** (W ou Seta Cima)
- **Baixo** (S ou Seta Baixo)
- **Esquerda** (A ou Seta Esquerda)
- **Direita** (D ou Seta Direita)
### ⚙️ Configuração
- **ESC:**	Pausar Jogo / Abrir Menu
- **Enter:**	Confirmar opções nos menus

## 📂 Estrutura do Projeto
- `main.py:` Ponto de entrada. Gerencia o loop principal, escolha de dificuldade e estados de fim de jogo (Vitória/Game Over).
- `game.py:` Contém a lógica do jogo, renderização do mapa, movimentação do Pac-Man e atualização dos fantasmas.
- `strategy.py:` Contém os algoritmos de comportamento para cada um dos fantasmas.
- `utilidades.py:` Funções auxiliares para interface (UI), cronômetro, limpeza de tela, manipulação de strings, etc...

  Projeto desenvolvido por:

## 👥 Autores
- [Tiago Lucas](https://github.com/tiagolucasoo)
- [Bianca Milani](https://github.com/bianncamilani)
- [Ana Beatriz](https://github.com/anacostt)
- Ágata Silverio
- Victor Ribeiro
