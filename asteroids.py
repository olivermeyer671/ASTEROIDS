import pygame
import sys
import math
import random

#initialize pygame
pygame.init()
pygame.mixer.init()

#screen constants
WIDTH,HEIGHT = 800,600
BACKGROUND_COLOR = (0,0,0)

#turret constants
TURRET_RADIUS = 50
TURRET_COLOR = (255,0,0)

#bullet constants
BULLET_SPEED = 0.5
BULLET_RADIUS = 2
BULLET_COLOR = (0,0,255)
BULLET_COOLDOWN = 50
LAST_BULLET_TIME = pygame.time.get_ticks()

#asteroid constants
ASTEROID_SPEED = 0.25
ASTEROID_RADIUS = 10
ASTEROID_COLOR = (0,255,0)
ASTEROID_COOLDOWN = 500
LAST_ASTEROID_TIME = pygame.time.get_ticks()

#building constants
BUILDING_COLOR = (255,0,0)
BUILDING_RADIUS = 50

#game data
SCORE = 0
LIVES = 4
TOP_SCORE = 0

#audio constants
SOUND_BULLET = pygame.mixer.Sound("audio/blipSelect.wav")
SOUND_HIT = pygame.mixer.Sound("audio/explosion.wav")
SOUND_EXPLOSION = pygame.mixer.Sound("audio/random.wav")
SOUND_GAME_OVER = pygame.mixer.Sound("audio/gameover.wav")
MUSIC_THEME = pygame.mixer.music.load("audio/theme.mp3")
MUSIC_TITLE = pygame.mixer.music.load("audio/title.mp3")

#audio mixing
SOUND_BULLET.set_volume(0.3)
SOUND_HIT.set_volume(0.4)

#setup the display
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ASTEROIDS")

#do not quit game yet
QUIT_GAME = False

#class for bullets
class Bullet:
    def __init__(self, x, y, angle, speed, radius, color):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.radius = radius
        self.color = color

    def update(self):
        self.x += BULLET_SPEED * math.cos(self.angle)
        self.y += BULLET_SPEED * math.sin(self.angle)

    def render(self):
        pygame.draw.circle(SCREEN, self.color, (self.x, self.y), self.radius)

#class for asteroids
class Asteroid:
    def __init__(self, x, y, angle, speed, radius, color):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.radius = radius
        self.color = color

    def update(self):
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

    def render(self):
        pygame.draw.circle(SCREEN, self.color, (self.x, self.y), self.radius)

#class for buildings
class Building:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

    def render(self):
        pygame.draw.circle(SCREEN, BUILDING_COLOR, (self.x, self.y), self.radius)

#IMPLEMENT COLLISIONS

#state manager
class State:
    def __init__(self):
        self.next_state = None
    
    def handle_events(self):
        pass

    def update(self):
        pass

    def render(self, screen):
        self.screen = screen

