# Imagens e capas dos jogos

Coloque aqui uma imagem para cada jogo do BoxConsole. O menu usa o `id` de
cada jogo (veja a lista `GAMES` em `../console_ui.py`). Enquanto a imagem não
existir, o espaço fica em branco e mostra apenas uma dica discreta do caminho.

## Nomes dos arquivos

| Jogo | Arquivo sugerido |
|------|------------------|
| Doom in PyGame | `doom.png` |
| Flappy Bird | `flappy.png` |
| Pac-Man | `pacman.png` |
| Street Fighter | `street.png` |
| Super Mario | `mario.png` |
| PyZelda RPG | `zelda.png` |
| Tetris | `tetris.png` |
| Aliens | `aliens.png` |
| Sudoku | `sudoku.png` |
| Snake Eater | `snake.png` |
| Pong | `pong.png` |
| Breakout | `breakout.png` |
| 2048 | `game2048.png` ou `2048.png` |
| Bomberman | `bomberman.png` |
| Speed Racer | `speed.png` ou `corrida.png` |
| Donkey King | `donkeyking.png` |

## Formatos e tamanho

- Formatos aceitos: `.png`, `.jpg`, `.jpeg`, `.jfif`, `.webp`, `.bmp`.
- Nomes alternativos aceitos: `2048.png` para o jogo `game2048`,
  `pac-man.*` para `pacman`, `pingpong.*` para `pong` e `corrida.*` para
  `speed`.
- Recomendado: **16:9**, por exemplo **640×360** ou **960×540**.
- A imagem é ajustada **inteira**, sem cortes. Se a proporção não for 16:9,
  aparecem faixas discretas na cor do painel (vertical ou horizontal).
- Não é preciso redimensionar manualmente.
- Para trocar uma capa, basta substituir o arquivo e reiniciar o BoxConsole.
