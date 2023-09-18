import pygame

background = (120, 220, 250)
screen = pygame.display.set_mode((300,300))

pygame.display.set_caption('testgame')

screen.fill(background)

pygame.display.flip()

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

            