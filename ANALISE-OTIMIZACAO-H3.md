# BoxConsole em Allwinner H3 — análise geral de otimização

> **Nota histórica:** este documento registra uma análise anterior. Várias
> referências de linha, dependências e números de FPS já mudaram. A fonte atual
> é o `README.md` e o `requirements.txt`; em especial, `numpy`, `scipy`,
> `opencv-python`, `keyboard` e `pyfiglet` não fazem mais parte das
> dependências, e o `colorama` é opcional.

**Alvo:** TV box Allwinner H3 (4× Cortex-A7 ARMv7, Mali-400 MP2), Linux, **1 GB de RAM**, **8 GB de armazenamento**, saída de vídeo típica em 720p/1080p.

**Resumo:** o projeto já recebeu otimizações importantes (canvas fixo, escala nearest, cache de capas, cache do frame do jogo, mixer mono, fallback para terminal). O que ainda pesa não é o armazenamento — é **CPU e RAM**. Os maiores ganhos restantes estão em quatro frentes:

1. **Menu:** ele redesenha a tela inteira 30 vezes por segundo, mesmo parado, e renderiza dezenas de textos por frame.
2. **Jogos embutidos:** alguns rodam em resolução/FPS altos demais para o H3 (Zelda a 1280×720/120 FPS, Street Fighter com blur OpenCV a cada frame, Doom com raycasting em Python).
3. **Dependências:** `scipy`, `opencv-python` e `keyboard` custam RAM, espaço, instalação e compatibilidade ARMv7 — e são usados em pontos pequenos.
4. **Sistema operacional:** sem desktop, com zram, kiosk e montagem com `noatime`, o mesmo hardware fica bem mais estável.

A ordem recomendada é: **medir → otimizar o menu → criar perfis por jogo → remover dependências pesadas → ajustar o Linux → validar por 30 minutos e por 10 ciclos de jogo.**

---

## 1. Metas práticas para este hardware

| Métrica | Meta |
|---|---|
| Menu parado | < 5% de CPU, sem redesenhar quando não há evento |
| Navegação no menu | 30 FPS estáveis (≤ 33 ms por frame) |
| RAM do launcher | < 200 MB |
| RAM por jogo | < 500 MB (ideal < 350 MB) |
| Volta do jogo ao menu | < 2 s |
| Boot até o menu | < 25 s |
| Temperatura após 30 min | < 75 °C (com dissipador) |
| Espaço livre | > 1 GB (mínimo 15% do cartão/eMMC) |
| Ciclos de jogo | 10 aberturas/fechamentos sem crescimento de RAM |

> Em 1 GB, o sistema + desktop + launcher + jogo competem pelo mesmo espaço. Um desktop XFCE consome 300–500 MB; um Armbian/DietPi em modo console consome ~100–150 MB. Só essa escolha muda bastante o resultado.

---

## 2. O que já está bom (não mexer sem medir)

- `pygame_ui.py`: canvas fixo em 1280×720 e escala nearest no `present()` (linhas 239–253 e 417–432).
- Cache de capas por `(id, tamanho)` (`get_cover`, linhas 458–485).
- Cache do “chrome” do frame do jogo (`draw_game_frame`, linhas 630–651).
- Overlay escuro reaproveitado (`get_dim`, linhas 858–863).
- `game_host.py`: teto de 60 FPS e suporte a `max_frames` (linhas 282–295), útil para testes.
- Mixer em mono com buffer maior (linha 188), decisão correta para ARM antigo.
- Fallback automático para o menu de terminal (`main.py`, linhas 66–90).
- Flappy Bird já evita `smoothscale` de tela cheia (`flappy-bird/main.py`, linhas 27–48).
- Doom já foi reduzido para 960×540/30 FPS (`Doom-PyGame/settings.py`, linhas 4–10).

Essas decisões devem ser preservadas. O problema é o que ainda é feito **por frame** ou **em resolução nativa**.

---

## 3. Diagnóstico por camada

### 3.1 Launcher Pygame — maior ganho com menor risco

**Problemas encontrados:**

