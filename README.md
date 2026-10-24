# BoxConsole — Jogos Arcade

Launcher de jogos com **menu principal em Pygame** (capas, carrossel e fichas
detalhadas) e **menu de terminal** como modo secundário/reserva. Os dois usam o
mesmo catálogo de jogos, então tudo que existe em um aparece no outro.

Ao iniciar, o BoxConsole tenta abrir o menu Pygame em tela cheia. Se o Pygame
não estiver instalado ou a tela falhar, ele abre automaticamente o menu de
terminal — nada deixa de funcionar.

## Estrutura do projeto

```text
games/      todos os jogos
sounds/     os três efeitos do menu
images/     capas e imagens
```

O código aceita os caminhos antigos como fallback, mas a organização nova é a
recomendada.

## Otimizações para o H3 / ARMv7

- O menu só redesenha quando há evento; parado, fica praticamente em 0% de CPU.
- Textos, capas, moldura do jogo e frames do menu são cacheados.
- Escalas de tela reaproveitam a superfície de destino (sem alocar por frame).
- Jogos pesados ganharam perfis próprios: Doom em 640×360/240 raios, Zelda em
  960×540 a 30 FPS, Street Fighter em 960×540 a 30 FPS sem blur por frame.
- `scipy`, `opencv-python`, `numpy`, `keyboard` e `pyfiglet` não são mais
  necessários.
- Recordes ficam em `~/.local/share/boxconsole/`, fora do repositório.
- O `boxconsole.sh` usa o Pygame do sistema e cai no terminal se ele faltar.

## Iniciar

Windows:

```bat
BoxConsole.bat
```

ou:

```bat
python main.py
```

Linux / TV box:

```bash
sudo apt install python3-colorama python3-pygame
bash boxconsole.sh
```

O `boxconsole.sh` **não instala Pygame à força** e não cria mais um ambiente
virtual cheio de pacotes pesados. Ele usa o Python do sistema (ou
`BOXCONSOLE_PYTHON`/`VIRTUAL_ENV`, se definidos) e abre o menu gráfico quando o
Pygame existe; sem Pygame, cai automaticamente no menu de terminal. No Debian e
no Ubuntu ARM, `python3-pygame` é bem mais leve e confiável que compilar o
Pygame pelo `pip`.

Também dá para rodar direto:

```bash
python3 main.py
```

Opções úteis:

```bash
python main.py              # menu Pygame em tela cheia
python main.py --windowed   # menu Pygame em janela (bom para testar)
python main.py --terminal   # força o menu de terminal
```

No menu Pygame, use `F11` para alternar entre tela cheia e janela. No menu de
terminal do Windows, a janela é maximizada automaticamente; para desativar,
mude `FULLSCREEN = False` no topo de `console_ui.py`.

No Linux, o `boxconsole.sh` inicia tudo do jeito certo:

```bash
bash boxconsole.sh
```

O menu, as setas e o OK funcionam normalmente. A maximização automática do
terminal é exclusiva do Windows, então no Linux/TV box use `F11` no terminal
(ou o `F11` do próprio menu Pygame).

## Dependências no Linux

O BoxConsole precisa apenas de **Pygame** (menu gráfico e jogos) e **colorama**
(menu de terminal). As dependências pesadas antigas — `numpy`, `scipy`,
`opencv-python`, `keyboard` e `pyfiglet` — foram removidas do projeto.

```bash
sudo apt install python3-colorama python3-pygame
```

No Windows:

```bash
python -m pip install -r requirements.txt
```

Observações:

- O **Pac-Man** agora lê o teclado pelo próprio terminal (termios/select no
  Linux e msvcrt no Windows), sem `keyboard` e sem `sudo`.
- O **Street Fighter** não usa mais OpenCV/NumPy: o fundo desfocado é calculado
  uma única vez com o próprio Pygame.
- O **Super Mario** não usa mais SciPy: o desfoque do menu de pausa usa
  `pygame.transform.smoothscale`.
- Os recordes do **Tetris** e do **Speed Racer** ficam em
  `~/.local/share/boxconsole/` (Linux) ou `%APPDATA%\boxconsole` (Windows), fora
  do repositório.

## Controles

### Menu Pygame (principal)

| Tela | Teclas |
|------|--------|
| Menu | `← →` ou `↑ ↓` (ou `W S`) navegar · `Enter`/OK abrir detalhes · `J` jogar direto · `D` diagnóstico · `F11` tela cheia/janela · `ESC`/`Backspace`/`Q` sair |
| Detalhes | `← →` escolher botão · `Enter`/OK confirmar · `J` jogar · `R` repositório · `ESC`/`Backspace` voltar |
| Diagnóstico | `ESC`/`Backspace`/`Enter` voltar |

