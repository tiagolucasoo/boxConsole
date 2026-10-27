import pygame
import time
import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.name == "nt":
    _data_base = os.environ.get("APPDATA") or BASE_DIR
else:
    _data_base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
_data_dir = os.path.join(_data_base, "boxconsole")
os.makedirs(_data_dir, exist_ok=True)
HIGHSCORE_PATH = os.path.join(_data_dir, "speed-racer-highscore.txt")
_legacy_highscore = os.path.join(BASE_DIR, "data", "Highscore.txt")
if not os.path.exists(HIGHSCORE_PATH) and os.path.exists(_legacy_highscore):
    try:
        with open(_legacy_highscore, "r") as _src, open(HIGHSCORE_PATH, "w") as _dst:
            _dst.write(_src.read().strip() or "0")
    except OSError:
        pass

pygame.init()
pygame.mixer.init()

# O jogo foi escrito para 1200x700. Renderizar nessa resolução e deixar o
# host reduzir custa caro no H3. Aqui tudo é desenhado a 75% e o host só
# amplia 900x525 para a área de 960x540.
SCALE = 0.75


def scaled_size(width, height):
    return (max(1, int(width * SCALE)), max(1, int(height * SCALE)))


class ScaledWindow:
    """Superfície 900x525 que aceita coordenadas do projeto original."""

    def __init__(self, surface):
        self.surface = surface

    def blit(self, source, dest, *args, **kwargs):
        return self.surface.blit(
            source,
            (int(dest[0] * SCALE), int(dest[1] * SCALE)),
            *args,
            **kwargs,
        )

    def fill(self, color):
        return self.surface.fill(color)


_real_window = pygame.display.set_mode(scaled_size(1200, 700))
gameWindow = ScaledWindow(_real_window)
pygame.display.set_caption("Speed Racer")

clock = pygame.time.Clock()
fps = 30

font1 = pygame.font.SysFont("Franklin Gothic Demi Cond", max(16, int(50 * SCALE)))

car = pygame.image.load("data/images/Car.png")
car = pygame.transform.scale(car, scaled_size(150, 150)).convert_alpha()

road = pygame.image.load("data/images/Road.png")
road = pygame.transform.scale(road, scaled_size(400, 700)).convert_alpha()

sand = pygame.image.load("data/images/Sand.jpg")
sand = pygame.transform.scale(sand, scaled_size(150, 700)).convert_alpha()

leftDisp = pygame.image.load("data/images/LeftDisplay.png")
leftDisp = pygame.transform.scale(leftDisp, scaled_size(250, 700)).convert_alpha()

rightDisp = pygame.image.load("data/images/RightDisplay.png")
rightDisp = pygame.transform.scale(rightDisp, scaled_size(250, 700)).convert_alpha()

tree = pygame.image.load("data/images/Tree.png")
tree = pygame.transform.scale(tree, scaled_size(185, 168)).convert_alpha()
treeLXY = [[290,0],[290,152.5],[290,305],[290,457.5],[290,610]]
treeRXY = [[760,0],[760,152.5],[760,305],[760,457.5],[760,610]]

strip = pygame.image.load("data/images/Strip.png")
strip = pygame.transform.scale(strip, scaled_size(25, 90)).convert_alpha()
stripXY = [[593,0],[593,152.5],[593,305],[593,457.5],[593,610]]

explosion = pygame.image.load("data/images/Explosion.png")
explosion = pygame.transform.scale(explosion, scaled_size(290, 164)).convert_alpha()

fuel = pygame.image.load("data/images/Fuel.png")
fuel = pygame.transform.scale(fuel, scaled_size(98, 104)).convert_alpha()

comingCars,goingCars = [],[]
speedCC = [13,14,15,14,14,15,13,14,15]
speedGC = [8,6,7,5,8,7,8,6,8]

for i in range(1,10):
    CCi = pygame.image.load("data/images/Coming Cars/"+"CC"+str(i)+".png")
    CCi = pygame.transform.scale(CCi, scaled_size(75, 158)).convert_alpha()
    comingCars.append([CCi,speedCC[i-1]])
    GCi = pygame.image.load("data/images/Going Cars/"+"GC"+str(i)+".png").convert_alpha()
    GCi = pygame.transform.scale(GCi, scaled_size(75, 158)).convert_alpha()
    goingCars.append([GCi,speedGC[i-1]])

def distance(carX,obstX,carY,obstY,isFuel = False):

    if not isFuel:
        carX += 75 # 75,75,37,79,55,130
        carY += 75
        obstX += 37
        obstY += 79

        return abs(carX - obstX) < 55 and abs(carY - obstY) < 130
    else:
        carX += 75
        carY += 75
        obstX += 98
        obstY += 104

        return abs(carX - obstX) < 70 and abs(carY - obstY) < 80

_text_cache = {}


def textOnScreen(text,color,x,y,font):
    key = (id(font), str(text), tuple(color))
    screenText = _text_cache.get(key)
    if screenText is None:
        screenText = font.render(str(text), True, color)
        if len(_text_cache) > 128:
            _text_cache.clear()
        _text_cache[key] = screenText
    gameWindow.blit(screenText,[x,y])