1. **Redesenho contínuo a 30 FPS**  
   `Launcher.run()` chama `draw()` e `clock.tick(30)` sempre (`pygame_ui.py`, linhas 1492–1498). O menu não tem animação contínua; ele só muda quando há evento. Isso mantém a CPU ocupada à toa e esquenta o H3.

2. **Texto renderizado a cada frame**  
   `draw_text()` chama `font.render()` sempre (linhas 115–119). Em uma tela de menu são dezenas de renders por frame: título, gênero, status, descrição, controles, 6 cartões, dicas, crédito. Em um Cortex-A7 isso custa caro, principalmente com fontes grandes.

3. **Tela de detalhes redesenha o menu inteiro**  
   `draw_details()` chama `draw_menu()` (linha 867) e depois joga o overlay por cima. O mesmo acontece em `draw_system()` (linha 1060). Ou seja: a tela de fundo é reconstruída inteira para ficar coberta.

4. **`find_spec` por frame**  
   `draw_details()` e `draw_system()` chamam `catalog.module_available(dep)` para cada dependência em cada frame (linhas 960, 1135). `find_spec` varre o `sys.path`; não é gratuito.

5. **`wrap_text()` e `ellipsize()` por frame**  
   Fazem várias chamadas de `font.size()` para medir texto (linhas 122–145). A descrição e os títulos não mudam entre frames.

6. **Escala de tela cheia no `present()`**  
   Se a tela real não for exatamente 1280×720 (por exemplo, 1920×1080), o `present()` escala o canvas inteiro com `pygame.transform.scale` a cada frame (linhas 424–431). Em jogo embutido isso acontece a cada frame do jogo.

7. **Carregamento de capa sob demanda**  
   A primeira seleção de cada jogo carrega e redimensiona a imagem (`get_cover`), causando engasgo na navegação.

**O que fazer (em ordem):**

- **Renderização sob demanda (dirty flag):** manter um `self.dirty`; desenhar apenas quando a seleção, o modo, o mouse, o toast ou a janela mudarem. Quando ocioso, usar `pygame.event.wait(timeout)` ou `clock.tick(5)` sem redesenhar. Isso derruba o consumo parado para quase zero.
- **Cache de texto:** um dicionário `(texto, tamanho, cor, bold, antialias)` → `Surface`. Para textos que mudam (placar, mensagens), cache com limite ou invalidação.
- **Cache de quadro do menu:** renderizar a tela do menu uma vez por jogo selecionado e reutilizar; invalidar ao trocar seleção, abrir modal, redimensionar ou tocar em som. Guardar só o atual e os vizinhos para não estourar RAM.
- **Não redesenhar o menu sob os modais:** guardar o último frame do menu e desenhar o modal sobre uma cópia; ou renderizar o modal direto sobre o frame cacheado.
- **Cachear `module_available()`:** dicionário nome → bool, recalculado apenas no diagnóstico `D` ou ao abrir detalhes.
- **Pré-computar textos:** quebrar descrições e medir títulos no início; guardar as linhas já prontas.
- **Pré-carregar capas em segundo plano:** carregar as 15 capas em 640×360 no início (≈ 10–15 MB) e gerar as miniaturas; evita engasgo. Se a RAM apertar, carregar só a atual e as duas vizinhas.
- **Fonte embutida:** usar `pygame.font.Font` com um `.ttf` do projeto (DejaVuSans) em vez de `SysFont`. Evita depender de fontconfig e dá métricas iguais em qualquer TV box.

**Impacto esperado:** menu parado praticamente sem CPU; navegação muito mais fluida; menos aquecimento. É a fase de melhor relação ganho/risco.

**Sobre a resolução do menu:** com renderização sob demanda, não é necessário baixar o menu para 960×540. O custo de desenhar 1280×720 só ocorre quando algo muda. O problema de escala no `present()` continua apenas durante o jogo embutido; aí vale tratar no perfil do jogo ou tentar fixar a saída em 720p.

---

### 3.2 Jogos embutidos — onde o H3 realmente sofre

O `game_host` limita o host a 60 FPS, mas **não limita o FPS interno do jogo** nem a resolução que ele escolhe. Alguns jogos pedem mais do que o H3 entrega.