O menu também aceita **mouse** (passar o mouse pelas capas muda a seleção;
clique abre a ficha ou os botões) e **controle/gamepad** (D-pad, analógico e
botões A/B). Os números `1` a `9` abrem a ficha do jogo correspondente; `0`
abre o 10º.

### Menu de terminal (secundário)

| Tela | Teclas |
|------|--------|
| Menu | `↑ ↓` ou `W S` navegar · `Enter`/OK abrir detalhes · `J` jogar direto · `D` diagnóstico · `Q`/`ESC` sair |
| Detalhes | `← →` escolher botão · `Enter`/OK confirmar · `J` jogar · `R` repositório · `V`/`ESC` voltar |
| Diagnóstico | `V`/`ESC`/`Enter` voltar |

Nas telas de detalhes dos dois menus há três botões navegáveis: **JOGAR**,
**REPOSITÓRIO** e **VOLTAR**. Use as setas e o OK — funciona bem com controle
remoto.

Os números `1` a `9` abrem diretamente a ficha do jogo correspondente; `0` abre
o 10º jogo (Snake Eater). Os jogos 11 a 15 são acessados pelo menu. Em um
controle remoto de TV box, as setas e o OK costumam funcionar direto; o botão
voltar envia `ESC` ou `Backspace`.

## Sons do menu

O menu Pygame usa três efeitos opcionais:

```text
sounds/sound-hover.mp3   # ao passar entre os jogos
sounds/sound-click.mp3   # ao abrir a ficha de um jogo
sounds/sound-return.mp3  # ao encerrar o programa geral
```

Também são aceitos `.ogg`, `.wav` e `.flac`, com os nomes `hover.*`,
`click.*` (ou `select.*`) e `return.*`, em `sounds/` (a raiz antiga ainda é
aceita como fallback).

- O som de hover toca quando a seleção muda: setas, roda do mouse, movimento
  do mouse sobre as capas, controle ou gamepad.
- O som de seleção toca ao abrir a ficha do jogo. Ao iniciar um jogo, os sons
  do menu são interrompidos para não se misturarem com o áudio do jogo.
- O som de return toca apenas ao fechar o BoxConsole pelo menu (`ESC`,
  `Backspace`, `Q`, botão B do controle ou fechar a janela). O efeito termina
  antes de o programa fechar; voltar de uma ficha para o menu não toca esse
  som.
- Se os arquivos não existirem ou o dispositivo de áudio falhar, o menu
  continua funcionando normalmente, em silêncio.
- Para ajustar o volume, edite `HOVER_VOLUME`, `SELECT_VOLUME` e
  `RETURN_VOLUME` no topo de `pygame_ui.py`.

## Capas do menu Pygame

As capas ficam em `images/`, usando o `id` do jogo:

```text
images/doom.png
images/mario.png
images/bomberman.png
...
```

- Formatos: `.png`, `.jpg`, `.jpeg`, `.jfif`, `.webp` e `.bmp`.
- Tamanho recomendado: **16:9**, como **640×360** ou **960×540**.
- Nomes alternativos aceitos: `2048.png` (para `game2048`), `pac-man.*`
  (para `pacman`), `pingpong.*` (para `pong`) e `corrida.*` (para `speed`).
- Enquanto a imagem não existir, o espaço fica **em branco**, com uma dica
  discreta do caminho do arquivo.
- A imagem é ajustada **inteira**, sem cortes; proporções diferentes de 16:9
  ganham faixas discretas na cor do painel.
- Veja a lista completa em `images/README.md`.

## Jogos incluídos

| # | Jogo | Entrada | Dependências |
|---|------|---------|--------------|
| 1 | Doom in PyGame | `games/Doom-PyGame/main.py` | pygame |
| 2 | Flappy Bird | `games/flappy-bird/main.py` | pygame |
| 3 | Pac-Man | `games/pacman/main.py` | colorama |
| 4 | Street Fighter | `games/Street_Fighter/src/main.py` | pygame |
| 5 | Super Mario | `games/super-mario-python/main.py` | pygame |
| 6 | PyZelda RPG | `games/pyzelda-rpg/code/main.py` | pygame |
| 7 | Tetris | `games/tetris-pygame/Tetris.py` | pygame |
| 8 | Aliens | `pygame.examples.aliens` | pygame |
| 9 | Sudoku | `games/sudoku/main.py` | pygame |
| 10 | Snake Eater | `games/snake-pygame/Snake Game.py` | pygame |
| 11 | Pong | `games/pong/main.py` | pygame |
| 12 | Breakout | `games/breakout/main.py` | pygame |
| 13 | 2048 | `games/2048/main.py` | pygame |
| 14 | Bomberman | `games/bomberman/main.py` | pygame |
| 15 | Speed Racer | `games/SPEED-RACER/Speed Racer.py` | pygame |

