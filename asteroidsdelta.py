import pygame
import sys
import math
import random
import json
import numpy as np

#initialize pygame
pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()

#screen constants
WIDTH = pygame.display.Info().current_w
HEIGHT = pygame.display.Info().current_h - 60
#WIDTH,HEIGHT = 800,600
BACKGROUND_COLOR = (0,0,0)

#fps limiter
FPS = 90

#master speed control
SPEED_MULTIPLIER = (10 * FPS) // FPS

#top score display color
FONT_COLOR = (255,0,0)
FONT_COLOR_TOP_SCORE = FONT_COLOR
FONT_COLOR_NEW_TOP_SCORE = (0,255,0)

#ship constants
TURRET_RADIUS = 20
TURRET_HEIGHT = 2 * TURRET_RADIUS
TURRET_COLOR = (255,0,0)
TURRET_SPEED = 0.3 * SPEED_MULTIPLIER
FORCE = 10
SHIP_DENSITY = 1000
MAX_SHIP_SPEED = 250

#bullet constants
BULLET_SPEED = 500
BULLET_RADIUS = 2
BULLET_COLOR = (0,0,255)
BULLET_COOLDOWN = 50
LAST_BULLET_TIME = pygame.time.get_ticks()
BULLET_DENSITY = 10000

#asteroid constants
ASTEROID_SPEED = 100 #pixels per second
ASTEROID_RADIUS = 10
ASTEROID_COLOR = (0,255,0)
ASTEROID_COOLDOWN = 800
LAST_ASTEROID_TIME = pygame.time.get_ticks()
ASTEROID_DENSITY = 100

#clump constants
LAST_CLUMP_TIME = pygame.time.get_ticks()
CLUMP_COOLDOWN = 1500
CLUMP_SPEED = 50
CLUMP_RADIUS = 20
CLUMP_DENSITY = 100
CLUMP_COLOR = (212,175,55)

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
INITIAL_LIVES = 5
INITIAL_SCORE = 0
SCORE = INITIAL_SCORE
LIVES = INITIAL_LIVES

#update score
LAST_SCORE_TIME = pygame.time.get_ticks()

#data file
DATA_FILE = "data.json"

#load data from file
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            top_score = data.get("TOP_SCORE", 0)
            gold = data.get("GOLD", 0)
            return top_score, gold
    except FileNotFoundError:
        return 0, 0
    
#top score
TOP_SCORE, GOLD = load_data()

#save data to file
def save_data():
    data = {"TOP_SCORE": TOP_SCORE, "GOLD": GOLD}
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

#audio constants
SOUND_BULLET = pygame.mixer.Sound("asteroids/audio/bullet.wav")
SOUND_MISSILE = pygame.mixer.Sound("asteroids/audio/missile.wav")
SOUND_HIT = pygame.mixer.Sound("asteroids/audio/hit.wav")
SOUND_EXPLOSION = pygame.mixer.Sound("asteroids/audio/explosion.wav")
SOUND_GAME_OVER = pygame.mixer.Sound("asteroids/audio/gameover.wav")
MUSIC_THEME = pygame.mixer.music.load("asteroids/audio/theme.ogg")
MUSIC_TITLE = pygame.mixer.music.load("asteroids/audio/title.ogg")

#audio mixing
SOUND_BULLET.set_volume(0.3)
SOUND_HIT.set_volume(0.4)

#setup the screen
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ASTEROIDS")

#class for particles
class Particle:
    def __init__(self, position, velocity, acceleration, radius, density, color):
        self.position = position
        self.velocity = velocity
        self.acceleration = acceleration
        self.force = [0, 0]
        self.radius = radius
        self.density = density
        self.color = color
        self.mass = math.pi*self.radius*self.radius*density

    def apply_force(self, force_0, force_1):
        self.force[0] += force_0
        self.force[1] += force_1

    def is_invisible(self):
        if (self.position[0] < 0 or self.position[0] > WIDTH or self.position[1] < 0 or self.position[1] > HEIGHT):
            return True
        else:
            return False

    def update(self, DELTA):
        #update acceleration
        self.acceleration = (self.acceleration[0] + self.force[0] / self.mass, self.acceleration[1] + self.force[1] / self.mass)
        #self.acceleration = (self.force[0] / self.mass, self.force[1] / self.mass)
        

        
        #update velocity
        self.velocity = (self.velocity[0] + self.acceleration[0]*DELTA, self.velocity[1] + self.acceleration[1]*DELTA)

        #update position
        self.position = (self.position[0] + self.velocity[0]*DELTA, self.position[1] + self.velocity[1]*DELTA)

        self.force = [0, 0]
        
    def render(self):
        pygame.draw.circle(SCREEN, self.color, (self.position[0], self.position[1]), self.radius)