| Jogo | Situação atual | Alvo sugerido no H3 | Motivo |
|---|---|---|---|
| **PyZelda** | 1280×720 a **120 FPS** (`pyzelda-rpg/code/settings.py`, linhas 4–6) | 960×540 a 30 FPS | 4× menos frames e elimina downscale por frame. É o caso mais grave. |
| **Street Fighter** | resolução nativa (até 1080p), 60 FPS, `cv2.GaussianBlur` **a cada frame** no menu (`Street_Fighter/src/main.py`, 95–110 e 155) | 960×540, 30 FPS, fundo desfocado calculado **uma vez** | Blur + conversão + `make_surface` + scale por frame é inviável em ARMv7. |
| **Doom** | 960×540, 30 FPS, 480 raios (`Doom-PyGame/settings.py`, 28) | 640×360, 20–30 FPS, 240–320 raios | Raycasting em Python escala com número de raios e pixels. |
| **Speed Racer** | 1200×700 a 60 FPS (`SPEED-RACER/Speed Racer.py`, 9–13) | 960×540 a 30 FPS | Reduz pixels e frames; evita downscale no host. |
| **Super Mario** | 640×480 a 60 FPS; `scipy` no pause (`classes/GaussianBlur.py`) | 640×480 a 30–60 FPS, sem `scipy` | O jogo em si é leve; o problema é a dependência. |
| **Tetris** | `clock.tick()` sem limite (`tetris-pygame/Tetris.py`, 400) | 30 FPS | O host corta em 60; 30 é suficiente e reduz CPU. |
| **Bomberman** | 800×600 a 60 FPS | 800×600 a 30 FPS | 30 FPS é suficiente para o gênero. |
| **Pong / Breakout** | 800×600 a 60 FPS | 800×600 a 30 FPS | Idem. |
| **Flappy** | 288×512, mas o jogo escala para 960×540 e o host escala de novo | 288×512 nativo; host escala uma vez | Evita uma segunda escala desnecessária. |
| **Snake** | 720×480, 15–120 FPS conforme dificuldade | Como está | Leve. |
| **Sudoku / 2048** | 30 FPS | Como está | Leves. |
| **Aliens** | 60 FPS | 30 FPS | Exemplo do Pygame; 30 basta. |
| **Pac-Man** | terminal, `keyboard` + `pyfiglet` | terminal, input sem root | Baixo CPU; o problema é a dependência `keyboard`. |

**Ações centrais:**

- **Perfil por jogo no catálogo:** adicionar campos como `"perfil": {"res": (960, 540), "fps": 30, "embed": True}` em `console_ui.GAMES` e aplicar no `game_host` e/ou no próprio jogo.
- **Limitar o FPS do jogo no host:** além do teto de 60 do host, oferecer um teto global de 30 FPS no perfil H3. Cuidado: jogos com passo fixo (sem delta time) ficam mais lentos; testar caso a caso. Jogos com `dt` continuam corretos.
- **Limitar a resolução no `_set_mode`** apenas para jogos que usam o tamanho retornado por `set_mode`. Jogos com constantes fixas (Zelda, Speed Racer) precisam de ajuste no próprio código.
- **Evitar renders duplicados:** alguns jogos chamam `pygame.display.update()` e `flip()` no mesmo frame; o host renderiza duas vezes. Guardar o timestamp do último render e ignorar chamadas dentro de ~16 ms.
- **Coletar lixo ao sair do jogo:** `gc.collect()` e liberar `virtual_surface` no `uninstall()`. Em 1 GB, fragmentação após vários jogos pode custar caro.
- **Modo externo para jogos pesados:** Doom, Zelda, Street Fighter e Speed Racer podem rodar em processo separado (como o Pac-Man já faz). Isso isola memória e crashes, permite resolução própria e evita que um jogo derrube o launcher. O custo é perder o “frame” bonito. Uma abordagem híbrida (leves embutidos, pesados externos) é a mais segura para 1 GB.
- **Flappy:** fazer o `_set_mode((0,0), FULLSCREEN)` devolver o tamanho nativo do jogo, não 960×540, para o host fazer a única escala.