O jogo 8 já vem embutido no próprio Pygame (exemplo oficial), então não precisa
de pasta: o BoxConsole roda `python -m pygame.examples.aliens`.

O **Sudoku** foi criado para o BoxConsole: gera tabuleiros aleatórios com
solução única, tem três dificuldades, cronômetro, destaque de erros e dicas.

O **Snake Eater** recebeu pequenos ajustes: a comida nunca nasce sobre a cobra,
a cabeça foi destacada, o jogo pausa com `P`/`Espaço`, e ao perder dá para
reiniciar com `R` em vez de fechar sozinho.

**Pong**, **Breakout**, **2048** e **Bomberman** também foram criados para o
BoxConsole, com foco em teclado e controle remoto: Pong tem CPU, Breakout tem
3 vidas, 2048 inclui desfazer o último movimento e Bomberman tem bombas em
cadeia, tijolos destrutíveis e melhorias de bomba e alcance.

O **Speed Racer** é um jogo de corrida de Keerat Sachdeva: desvie dos carros,
colecione combustível e tente bater o recorde de distância.

O BoxConsole inicia cada jogo na pasta correta e volta ao menu quando o jogo é
fechado. No menu de terminal, quando a lista fica grande demais para a altura
da tela, o logo grande é trocado automaticamente por um cabeçalho compacto.

## Jogos dentro do frame (modo embutido)

A maioria dos jogos Pygame roda **dentro da própria janela do BoxConsole**, na
área central do menu, como se fosse um frame de console. O jogo não abre outra
janela: o `pygame.display` dele é redirecionado para uma superfície virtual, e
o BoxConsole desenha essa superfície no frame, redimensionando sem cortar.

- **F12** volta ao menu a qualquer momento. O botão **VOLTAR (F12)**, no canto
  inferior direito, faz a mesma coisa e pode ser clicado com o mouse.
- Teclado, mouse e controle continuam funcionando normalmente. As coordenadas
  do mouse são convertidas para a área do jogo.
- O jogo usa o menu/teclas de saída dele normalmente; ao terminar, o BoxConsole
  volta sozinho para o menu.
- **Pac-Man** é um jogo de terminal e abre em um console próprio, como antes.
- Se algum jogo não conseguir rodar embutido, o BoxConsole tenta
  automaticamente o modo externo, sem travar o launcher.

Para o modo embutido funcionar, o jogo precisa desenhar em Pygame e não pode
usar OpenGL. Jogos de terminal ou que abrem janelas de outras bibliotecas
continuam no modo externo.

## Adicionar os detalhes dos repositórios

Abra `console_ui.py` e edite a lista `GAMES`. Cada jogo tem os campos:

```python
"repo": "https://github.com/usuario/projeto",
"site": None,                 # link opcional de play/download
"autor": "Nome do autor",
"licenca": "MIT",
```

Quando `repo` for `None`, a ficha mostra **“a ser adicionado”** e o botão `R`
explica onde preencher. Basta colocar a URL para o botão passar a abrir o
repositório no navegador.

Para jogos sem repositório externo existe o campo opcional
`"repo_texto": "*Jogo Próprio"`: a ficha mostra esse texto e o botão de
repositório apenas avisa que não há link.

Jogos que não são Pygame, ou que precisam abrir uma janela/console próprio,
podem usar `"embed": False`. Eles continuam funcionando pelo modo externo. Sem
esse campo, jogos Pygame entram automaticamente no frame.

Todos os jogos têm repositório cadastrado ou indicação de autoria; o Super
Mario aponta para `mx0c/super-mario-python`, e Sudoku, Pong, Breakout, 2048 e
Bomberman aparecem como **Jogo Próprio**.

## Dependências do launcher

O `boxconsole.sh` já cria o ambiente isolado e instala `colorama` e `pygame`
(necessários para abrir o launcher) quando necessário. As dependências
completas dos 15 jogos estão em `requirements.txt`. No Debian/Ubuntu/TV box,
os pacotes equivalentes são:

```bash
sudo apt install python3-colorama python3-pygame
```

Evite `python -m pip install` no Python do sistema em distribuições com PEP 668.

O `colorama` também é usado pelo menu de terminal de reserva. Sem o Pygame, o
BoxConsole continua abrindo no terminal.

## Créditos

**BoxConsole — 2026 — desenvolvido por Tiago Lucas Oliveira (IFPR Londrina).**

Projeto open source: <https://github.com/tiagolucasoo/boxConsole>

Os jogos de terceiros mantêm seus autores, licenças e repositórios nas
respectivas fichas dentro do launcher.