#class for tethers
class Tether:
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.distance = np.linalg.norm(np.array(end.position) - np.array(start.position))
        self.color = (255,255,255)

    def update(self, DELTA):
        if np.linalg.norm(np.array(self.end.position) - np.array(self.start.position)) >= self.distance:
            self.apply_forces()

    def apply_forces(self):
        # Calculate the forces on the start and end circles based on the tension in the tether
        m1 = self.start.mass  # Mass of the start circle
        m2 = self.end.mass  # Mass of the end circle

        # Calculate the acceleration components due to tension
        # Tension_x = m1 * a1_x
        a1_x = (self.distance * (self.end.position[0] - self.start.position[0])) / (self.distance * (m1 + m2))

        # Tension_y = m1 * a1_y
        a1_y = (self.distance * (self.end.position[1] - self.start.position[1])) / (self.distance * (m1 + m2))

        # Tension_x = m2 * a2_x
        a2_x = (self.distance * (self.start.position[0] - self.end.position[0])) / (self.distance * (m1 + m2))

        # Tension_y = m2 * a2_y
        a2_y = (self.distance * (self.start.position[1] - self.end.position[1])) / (self.distance * (m1 + m2))

        # Calculate the forces based on the calculated accelerations
        force_start_x = m1 * a1_x
        force_start_y = m1 * a1_y
        force_end_x = m2 * a2_x
        force_end_y = m2 * a2_y

        # Apply these forces to the circles
        self.start.apply_force(force_start_x, force_start_y)
        self.end.apply_force(force_end_x, force_end_y)

    def render(self):
        pygame.draw.aaline(SCREEN, self.color, self.start.position, self.end.position)