**Impacto esperado:** os jogos que hoje provavelmente travam ou ficam em 5–10 FPS passam a ser jogáveis; o menu deixa de ser afetado pelo jogo.

---

### 3.3 Dependências — RAM, espaço e compatibilidade ARMv7

O `requirements.txt` atual puxa:

- `pygame` — necessário.
- `colorama` — necessário só para o menu de terminal; é pequeno.
- `keyboard` — usado só pelo Pac-Man; no Linux costuma exigir **root** ou regra de udev.
- `pyfiglet` — usado só para o logo ASCII do Pac-Man.
- `numpy` + `opencv-python` — usados só pelo Street Fighter.
- `scipy` — usado só pelo desfoque do pause do Super Mario.

**Custo:** `opencv-python` + `numpy` + `scipy` ocupam centenas de MB, demoram para instalar/compilar em ARMv7 e aumentam o tempo de import. Em 8 GB até cabem, mas competem com o sistema e com o cache.

**Substituições recomendadas:**

- **Street Fighter:** carregar o fundo com `pygame.image.load`, gerar a versão desfocada **uma vez** no início (ou usar um asset já desfocado, pré-gerado no PC) e escalar uma vez. Remove `cv2` e `numpy`.
- **Super Mario:** trocar `scipy.ndimage.gaussian_filter` por um desfoque simples com `pygame.transform.smoothscale` (reduzir e aumentar) ou por um asset pré-desfocado. Remove `scipy`.
- **Pac-Man:** trocar `keyboard` por leitura de `termios`/`select` ou `curses` (sem root); trocar `pyfiglet` por um logo ASCII pré-renderizado em arquivo. Remove as duas dependências.
- **Resultado:** o `requirements.txt` pode ficar em **pygame + colorama**. Isso simplifica o `boxconsole.sh`, elimina compilação no ARMv7 e libera RAM/espaço.

**Observação:** `scipy.ndimage.filters` foi removido/descontinuado em versões novas do SciPy; remover a dependência também evita uma quebra futura.

**Script de instalação:** o `boxconsole.sh` ainda tenta `pip install pygame` se não encontrar o Pygame no ambiente isolado. Em ARMv7 isso pode tentar compilar e falhar (ou baixar uma versão incompatível). O ideal é o script **não instalar Pygame automaticamente**: verificar `python3-pygame` do apt, explicar o comando e, se faltar, abrir o menu de terminal. Também vale evitar o venv quando não for mais necessário (sem `keyboard`, o projeto pode rodar direto no Python do sistema).

---

### 3.4 Assets e armazenamento — 8 GB é bastante, mas dá para trocar espaço por CPU

O armazenamento não é o gargalo principal, mas há ganhos fáceis e alguns riscos de desgaste:

- **Capas:** manter apenas uma pasta (`covers/` ou `imagens/`), em **640×360 WebP/JPEG** (qualidade 80). Hoje há imagens em `imagens/` e a pasta `covers/` só tem README. Gerar miniaturas de 156×88 junto evita `smoothscale` no launcher.
- **Pré-computar o que o H3 não deve calcular:** fundo desfocado do Street Fighter, logo ASCII do Pac-Man, capas redimensionadas, talvez sprites já escalados. Com 8 GB, trocar CPU por armazenamento é uma boa estratégia.
- **Áudio:** converter WAVs longos para OGG mono 64–96 kbps; manter WAVs curtos de efeito em 22050 Hz mono. Evita decode de MP3 a cada efeito do menu.
- **Limpeza:** remover `__pycache__`/`.pyc` de versões antigas (há cache de 3.11, 3.13 e 3.15), `patch-performance.zip` se já foi aplicado, screenshots de README e arquivos de teste. Isso reduz espaço e confusão.
- **Dados de jogo:** `Tetris` grava `highscore.txt` na pasta do jogo e `Speed Racer` grava `data/Highscore.txt`. Em root somente leitura isso quebra; mover para `$XDG_DATA_HOME/boxconsole/saves/<jogo>/`. Também reduz escrita no cartão.
- **Logs:** gravar em `$XDG_STATE_HOME/boxconsole/` ou no journald, com rotação. Evita crescimento infinito no cartão.
- **Sistema de arquivos:** `noatime`, `commit=60`, `fstrim.timer` semanal. Se possível, root somente leitura com overlayfs e uma partição pequena gravável para saves/logs.

