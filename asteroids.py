import pygame
import sys
import math
import random
import json

#initialize pygame
pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()

#screen constants
#WIDTH = pygame.display.Info().current_w
#HEIGHT = pygame.display.Info().current_h - 60
WIDTH,HEIGHT = 800,600
BACKGROUND_COLOR = (0,0,0)

#fps limiter
FPS = 120

#master speed control
SPEED_MULTIPLIER = (10 * FPS) // FPS

#top score display color
FONT_COLOR = (255,0,0)
FONT_COLOR_TOP_SCORE = FONT_COLOR

#turret constants
TURRET_RADIUS = 20
TURRET_HEIGHT = 2 * TURRET_RADIUS
TURRET_COLOR = (255,0,0)

#bullet constants
BULLET_SPEED = 1 * SPEED_MULTIPLIER
BULLET_RADIUS = 2
BULLET_COLOR = (0,0,255)
BULLET_COOLDOWN = 50
LAST_BULLET_TIME = pygame.time.get_ticks()

#asteroid constants
ASTEROID_SPEED = 0.1 * SPEED_MULTIPLIER
ASTEROID_RADIUS = 10
ASTEROID_COLOR = (0,255,0)
ASTEROID_COOLDOWN = 500
LAST_ASTEROID_TIME = pygame.time.get_ticks()

#missile constants
MISSILE_SPEED = 1 * SPEED_MULTIPLIER
MISSILE_RADIUS = 3
MISSILE_COLOR = (255,255,255)
MISSILE_COOLDOWN = 1000
LAST_MISSILE_TIME = pygame.time.get_ticks()

#building constants
BUILDING_COLOR = (255,0,0)
BUILDING_RADIUS = 50

#game data
SCORE = 0
LIVES = 4

#data file
DATA_FILE = "data.json"

#load data from file
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            return data.get("TOP_SCORE", 0)
    except FileNotFoundError:
        return 0
    
#top score
TOP_SCORE = load_data()

#save data to file
def save_data():
    data = {"TOP_SCORE": TOP_SCORE}
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

#audio constants
SOUND_BULLET = pygame.mixer.Sound("audio/bullet.wav")
SOUND_MISSILE = pygame.mixer.Sound("audio/missile.wav")
SOUND_HIT = pygame.mixer.Sound("audio/hit.wav")
SOUND_EXPLOSION = pygame.mixer.Sound("audio/explosion.wav")
SOUND_GAME_OVER = pygame.mixer.Sound("audio/gameover.wav")
MUSIC_THEME = pygame.mixer.music.load("audio/theme.ogg")
MUSIC_TITLE = pygame.mixer.music.load("audio/title.ogg")

#audio mixing
SOUND_BULLET.set_volume(0.3)
SOUND_HIT.set_volume(0.4)

#setup the screen
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ASTEROIDS")

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

#class for missiles
class Missile:
    def __init__(self, x, y, angle, speed, radius, color, target_x, target_y, target_angle, target_speed):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.radius = radius
        self.color = color
        self.target_x = target_x
        self.target_y = target_y
        self.target_angle = target_angle
        self.target_speed = target_speed

    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        self.angle = math.atan2(dy,dx)
        self.x += BULLET_SPEED * math.cos(self.angle)
        self.y += BULLET_SPEED * math.sin(self.angle)
        self.target_x += self.target_speed * math.cos(self.target_angle)
        self.target_y += self.target_speed * math.sin(self.target_angle)

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