#class for clumps
class Clump:
    def __init__(self, position, velocity, acceleration, radius, density, color, count):
        self.position = position
        self.velocity = velocity
        self.acceleration = acceleration
        self.radius = radius
        self.density = density
        self.color = color
        self.init_clump = []
        self.count = count
        self.clump = self.recursive_clump(self.init_clump, self.count)
        self.mass = len(self.clump) * self.density * math.pi * self.radius * self.radius
        self.box = Particle(position, velocity, acceleration, radius, density, color)

    def recursive_clump(self, clump, count):
            position = np.array([self.position[0] + random.uniform(-self.radius, self.radius), self.position[1] + random.uniform(-self.radius, self.radius)])
            if(len(clump) < count):
                clump.append(Particle(position, self.velocity, self.acceleration, self.radius, self.density, self.color))
                return self.recursive_clump(clump, count)
            else:
                return clump

    def update(self, DELTA):
        self.mass = len(self.clump) * self.density * math.pi * self.radius * self.radius + 0.1 #minimum mass to prevent error in particle update
        for particle in self.clump:
            particle.velocity = self.velocity
            particle.mass = self.mass
            particle.update(DELTA)
        self.box.velocity = self.velocity
        self.box.mass = self.mass
        self.box.update(DELTA)
        
    def render(self):
        for particle in self.clump:
            particle.render()

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
        pygame.mixer.music.load("asteroids/audio/title.ogg")
        pygame.mixer.music.play(-1)

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            self.next_state = GameState()
        if pygame.key.get_pressed()[pygame.K_m]:
            self.next_state = MenuState()

    def update(self, DELTA):
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
        text_prompt = font.render("press space to play, m for menu", True, FONT_COLOR)
        screen.blit(text_prompt, ((WIDTH // 2) - (text_prompt.get_width() // 2), (HEIGHT // 2) - (text_prompt.get_height() // 2) + (text.get_height() // 2) + 10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP SCORE: {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

#menu state
class MenuState(State):
    global SCORE, LIVES

    def __init__(self):
        super().__init__()
        pygame.mixer.music.load("asteroids/audio/title.ogg")
        pygame.mixer.music.play(-1)

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            self.next_state = TitleState()

    def update(self, DELTA):
        pass

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        #display title
        font = pygame.font.Font(None, 72)
        text = font.render("MENU", True, FONT_COLOR)
        screen.blit(text, ((WIDTH // 2) - (text.get_width() // 2), (HEIGHT // 2) - (text.get_height() // 2)))

        #display press spacebar
        font = pygame.font.Font(None, 18)
        text_prompt = font.render("press escape for titlescreen", True, FONT_COLOR)
        screen.blit(text_prompt, ((WIDTH // 2) - (text_prompt.get_width() // 2), (HEIGHT // 2) - (text_prompt.get_height() // 2) + (text.get_height() // 2) + 10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP SCORE: {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

#game state
class GameState(State):
    def __init__(self):
        global FONT_COLOR, SCORE, LIVES, FONT_COLOR_TOP_SCORE, SHIP_DENSITY, ASTEROID_DENSITY, BULLET_DENSITY
        super().__init__()
        FONT_COLOR_TOP_SCORE = FONT_COLOR
        SCORE = INITIAL_SCORE
        LIVES = INITIAL_LIVES
        pygame.mixer.music.load("asteroids/audio/theme.ogg")
        pygame.mixer.music.play(-1)
        pygame.time.delay(500)
        self.asteroids = []
        self.ships = [Particle((WIDTH / 2, 2 * HEIGHT / 3), (0, 0), (0, 0), TURRET_RADIUS, SHIP_DENSITY, TURRET_COLOR)]
        self.bullets = []
        self.clumps = []
        self.tethers = []
        

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            self.next_state = TitleState()

    def create_asteroid(self):
        #random initial particle state
        position = np.array([random.uniform(0, WIDTH), 0])
        angle = random.uniform(math.pi/4, 3*math.pi/4)
        speed = ASTEROID_SPEED*random.uniform(0.5, 6)
        velocity = np.array([speed * math.cos(angle), speed * math.sin(angle)])
        #acceleration = np.array([random.uniform(-100, 100),random.uniform(-100, 100)])
        acceleration = np.array([0,0])
        radius = ASTEROID_RADIUS*random.uniform(0.5, 2)
        density = ASTEROID_DENSITY
        color = ASTEROID_COLOR

        #create the asteroid
        new_asteroid = Particle(position, velocity, acceleration, radius, density, color)

        #add asteroid to list
        self.asteroids.append(new_asteroid)

    def create_bullet(self):
        if self.ships and len(self.ships) > 0:

            mouse_x, mouse_y = pygame.mouse.get_pos()
            direction = np.array((mouse_x - self.ships[0].position[0], mouse_y - self.ships[0].position[1]))
            magnitude = np.linalg.norm(direction)
            unit_direction = direction / magnitude

            new_bullet = Particle(self.ships[0].position, unit_direction * BULLET_SPEED, [0,0], BULLET_RADIUS, BULLET_DENSITY, BUILDING_COLOR)
            self.bullets.append(new_bullet)

    def elastic_collision(self, p1, p2):
        v1 = np.array(p1.velocity)
        v2 = np.array(p2.velocity)
        x1 = np.array(p1.position)
        x2 = np.array(p2.position)

        distance = np.linalg.norm(x1 - x2)
        normal = (x2 - x1) / distance

        if (distance <= p1.radius + p2.radius):
            # Calculate relative velocity
            relative_velocity = v2 - v1

            # Calculate the impulse
            impulse = (2 * p1.mass * p2.mass / (p1.mass + p2.mass)) * np.dot(relative_velocity, normal) * normal

            # Update velocities
            p1.velocity = v1 + impulse / p1.mass
            p2.velocity = v2 - impulse / p2.mass

            # Separate the circles to avoid sticking together (assuming they have some overlap)
            overlap = p1.radius + p2.radius - distance
            separation = 0.5 * overlap * normal
            p1.position = x1 - separation
            p2.position = x2 + separation

            return True
        else:
            return False

    #updates position of all items on screen, removes them if a collision is detected or they move off screen
    def update(self, DELTA):
        global LAST_BULLET_TIME, LAST_ASTEROID_TIME, LAST_MISSILE_TIME, LIVES, SCORE, TOP_SCORE, FONT_COLOR, FONT_COLOR_TOP_SCORE, FORCE, MAX_SHIP_SPEED, ASTEROID_COLOR, LAST_CLUMP_TIME, CLUMP_COLOR, GOLD, LAST_SCORE_TIME, FONT_COLOR_NEW_TOP_SCORE

        #update the score
        current_time = pygame.time.get_ticks()
        if current_time - LAST_SCORE_TIME >= 1000:
            SCORE += 1
            if SCORE > TOP_SCORE:
                TOP_SCORE = SCORE
                FONT_COLOR_TOP_SCORE = FONT_COLOR_NEW_TOP_SCORE
            LAST_SCORE_TIME = current_time

        #create asteroids
        if pygame.time.get_ticks() - LAST_ASTEROID_TIME > ASTEROID_COOLDOWN:
            self.create_asteroid()
            LAST_ASTEROID_TIME = pygame.time.get_ticks()
        
        #update asteroids
        for asteroid in self.asteroids:
            asteroid.update(DELTA)
            if (asteroid.is_invisible()):
                self.asteroids.remove(asteroid)

        #CLUMP_COLOR = (random.uniform(0,255), random.uniform(10,255), random.uniform(0,255))

        #asteroid collisions
        for p1 in self.asteroids:
            for p2 in self.asteroids:
                if p1 != p2:
                    self.elastic_collision(p1,p2)
                    

        #update ships
        for ship in self.ships:
            #ship.apply_force(-1*ship.velocity[0], -1*ship.velocity[1])
            ship.update(DELTA)
            if (ship.is_invisible()):
                if ship in self.ships:
                    self.ships.remove(ship)
            if (ship.position[0] <= ship.radius and ship.velocity[0] <= 0) or (ship.position[0] >= WIDTH - ship.radius and ship.velocity[0] >= 0):
                ship.velocity = (-1*ship.velocity[0], ship.velocity[1])
            if (ship.position[1] <= ship.radius and ship.velocity[1] <= 0) or (ship.position[1] >= HEIGHT - ship.radius and ship.velocity[1] >= 0):
                ship.velocity = (ship.velocity[0], -1*ship.velocity[1])


        for ship in self.ships:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                ship.velocity = ((ship.velocity[0],max(ship.velocity[1] - FORCE, -MAX_SHIP_SPEED)))  # Apply an upward force
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                ship.velocity = ((ship.velocity[0], min(ship.velocity[1] + FORCE, MAX_SHIP_SPEED)))  # Apply a downward force
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                ship.velocity = ((max(ship.velocity[0] -FORCE, -MAX_SHIP_SPEED), ship.velocity[1]))  # Apply a leftward force
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                ship.velocity = ((min(ship.velocity[0] + FORCE, MAX_SHIP_SPEED), ship.velocity[1]))
            

        #ship collisions
        for p1 in self.asteroids:
            for p2 in self.ships:
                if p1 != p2:
                    if self.elastic_collision(p1,p2):
                        LIVES -= 1
                        SOUND_EXPLOSION.play()
                        if LIVES <= 0:
                            if ship in self.ships:
                                self.ships.remove(ship)
                            LIVES = 4
                            save_data()
                            SOUND_GAME_OVER.play()
                            self.next_state = TitleState()

                      
        #update bullets
        if (pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_SPACE]) and pygame.time.get_ticks() - LAST_BULLET_TIME > BULLET_COOLDOWN:
            self.create_bullet()
            LAST_BULLET_TIME = pygame.time.get_ticks()
            SOUND_BULLET.play()
        for bullet in self.bullets:
            bullet.update(DELTA)
            if (bullet.is_invisible()):
                if bullet in self.bullets:
                    self.bullets.remove(bullet)

        
        #create tethers
        if pygame.mouse.get_pressed()[2]:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for clump in self.clumps:
                for circle in clump.clump:
                    distance = np.linalg.norm(np.array(circle.position) - np.array((mouse_x, mouse_y)))
                    if distance <= circle.radius:
                        if self.ships:  # Check if there are any ships
                            self.tethers.append(Tether(self.ships[0], circle))

        #create all tethers
        if pygame.mouse.get_pressed()[1]:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for clump in self.clumps:
                for circle in clump.clump:
                    if self.ships:  # Check if there are any ships
                        self.tethers.append(Tether(self.ships[0], circle))

        #update tethers
        for tether in self.tethers:
            tether.update(DELTA)
            present = False
            for clump in self.clumps:
                for particle in clump.clump:
                    if (tether.end in clump.clump):
                        present = True
            if not present:
                self.tethers.remove(tether)
                

        #bullet-asteroid collisions
        for asteroid in self.asteroids:
            for bullet in self.bullets:
                if asteroid != bullet:
                    self.elastic_collision(asteroid,bullet)
                        

        #create clumps
        if pygame.time.get_ticks() - LAST_CLUMP_TIME > CLUMP_COOLDOWN:
            LAST_CLUMP_TIME = pygame.time.get_ticks()

            position = np.array([random.uniform(0, WIDTH), 0])
            angle = random.uniform(math.pi/4, 3*math.pi/4)
            speed = CLUMP_SPEED*random.uniform(0.5, 6)
            velocity = np.array([speed * math.cos(angle), speed * math.sin(angle)])
            #acceleration = np.array([random.uniform(-100, 100),random.uniform(-100, 100)])
            acceleration = np.array([0,0])
            radius = CLUMP_RADIUS*random.uniform(0.5, 2)
            density = CLUMP_DENSITY
            color = CLUMP_COLOR

            self.clumps.append(Clump(position, velocity, acceleration, radius, density, color, 10))

        #update clumps
        for clump in self.clumps:
            clump.update(DELTA)
            for particle in clump.clump:
                if (particle.is_invisible()):
                        if particle in clump.clump:
                            clump.clump.remove(particle)

        #clump on asteroids and ship collisions
        for list in [self.asteroids, self.ships]:
            for p1 in list:
                for clump in self.clumps:
                    for p2 in clump.clump:
                        if p1 != p2:
                            if self.elastic_collision(p1,p2):
                                clump.velocity = p2.velocity

        #clump on bullet collision
        for p1 in self.bullets:
                for clump in self.clumps:
                    for p2 in clump.clump:
                        if p1 != p2:
                            if self.elastic_collision(p1,p2):
                                clump.velocity = p2.velocity
                                if p2 in clump.clump:
                                    clump.clump.remove(p2)
                                GOLD += 1

        #clump on clump collision simplified
        for clump1 in self.clumps:
            for clump2 in self.clumps:
                if clump1 != clump2:
                    p1 = clump1.box
                    p2 = clump2.box
                    if p1 != p2:
                        if self.elastic_collision(p1,p2):
                            clump1.velocity = p1.velocity
                            clump2.velocity = p2.velocity

        '''
        #clump on clump collisions (needs pruning step to be functionally efficient)
        for clump1 in self.clumps:
            for clump2 in self.clumps:
                for p1 in clump1.clump:
                    for p2 in clump2.clump:
                        if p1 != p2:
                            if self.elastic_collision(p1,p2):
                                clump1.velocity = p1.velocity
                                clump2.velocity = p2.velocity
        '''                  

    #renders all necessary gameplay items on screen
    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        for asteroid in self.asteroids:
            asteroid.render()

        for tether in self.tethers:
            tether.render()

        for ship in self.ships:
            ship.render()

        for bullet in self.bullets:
            bullet.render() 

        for clump in self.clumps:
            clump.render()
        

        #display score
        font = pygame.font.Font(None, 36)
        text_score = font.render(f'SCORE: {SCORE}', True, FONT_COLOR)
        screen.blit(text_score, (10,10))

        '''
        #display missile availability
        if pygame.time.get_ticks() - LAST_MISSILE_TIME > MISSILE_COOLDOWN:
            font = pygame.font.Font(None, 36)
            text_missiles = font.render('MISSILES READY', True, FONT_COLOR)
            screen.blit(text_missiles, (10,10 + text_score.get_height() + 10))
        '''

        #display gold
        font = pygame.font.Font(None, 36)
        text_gold = font.render(f'GOLD: {GOLD}', True, FONT_COLOR)
        screen.blit(text_gold, (10,10 + text_score.get_height() + 10))

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

    #limit to the fps constant
    DELTA = clock.tick(FPS) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            QUIT_GAME = True
      

    #handle events and state transitions
    CURRENT_STATE.handle_events()
    if CURRENT_STATE.next_state:
        CURRENT_STATE = CURRENT_STATE.next_state
    
    #update and render the current state
    CURRENT_STATE.update(DELTA)
    CURRENT_STATE.render(SCREEN)

    #update display
    pygame.display.update()



#quit pygame
pygame.quit()
sys.exit()