def slowDown(carX,carY,dist,highscore):

    stripXY_ = [[593, 0], [593, 152.5], [593, 305], [593, 457.5], [593, 610]]
    exitScreen = False

    stripSpeed = 2

    start = time.time()
    while not exitScreen:
        if time.time() - start > 3:
            stripSpeed = 1
        if time.time() - start > 6:
            exitScreen = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exitScreen = True

        gameWindow.fill((0,0,0))
        gameWindow.blit(leftDisp, (0, 0))
        textOnScreen("DISTANCE", (255, 255, 0), 27, 388, font1)
        textOnScreen(str(dist) + " Kms", (255, 0, 0), 56, 480, font1)
        textOnScreen("FUEL", (255, 255, 0), 73, 90, font1)
        textOnScreen(str(0.00) + ' %', (255, 0, 0), 75, 184, font1)
        gameWindow.blit(rightDisp, (950, 0))
        textOnScreen("HIGHSCORE", (255, 255, 0), 958, 236, font1)
        if(highscore < 10):
            disp = str(0) + str(highscore)
        else:
            disp = str(highscore)
        textOnScreen(disp + " Kms", (255, 0, 0), 1005, 342, font1)
        gameWindow.blit(road, (400, 0))
        gameWindow.blit(sand,(250,0))
        gameWindow.blit(sand,(800,0))

        for i in range(len(stripXY_)):
            stripXY_[i][1] += stripSpeed
            if stripXY_[i][1] > 700:
                stripXY_[i] = [593, -60]
        for i in range(len(treeLXY)):
            treeLXY[i][1] += stripSpeed
            if treeLXY[i][1] > 700:
                treeLXY[i] = [290,-60]
        for i in range(len(treeRXY)):
            treeRXY[i][1] += stripSpeed
            if treeRXY[i][1] > 700:
                treeRXY[i] = [760,-60]

        for X,Y in stripXY_:
            gameWindow.blit(strip,(X,Y))
        for treeX,treeY in treeLXY:
            gameWindow.blit(tree,(treeX,treeY))
        for treeX,treeY in treeRXY:
            gameWindow.blit(tree,(treeX,treeY))

        gameWindow.blit(car,(carX,carY))
        pygame.display.update()
        # Sem isso a tela de fim de jogo rodava em 100% de CPU no H3.
        clock.tick(fps)

