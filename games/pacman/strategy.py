import random

def eh_obstaculo(mapa, y, x):
    """Verifica se uma posição é um obstáculo."""
    obstaculos = {'#', '8', '7', '6', '5'}
    
    # Verifica limites do mapa
    if not (0 <= y < len(mapa) and 0 <= x < len(mapa[0])):
        return True
        
    if mapa[y][x] in obstaculos:
        return True
        
    return False

def movimento_aleatorio_valido(mapa, fantasma):
    """Retorna um movimento aleatório que não seja um obstáculo."""
    movimentos_possiveis = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    random.shuffle(movimentos_possiveis) # Embaralha para não viciar
    
    for dy, dx in movimentos_possiveis:
        if not eh_obstaculo(mapa, fantasma['y'] + dy, fantasma['x'] + dx):
            return (dy, dx) # Retorna o primeiro aleatório válido
            
    return (0, 0) # Fica parado se estiver totalmente preso

def movimento_base_perseguicao(mapa, fantasma, alvo_y, alvo_x):
    # 1. Calcula a distância (direção)
    dist_y = alvo_y - fantasma['y']
    dist_x = alvo_x - fantasma['x']
    
    # 2. Define o movimento preferencial
    mov_y, mov_x = 0, 0
    
    # 3. Tenta se mover no eixo com maior distância primeiro
    if abs(dist_y) > abs(dist_x):
        # Tenta mover na vertical (Y)
        if dist_y > 0: mov_y = 1   # Tenta ir para Baixo
        elif dist_y < 0: mov_y = -1 # Tenta ir para Cima
        
        # Se o caminho preferido (Y) for um obstáculo...
        if eh_obstaculo(mapa, fantasma['y'] + mov_y, fantasma['x']):
            # ...tenta se mover no eixo X (se houver necessidade)
            if dist_x > 0: mov_x = 1
            elif dist_x < 0: mov_x = -1
            mov_y = 0 # Cancela o movimento Y
        
    else:
        # Tenta mover na horizontal (X)
        if dist_x > 0: mov_x = 1   # Tenta ir para Direita
        elif dist_x < 0: mov_x = -1 # Tenta ir para Esquerda
        
        # Se o caminho preferido (X) for um obstáculo...
        if eh_obstaculo(mapa, fantasma['y'], fantasma['x'] + mov_x):
            # ...tenta se mover no eixo Y (se houver necessidade)
            if dist_y > 0: mov_y = 1
            elif dist_y < 0: mov_y = -1
            mov_x = 0 # Cancela o movimento X

    # Se o movimento final não for (0,0) E não for um obstáculo
    if (mov_y != 0 or mov_x != 0) and not eh_obstaculo(mapa, fantasma['y'] + mov_y, fantasma['x'] + mov_x):
        return (mov_y, mov_x)

    # 4. Se ficou preso (ex: beco sem saída), faz um movimento aleatório válido
    return movimento_aleatorio_valido(mapa, fantasma)

def fantasma_blinky(mapa, fantasma, pacman_y, pacman_x):
    return movimento_base_perseguicao(mapa, fantasma, pacman_y, pacman_x)

def fantasma_pinky(mapa, fantasma, pacman_y, pacman_x):
    return movimento_base_perseguicao(mapa, fantasma, pacman_y - 4, pacman_x)

def fantasma_inky(mapa, fantasma, pacman_y, pacman_x):
    return movimento_base_perseguicao(mapa, fantasma, pacman_y + 4, pacman_x)

def fantasma_clyde(mapa, fantasma, pacman_y, pacman_x):
    # Calcula a distância
    distancia = abs(fantasma['y'] - pacman_y) + abs(fantasma['x'] - pacman_x)
    
    if distancia > 8:
        # Se longe, persegue o Pac-Man (igual ao Blinky)
        return movimento_base_perseguicao(mapa, fantasma, pacman_y, pacman_x)
    else:
        # Se perto, foge para o canto inferior esquerdo
        alvo_fuga_y = len(mapa) - 2
        alvo_fuga_x = 1            
        return movimento_base_perseguicao(mapa, fantasma, alvo_fuga_y, alvo_fuga_x)