#state manager interface
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

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            self.next_state = GameState()

    def update(self):
        pass

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        #display title
        font = pygame.font.Font(None, 72)
        text = font.render("ASTEROIDS", True, FONT_COLOR)
        screen.blit(text, ((WIDTH // 2) - (text.get_width() // 2), (HEIGHT // 2) - (text.get_height() // 2)))

        #display press spacebar
        font = pygame.font.Font(None, 18)
        text_prompt = font.render("press space", True, FONT_COLOR)
        screen.blit(text_prompt, ((WIDTH // 2) - (text_prompt.get_width() // 2), (HEIGHT // 2) - (text_prompt.get_height() // 2) + (text.get_height() // 2) + 10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP SCORE: {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

#game state
class GameState(State):
    def __init__(self):
        global FONT_COLOR, SCORE, LIVES, FONT_COLOR_TOP_SCORE
        super().__init__()
        FONT_COLOR_TOP_SCORE = FONT_COLOR
        SCORE = 0
        LIVES = 4
        pygame.mixer.music.load("audio/theme.mp3")
        pygame.mixer.music.play(-1)
        pygame.time.delay(500)
        self.asteroids = []
        self.bullets = []
        self.buildings = [Building(WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(2*WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(4*WIDTH//6, HEIGHT, BUILDING_RADIUS),
                          Building(5*WIDTH//6, HEIGHT, BUILDING_RADIUS)]
        self.missiles = []

    def create_asteroid(self):
            new_asteroid = Asteroid(random.uniform(0, WIDTH), 0, random.uniform(math.pi/4, 3*math.pi/4), ASTEROID_SPEED*random.uniform(0.5, 6), ASTEROID_RADIUS*random.uniform(0.5, 2), ASTEROID_COLOR)
            self.asteroids.append(new_asteroid)

    def update_asteroids(self):
        for asteroid in self.asteroids:
            if asteroid.x < 0 or asteroid.x > WIDTH or asteroid.y < 0 or asteroid.y > HEIGHT:
                self.asteroids.remove(asteroid)

    #returns the current angle from the turret to the pointer
    def bullet_angle(self):
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        dx = self.mouse_x - WIDTH//2
        dy = self.mouse_y - (HEIGHT - TURRET_HEIGHT)
        return math.atan2(dy,dx)
    
    #returns the starting coordinates of the bullet or missile on the turret circle
    def bullet_coordinate(self, angle, radius):
        x = WIDTH // 2 + int(radius * math.cos(angle))
        y = (HEIGHT - TURRET_HEIGHT) + int(radius * math.sin(angle))
        return (x, y)

    def create_bullet(self):
        bullet_position = self.bullet_coordinate(self.bullet_angle(), TURRET_RADIUS)
        new_bullet = Bullet(bullet_position[0], bullet_position[1], self.bullet_angle(), BULLET_SPEED, BULLET_RADIUS, BULLET_COLOR)
        self.bullets.append(new_bullet)

    def update_bullets(self):
        for bullet in self.bullets:
            if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
                self.bullets.remove(bullet)

    def create_missile(self, target_x, target_y, target_angle, target_speed):
        missile_position = self.bullet_coordinate(self.bullet_angle(), TURRET_RADIUS)
        new_missile = Missile(missile_position[0], missile_position[1], self.bullet_angle(), MISSILE_SPEED, MISSILE_RADIUS, MISSILE_COLOR, target_x, target_y, target_angle, target_speed)
        self.missiles.append(new_missile)

    def update_missiles(self):
        for missile in self.missiles:
            if missile.x < 0 or missile.x > WIDTH or missile.y < 0 or missile.y > HEIGHT:
                self.missiles.remove(missile)

    #detects a collision between two circles
    def check_collision(self, c1, c2):
        self.c1 = c1
        self.c2 = c2
        distance = math.sqrt((self.c1.x - self.c2.x)**2 + (self.c1.y - self.c2.y)**2)
        return distance < self.c1.radius + self.c2.radius

    #updates position of all items on screen, removes them if a collision is detected or they move off screen
    def update(self):
        global LAST_BULLET_TIME, LAST_ASTEROID_TIME, LAST_MISSILE_TIME, LIVES, SCORE, TOP_SCORE, FONT_COLOR, FONT_COLOR_TOP_SCORE

        #update asteroids
        if pygame.time.get_ticks() - LAST_ASTEROID_TIME > ASTEROID_COOLDOWN:
            self.create_asteroid()
            LAST_ASTEROID_TIME = pygame.time.get_ticks()
        self.update_asteroids()
        for asteroid in self.asteroids:
            asteroid.update()

        #update bullets
        if pygame.mouse.get_pressed()[0] and pygame.time.get_ticks() - LAST_BULLET_TIME > BULLET_COOLDOWN:
            self.create_bullet()
            LAST_BULLET_TIME = pygame.time.get_ticks()
            SOUND_BULLET.play()
        self.update_bullets()
        for bullet in self.bullets:
            bullet.update()

        #update missiles
        if pygame.mouse.get_pressed()[2] and pygame.time.get_ticks() - LAST_MISSILE_TIME > MISSILE_COOLDOWN:
            for asteroid in self.asteroids:
                self.create_missile(asteroid.x, asteroid.y, asteroid.angle, asteroid.speed)
                LAST_MISSILE_TIME = pygame.time.get_ticks()
                SOUND_MISSILE.play()
        self.update_missiles()
        for missile in self.missiles:
            missile.update()

        #check for collisions between asteroids and bullets, update stats
        for bullet in self.bullets:
            for asteroid in self.asteroids:
                if self.check_collision(asteroid, bullet):
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    if asteroid in self.asteroids:
                        self.asteroids.remove(asteroid)
                    SOUND_HIT.play()
                    SCORE += 10
                    if SCORE > TOP_SCORE:
                        TOP_SCORE = SCORE
                        FONT_COLOR_TOP_SCORE = (0,255,0)

        #check for collisions between asteroids and buildings, update stats
        for asteroid in self.asteroids:
            for building in self.buildings:
                if self.check_collision(asteroid, building):
                    if building in self.buildings:
                        self.buildings.remove(building)
                    if asteroid in self.asteroids:
                        self.asteroids.remove(asteroid)
                    LIVES -= 1
                    SOUND_EXPLOSION.play()
                    if LIVES <= 0:
                        LIVES = 4
                        save_data()
                        SOUND_GAME_OVER.play()
                        self.next_state = TitleState()

        #check for collisions between asteroids and missiles, update stats
        for missile in self.missiles:
            for asteroid in self.asteroids:
                if self.check_collision(asteroid, missile):
                    if missile in self.missiles:
                        self.missiles.remove(missile)
                    if asteroid in self.asteroids:
                        self.asteroids.remove(asteroid)
                    SOUND_HIT.play()
                    SCORE += 10
                    if SCORE > TOP_SCORE:
                        TOP_SCORE = SCORE
                        FONT_COLOR_TOP_SCORE = (0,255,0)

    #renders all necessary gameplay items on screen
    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        for asteroid in self.asteroids:
            asteroid.render()

        for bullet in self.bullets:
            bullet.render()

        for building in self.buildings:
            building.render()

        for missile in self.missiles:
            missile.render()

        #display the turret
        pygame.draw.circle(screen, TURRET_COLOR, (WIDTH // 2, HEIGHT - TURRET_HEIGHT), TURRET_RADIUS)
        pygame.draw.line(screen, TURRET_COLOR, (WIDTH // 2, HEIGHT), (WIDTH // 2, HEIGHT - TURRET_HEIGHT), TURRET_RADIUS)

        #display score
        font = pygame.font.Font(None, 36)
        text_score = font.render(f'SCORE: {SCORE}', True, FONT_COLOR)
        screen.blit(text_score, (10,10))

        #display missile availability
        if pygame.time.get_ticks() - LAST_MISSILE_TIME > MISSILE_COOLDOWN:
            font = pygame.font.Font(None, 36)
            text_missiles = font.render('MISSILES READY', True, FONT_COLOR)
            screen.blit(text_missiles, (10,10 + text_score.get_height() + 10))

        #display lives
        font = pygame.font.Font(None, 36)
        text_lives = font.render(f'LIVES: {LIVES}', True, FONT_COLOR)
        screen.blit(text_lives, (WIDTH - text_lives.get_width() - 10,10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP SCORE: {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

        #display fps
        font = pygame.font.Font(None, 36)
        fps = clock.get_fps()
        text_fps = font.render(f'FPS: {fps:.0f}', True, FONT_COLOR)
        screen.blit(text_fps, ((WIDTH // 2) - (text_fps.get_width() // 2), 10 + text_top_score.get_height() + 10))

#start game on title screen
CURRENT_STATE = TitleState()

#exit variable
QUIT_GAME = False

#main loop
while not QUIT_GAME:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            QUIT_GAME = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                QUIT_GAME = True

    #handle events and state transitions
    CURRENT_STATE.handle_events()
    if CURRENT_STATE.next_state:
        CURRENT_STATE = CURRENT_STATE.next_state
    
    #update and render the current state
    CURRENT_STATE.update()
    CURRENT_STATE.render(SCREEN)

    #update display
    pygame.display.update()

    #limit to the fps constant
    clock.tick(FPS)

#quit pygame
pygame.quit()
sys.exit()