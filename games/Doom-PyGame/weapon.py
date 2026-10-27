from sprite_object import *


class Weapon(AnimatedSprite):
    def __init__(self, game, path='resources/sprites/weapon/shotgun/0.png', scale=None, animation_time=90):
        super().__init__(game=game, path=path, scale=scale or 0.4, animation_time=animation_time)
        if scale is None:
            # A HUD é desenhada na resolução virtual de 480x270. O scale fixo
            # de 0.4 foi pensado para 1080p e deixava a arma maior que a tela.
            target_height = HEIGHT * 0.40
            scale = target_height / max(1, self.images[0].get_height())
        self.images = deque(
            [pg.transform.smoothscale(
                img,
                (max(1, int(img.get_width() * scale)),
                 max(1, int(img.get_height() * scale))),
            ) for img in self.images])
        self.image = self.images[0]
        self.weapon_pos = (HALF_WIDTH - self.images[0].get_width() // 2, HEIGHT - self.images[0].get_height())
        self.reloading = False
        self.num_images = len(self.images)
        self.frame_counter = 0
        self.damage = 50

    def animate_shot(self):
        if self.reloading:
            self.game.player.shot = False
            if self.animation_trigger:
                self.images.rotate(-1)
                self.image = self.images[0]
                self.frame_counter += 1
                if self.frame_counter == self.num_images:
                    self.reloading = False
                    self.frame_counter = 0

    def draw(self):
        self.game.screen.blit(self.images[0], self.weapon_pos)

    def update(self):
        self.check_animation_time()
        self.animate_shot()