def gameLoop():

    pygame.mixer.music.load("data/audios/lmn.mp3")
    pygame.mixer.music.play()

    time.sleep(1)

    carX,carY = 625,540
    drift = 4
    carSpeedX = 0

    obstacleXY = [[460,-10],[710,-300]]
    c1,c2 = random.randint(0,8),random.randint(0,8)
    if(c1 == c2):
        c1 = random.randint(0,8)

    obstacleSpeed = [comingCars[c1][1],goingCars[c2][1]]
    obstacles = [comingCars[c1][0],goingCars[c2][0]]

    stripSpeed = 9

    exitGame = False
    gameOver = False
    explode = False

    fuelCount = 50
    fuelX,fuelY = random.randint(420,620),-1000
    fuelSpeed = 8
    dist = 0

    with open(HIGHSCORE_PATH, "r") as f:
        highscore = int(f.read().strip() or 0)

    slow = False
    plotFuel = True

    start1 = time.time()
    start = [start1,start1]
    start2 = start1
    start3 = start1
    start4 = start1
    arrival = [2,3.5]

    while not exitGame:
        if gameOver:

            if slow:
                slowDown(carX,carY,dist,highscore)
            time.sleep(2)

            pygame.mixer.music.stop()
            pygame.mixer.music.load("data/audios/rtn.mp3")
            pygame.mixer.music.play()

            exitScreen = False
            go = pygame.image.load("data/images/GameOver.png")
            go = pygame.transform.scale(go, scaled_size(1239, 752)).convert_alpha()

            with open(HIGHSCORE_PATH, "w") as f:
                f.write(str(highscore))

            while not exitScreen:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        exitScreen = True
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            pygame.mixer.music.stop()
                            homeScreen()
                gameWindow.fill((0,0,0))
                gameWindow.blit(go,(0,0))
                if(dist < 10):
                    disp = str(0) + str(dist)
                else:
                    disp = str(dist)
                textOnScreen(disp,(255,0,0),540,429,font1)
                pygame.display.update()
                clock.tick(fps)

            pygame.quit()
            quit()
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exitGame = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        carSpeedX = drift
                    elif event.key == pygame.K_LEFT:
                        carSpeedX = -drift
                    elif event.key == pygame.K_a:
                        obstacleXY[0][0] -= 20
                    elif event.key == pygame.K_d:
                        obstacleXY[1][0] += 20

            carX += carSpeedX
            fuelY += fuelSpeed

            if time.time() - start4 >= 2:
                dist += 1
                if dist > highscore:
                    highscore = dist
                start4 = time.time()

            if time.time() - start2 >= 3:
                fuelCount -= 5
                start2 = time.time()

            if distance(carX,fuelX,carY,fuelY,True) and plotFuel:
                plotFuel = False
                fuelCount += 20

            for i in range(len(obstacleXY)):
                obstacleXY[i][1] += obstacleSpeed[i]

            fuelper = fuelCount/50
            if fuelper >= 1:
                fuelper = 1

            gameWindow.fill((0,0,0))
            gameWindow.blit(leftDisp,(0,0))
            textOnScreen("DISTANCE", (255, 255, 0),27,388,font1)
            if(dist < 10):
                disp = str(0) + str(dist)
            else:
                disp = str(dist)
            textOnScreen(disp + " Kms",(255,0,0),56,480,font1)
            textOnScreen("FUEL",(255,255,0),73,90,font1)
            textOnScreen(str(fuelper*100) + ' %',(255,0,0),60,184,font1)
            gameWindow.blit(rightDisp, (950, 0))
            textOnScreen("HIGHSCORE",(255,255,0),958,236,font1)
            if(highscore < 10):
                disp = str(0) + str(highscore)
            else:
                disp = str(highscore)            
            textOnScreen(disp + " Kms",(255,0,0),1005,342,font1)
            gameWindow.blit(road,(400,0))
            gameWindow.blit(sand, (250, 0))
            gameWindow.blit(sand, (800, 0))

            if fuelCount == 0:
                gameOver = True
                slow = True

            if carX > 720 or carX < 330:
                pygame.mixer.music.load("data/audios/Crash.mp3")
                pygame.mixer.music.play()
                gameOver = True
                explode = True

            for i in range(len(obstacleXY)):
                if distance(carX,obstacleXY[i][0],carY,obstacleXY[i][1]):
                    pygame.mixer.music.load("data/audios/Crash.mp3")
                    pygame.mixer.music.play()
                    gameOver = True
                    explode = True
                    break
            for i in range(len(stripXY)):
                stripXY[i][1] += stripSpeed
                if stripXY[i][1] > 700:
                    stripXY[i] = [593,-60]
            for i in range(len(treeLXY)):
                treeLXY[i][1] += stripSpeed
                if treeLXY[i][1] > 700:
                    treeLXY[i] = [290, -60]
            for i in range(len(treeRXY)):
                treeRXY[i][1] += stripSpeed
                if treeRXY[i][1] > 700:
                    treeRXY[i] = [760, -60]

            for stripX,stripY in stripXY:
                gameWindow.blit(strip,(stripX,stripY))

            if fuelY < 750:
                if plotFuel:
                    gameWindow.blit(fuel,(fuelX,fuelY))

            gameWindow.blit(car,(carX,carY))

            for i in range(len(obstacleXY)):
                if obstacleXY[i][1] < 750:
                    gameWindow.blit(obstacles[i],(obstacleXY[i][0], obstacleXY[i][1]))

            for treeX, treeY in treeLXY:
                gameWindow.blit(tree, (treeX, treeY))
            for treeX, treeY in treeRXY:
                gameWindow.blit(tree, (treeX, treeY))

            if time.time() - start[0] >= arrival[0]:
                x = random.randint(430,530)
                x+=3
                obstacleXY[0] = [x,-10]
                c1 = random.randint(0,8)
                obstacles[0] = comingCars[c1][0]
                obstacleSpeed[0] = comingCars[c1][1]
                start[0] = time.time()
            if time.time() - start[1] >= arrival[1]:
                x = random.randint(620,710)
                x-=3
                obstacleXY[1] = [x,-10]
                c2 = random.randint(0,8)
                obstacles[1] = goingCars[c2][0]
                obstacleSpeed[1] = goingCars[c2][1]
                start[1] = time.time()
            if time.time() - start3 >= 15:
                fuelX,fuelY = random.randint(420,710),-500
                plotFuel = True
                start3 = time.time()
            if explode:
                gameWindow.blit(explosion,(carX - 63,carY))

            pygame.display.update()
            clock.tick(fps)


    pygame.quit()
    quit()

def homeScreen():

    pygame.mixer.music.load("data/audios/rtn.mp3")
    pygame.mixer.music.play()

    if not os.path.exists(HIGHSCORE_PATH):
        with open(HIGHSCORE_PATH, "w") as f:
            f.write("0")
        highscore = 0
    else:
        with open(HIGHSCORE_PATH, "r") as f:
            highscore = int(f.read().strip() or 0)


    background = pygame.image.load("data/images/Background.png")
    background = pygame.transform.scale(background, scaled_size(1213, 760)).convert_alpha()

    exitScreen = False
    while not exitScreen:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exitScreen = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    pygame.mixer.music.stop()
                    gameLoop()

        gameWindow.blit(background,(-6,-32))
        if(highscore < 10):
            disp = str(0) + str(highscore)
        else:
            disp = str(highscore)
        textOnScreen(disp,(255,0,0),980,9,font1)
        pygame.display.update()
        clock.tick(fps)

    pygame.quit()
    quit()


homeScreen()    