---

### 3.5 Sistema operacional e runtime

O maior ganho “de graça” em 1 GB é não carregar um desktop.

- **SO:** Armbian Bookworm minimal (console) ou DietPi. Evitar XFCE/GNOME/KDE.
- **Vídeo:** testar `SDL_VIDEODRIVER=kmsdrm` (KMS/DRM) ou `fbcon`; evitar X11/Wayland com compositor. Fixar a saída em **1280×720@60** reduz muito o custo de escala no `present()` e nos jogos.
- **Áudio:** `SDL_AUDIODRIVER=alsa`, formato 22050 Hz mono para o menu. Reabrir o mixer no formato do menu depois de cada jogo, porque o jogo pode mudar o formato.
- **Memória:** zram de 256–512 MB (`vm.swappiness=100`). Evitar swap em cartão SD; se for eMMC, um swap pequeno é aceitável como última linha.
- **Glifos e locale:** `LANG=C.UTF-8`; fonte DejaVu embutida; evitar depender de fontconfig.
- **Kiosk:** serviço systemd com `Restart=always`, autologin no `tty1`, `consoleblank=0`, cursor escondido, sem screensaver/DPMS.
- **Boot:** desabilitar serviços não usados (Bluetooth, Avahi, CUPS, ModemManager, wait-online), `quiet loglevel=3`, `systemd-analyze blame`.
- **CPU/térmica:** governor `ondemand`/`schedutil`, limite de frequência estável (ex.: 1.2 GHz), dissipador. O H3 esquenta e throttla; medir com `armbianmonitor -m` ou `cat /sys/class/thermal/thermal_zone0/temp`.
- **CMA:** se não usar GPU/GLES, verificar reserva de CMA (`dmesg | grep -i cma`). Em alguns kernels são 128–256 MB “presos”; reduzir para 64 MB pode liberar RAM, mas testar o display antes.
- **Cgroups (opcional):** limitar a memória de jogos externos com `systemd-run --scope -p MemoryMax=...` para o OOM killer não derrubar o launcher.

---

### 3.6 Arquitetura e manutenção

Hoje as decisões de performance estão espalhadas por `pygame_ui.py`, `game_host.py`, `flappy-bird/main.py`, `Doom-PyGame/settings.py` etc. Isso funciona, mas cada novo ajuste exige lembrar de vários lugares.

**Recomendação:** criar um módulo `performance.py` (ou `perfil.py`) com:

```python
PROFILE = "h3"          # detectado por /proc/meminfo e platform.machine()
MENU_FPS = 30
IDLE_FPS = 5
MAX_GAME_FPS = 30
MAX_GAME_SIZE = (960, 540)
ENABLE_AUDIO = True
ENABLE_JOYSTICK = True
EMBED_HEAVY_GAMES = False
COVER_SIZE = (640, 360)
```

E um campo por jogo no catálogo:

```python
"perfil": {"res": (960, 540), "fps": 30, "embed": True}
```

Assim, o mesmo código roda no PC (qualidade máxima) e no H3 (modo econômico), sem `if` espalhado.

**Outras melhorias de arquitetura:**

- Separar `console_ui.py` em `catalog.py` (dados), `catalog_status.py` (disponibilidade/deps) e `console_ui.py` (UI de terminal). Hoje o menu Pygame importa o menu de terminal só pelo catálogo; separar reduz acoplamento e permite um `--list --json`.
- Adicionar `--benchmark` / `--smoke-test`: rodar o menu por N frames com `SDL_VIDEODRIVER=dummy` e cada jogo com `max_frames`, medindo ms/frame, RAM e erros. O `GameHost` já tem `max_frames`; é só expor.
- Adicionar diagnóstico real na tela `SISTEMA`: RAM livre/total (`/proc/meminfo`), temperatura, governador/frequência, espaço livre, driver de vídeo, FPS médio do menu e último FPS/RAM de cada jogo.
- Logging com `faulthandler` e arquivo rotativo; hoje um traceback em tela cheia é invisível.
- `git init` + `.gitignore` (`__pycache__`, `*.pyc`, `.venv`, logs, saves) para facilitar reverter experimentos de performance.

