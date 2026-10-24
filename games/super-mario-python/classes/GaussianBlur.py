import pygame


class GaussianBlur:
    """Desfoque barato usando redução + ampliação com smoothscale.

    Substitui o scipy.ndimage.gaussian_filter: o resultado é visualmente
    semelhante para o menu de pausa e não exige numpy/scipy no ARMv7.
    """

    def __init__(self, kernelsize=7):
        self.kernel_size = kernelsize

    def filter(self, srfc, xpos, ypos, width, height):
        region = srfc.subsurface((xpos, ypos, width, height)).copy()
        divisor = max(2, min(16, int(self.kernel_size)))
        small = pygame.transform.smoothscale(
            region, (max(1, width // divisor), max(1, height // divisor))
        )
        return pygame.transform.smoothscale(small, (width, height))