#title state
class TitleState(State):
    global SCORE, LIVES

    def __init__(self):
        super().__init__()
        pygame.mixer.music.load("audio/title.mp3")
        pygame.mixer.music.play(-1)
        SCORE = 0
        LIVES = 4
    
    def number(self):
        return 0

    def handle_events(self):
        if any(pygame.key.get_pressed()):
            self.next_state = GameState()

    def update(self):
        pass

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        #display title
        font = pygame.font.Font(None, 72)
        text = font.render("ASTEROIDS", True, (255,0,0))
        screen.blit(text, ((WIDTH // 2) - (text.get_width() // 2), (HEIGHT // 2) - (text.get_height() // 2)))

#game state
class GameState(State):
    def __init__(self):
        super().__init__()
        pygame.mixer.music.load("audio/theme.mp3")
        pygame.mixer.music.play(-1)
        pygame.time.delay(500)
        self.asteroids = []
        self.bullets = []
        self.buildings = [Building(WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(2*WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(4*WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(5*WIDTH//6, HEIGHT, BUILDING_RADIUS)]
          
    def number(self):
        return 1

    def create_asteroid(self):
            new_asteroid = Asteroid(random.uniform(0, WIDTH), 0, random.uniform(math.pi/4, 3*math.pi/4), random.uniform(ASTEROID_SPEED/2, 2*ASTEROID_SPEED), random.uniform(ASTEROID_RADIUS/2, 2*ASTEROID_RADIUS), ASTEROID_COLOR)
            self.asteroids.append(new_asteroid)

    def update_asteroid(self):
        for asteroid in self.asteroids:
            if asteroid.x < 0 or asteroid.x > WIDTH or asteroid.y < 0 or asteroid.y > HEIGHT:
                self.asteroids.remove(asteroid)

    def bullet_angle(self):
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        dx = self.mouse_x - WIDTH//2
        dy = self.mouse_y - HEIGHT
        return math.atan2(dy,dx)
    
    def bullet_coordinate(self, angle, radius):
        x = WIDTH // 2 + int(radius * math.cos(angle))
        y = HEIGHT + int(radius * math.sin(angle))
        return (x, y)

    def create_bullet(self):
        bullet_position = self.bullet_coordinate(self.bullet_angle(), TURRET_RADIUS)
        new_bullet = Bullet(bullet_position[0], bullet_position[1], self.bullet_angle(), BULLET_SPEED, BULLET_RADIUS, BULLET_COLOR)
        self.bullets.append(new_bullet)

    def update_bullet(self):
        for bullet in self.bullets:
            if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
                self.bullets.remove(bullet)

    def check_collision(self, c1, c2):
        self.c1 = c1
        self.c2 = c2
        distance = math.sqrt((self.c1.x - self.c2.x)**2 + (self.c1.y - self.c2.y)**2)
        return distance < self.c1.radius + self.c2.radius

    def update(self):
        global LAST_BULLET_TIME, LAST_ASTEROID_TIME, LIVES, SCORE

        #update asteroids
        if pygame.time.get_ticks() - LAST_ASTEROID_TIME > ASTEROID_COOLDOWN:
            self.create_asteroid()
            LAST_ASTEROID_TIME = pygame.time.get_ticks()
        self.update_asteroid()
        for asteroid in self.asteroids:
            asteroid.update()

        #update bullets
        if pygame.mouse.get_pressed()[0] and pygame.time.get_ticks() - LAST_BULLET_TIME > BULLET_COOLDOWN:
            self.create_bullet()
            LAST_BULLET_TIME = pygame.time.get_ticks()
            SOUND_BULLET.play()
        self.update_bullet()
        for bullet in self.bullets:
            bullet.update()

        #check for collisions and update stats
        for asteroid in self.asteroids:
            for bullet in self.bullets:
                if self.check_collision(asteroid, bullet):
                    self.bullets.remove(bullet)
                    self.asteroids.remove(asteroid)
                    SOUND_HIT.play()
                    SCORE += 10

            for building in self.buildings:
                if self.check_collision(asteroid, building):
                    self.buildings.remove(building)
                    self.asteroids.remove(asteroid)
                    LIVES -= 1
                    SOUND_EXPLOSION.play()
                    if LIVES <= 0:
                        LIVES = 4
                        SOUND_GAME_OVER.play()
                        self.next_state = TitleState()

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        for asteroid in self.asteroids:
            asteroid.render()

        for bullet in self.bullets:
            bullet.render()

        for building in self.buildings:
            building.render()

#start game on title screen
CURRENT_STATE = TitleState()

#main loop
while not QUIT_GAME:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            QUIT_GAME = True

    #handle events and state transitions
    CURRENT_STATE.handle_events()
    if CURRENT_STATE.next_state:
        CURRENT_STATE = CURRENT_STATE.next_state
    
    #update and render the current state
    CURRENT_STATE.update()
    CURRENT_STATE.render(SCREEN)

    #update display
    pygame.display.flip()

#quit pygame
pygame.quit()
sys.exit()