---

## 4. Plano em fases

| Fase | O que fazer | Ganho | Risco | Esforço |
|---|---|---|---|---|
| **0. Medir** | Benchmark do menu e dos jogos, RAM, temperatura, tempo de boot; `df -h`, `du -sh` | Dados reais para priorizar | Nenhum | Baixo |
| **1. Menu** | Dirty flag, cache de texto, cache de quadro, cache de `find_spec`, pré-carregar capas | Alto (CPU parada e navegação) | Baixo | Médio |
| **2. Jogos** | Perfis de resolução/FPS; corrigir Zelda, Street Fighter, Doom, Speed Racer; GC no host | Muito alto (jogabilidade) | Médio | Médio |
| **3. Dependências** | Remover `scipy`, `opencv`, `numpy`, `keyboard`, `pyfiglet`; enxugar `requirements.txt` | Alto (RAM, espaço, instalação) | Médio | Médio |
| **4. Assets** | Capas 640×360, áudio mono/OGG, limpeza de caches, saves em XDG | Médio (espaço, load, SD) | Baixo | Baixo |
| **5. Sistema** | Armbian/DietPi console, zram, kiosk systemd, 720p, `noatime`, log2ram | Alto (estabilidade/térmica) | Médio | Alto |
| **6. Validar** | 30 min de uso, 10 ciclos de jogo, 720p/1080p, controle remoto, áudio | Confiança | — | Médio |

---

## 5. Checklist de medição no H3

Antes de otimizar, rodar no aparelho:

```bash
free -m
cat /proc/meminfo | head -n 20
df -h
du -sh ./* 2>/dev/null | sort -h
cat /sys/class/thermal/thermal_zone0/temp
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Durante o menu:

```bash
python3 -X importtime main.py --terminal   # custo de import
top -p $(pgrep -f "main.py")               # CPU/RAM parado e navegando
```

Se possível, medir frame time com um `--benchmark` simples:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python3 main.py --benchmark --frames 300
```

E cada jogo por 120–300 frames embutidos, registrando FPS médio e pico de RAM. Sem esses números, qualquer ajuste é chute.

---

## 6. O que evitar

- **PyPy:** consome mais RAM e a integração com Pygame em ARMv7 não compensa.
- **OpenGL/Mali-400 “no escuro”:** o Pygame continua desenhando em software; forçar GLES pode quebrar o modo embutido. Só testar com `pygame.SCALED` e um driver estável.
- **Overclock sem dissipador:** o H3 throttla e fica instável; o ganho é menor que o risco.
- **Rodar tudo como root** só por causa da biblioteca `keyboard`.
- **Pré-carregar todos os assets de todos os jogos:** em 1 GB, isso termina em OOM.
- **Swap em cartão SD:** desgasta e é lento; prefira zram.
- **Otimizar armazenamento às custas de CPU:** com 8 GB, pré-computar imagens/áudio é melhor do que descomprimir/decodificar a cada frame.

---

## 7. Próximo passo sugerido

Se for para implementar uma coisa primeiro, implementar a **Fase 1 (menu)**:

1. `dirty` flag + renderização sob demanda em `pygame_ui.run()`.
2. Cache de texto em `draw_text()`.
3. Cache do quadro do menu por jogo selecionado.
4. Cache de `module_available()` e dos textos quebrados.
5. Pré-carregamento das capas em 640×360.

É a mudança de menor risco e maior efeito percebido: o menu deixa de consumir CPU parado e a navegação fica fluida mesmo antes de mexer nos jogos.

Depois, a **Fase 2** ataca o que realmente impede de jogar: Zelda a 120 FPS, Street Fighter com blur por frame, Doom com raycasting e Speed Racer a 60 FPS.
