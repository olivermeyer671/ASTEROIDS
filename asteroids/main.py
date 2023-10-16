import asyncio
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
music = pygame.mixer.music

#screen constants
WIDTH = pygame.display.Info().current_w
HEIGHT = pygame.display.Info().current_h - 60
#WIDTH,HEIGHT = 800,600
BACKGROUND_COLOR = (0,0,0)

#fps limiter
FPS = 60

#font colors
FONT_COLOR = (255,0,0)
FONT_COLOR_TOP_SCORE = FONT_COLOR
FONT_COLOR_NEW_TOP_SCORE = (0,255,0)

#world constants
GRAVITY = 9.8 #N/Kg
FRICTION_COEFFICIENT = 0.6
LAST_COLOR_CHANGE_TIME = pygame.time.get_ticks()
COLOR_CHANGE_COOLDOWN = 200
DIFFICULTY = 1
DIFFICULTY_RATE = 0.01

#ship constants
SHIP_RADIUS = 20
SHIP_COLOR = (0,0,255)
SHIP_ACCELERATION = 1000 #pixels per second per second
SHIP_DENSITY = 10
MAX_SHIP_SPEED = 250

#bullet constants
BULLET_SPEED = 1000
BULLET_RADIUS = 2
BULLET_COLOR = (0,0,255)
BULLET_COOLDOWN = 50
LAST_BULLET_TIME = pygame.time.get_ticks()
BULLET_DENSITY = 100

#asteroid constants
ASTEROID_SPEED = 100 * (DIFFICULTY - 0.2) #pixels per second
ASTEROID_RADIUS = 10
ASTEROID_COLOR = (255,0,0)
ASTEROID_COOLDOWN = 800 * (1 / (DIFFICULTY - 0.0))
LAST_ASTEROID_TIME = pygame.time.get_ticks()
ASTEROID_DENSITY = 1
COLOR_DIRECTION = 1

#clump constants
LAST_CLUMP_TIME = pygame.time.get_ticks()
CLUMP_COOLDOWN = 5000 * (DIFFICULTY - 0.1)
CLUMP_SPEED = 100 * (DIFFICULTY - 0.2)
CLUMP_RADIUS = 10
CLUMP_DENSITY = 1
CLUMP_COLOR = (212,175,55)
CLUMP_COUNT = 10

#tether constants
TETHER_COLOR = (240,240,240)
TETHER_COST = 100

#portal constants
PORTAL_SPEED = 50 * (DIFFICULTY - 0.0)
PORTAL_RADIUS = 40
PORTAL_DENSITY = 1
PORTAL_COLOR = (0,255,255)
LAST_PORTAL_TIME = pygame.time.get_ticks()
PORTAL_COOLDOWN = 10000 * (DIFFICULTY - 0.0)

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
            gold = data.get("GOLD", 100)
            tethers = data.get("TETHERS", 1)
            return top_score, gold, tethers
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return 0, 100, 1
    
#persistant data
TOP_SCORE, GOLD, TETHERS = load_data()

#save data to file
def save_data():
    data = {"TOP_SCORE": TOP_SCORE, "GOLD": GOLD, "TETHERS": TETHERS}
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
SOUND_HIT.set_volume(0.1)
SOUND_EXPLOSION.set_volume(0.5)

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
        self.active = True

    def apply_friction(self, coefficient):
        velocity_magnitude = np.linalg.norm(self.velocity)
        normal_force = GRAVITY  * self.mass
        friction_force = coefficient * velocity_magnitude * normal_force
        # Calculate the direction of the friction force (opposite to velocity)
        if velocity_magnitude > 0:
            friction_direction = (-self.velocity[0] / velocity_magnitude, -self.velocity[1] / velocity_magnitude)
        else:
            friction_direction = (0, 0)
        # Calculate the friction force components
        friction_force_x = friction_force * friction_direction[0]
        friction_force_y = friction_force * friction_direction[1]
        # Apply the friction force as an acceleration
        self.apply_force(friction_force_x, friction_force_y)

    def apply_force(self, force_0, force_1):
        self.force[0] += force_0
        self.force[1] += force_1

    def is_invisible(self):
        if (self.position[0] < 0 or self.position[0] > WIDTH or self.position[1] < 0 or self.position[1] > HEIGHT):
            return True
        else:
            return False

    def update(self, DELTA):
        if self.is_invisible():
            self.active = False

        else:
            #update acceleration
            self.acceleration = (self.force[0] / self.mass, self.force[1] / self.mass)
            
            #update velocity
            self.velocity = (self.velocity[0] + self.acceleration[0]*DELTA, self.velocity[1] + self.acceleration[1]*DELTA)

            #update position
            self.position = (self.position[0] + self.velocity[0]*DELTA, self.position[1] + self.velocity[1]*DELTA)

            #remove applied force
            self.force = [0, 0]
        
    def render(self, color):
        pygame.draw.circle(SCREEN, color, (self.position[0], self.position[1]), self.radius)


#class for tethers
class Tether:
    def __init__(self, start_particle, end_clump, end_particle):
        self.start_particle = start_particle
        self.end_clump = end_clump
        self.end_particle = end_particle
        self.distance = np.linalg.norm(np.array(end_particle.position) - np.array(start_particle.position))
        self.color = TETHER_COLOR
        self.active = True

    def update(self, DELTA):
        if self.end_particle not in self.end_clump.clump:
            self.active = False
        else:
            # Calculate the displacement vector between the particles
            displacement = np.array(self.end_particle.position) - np.array(self.start_particle.position)
            current_length = np.linalg.norm(displacement)
            if current_length != 0:
                #force_magnitude = current_length - self.distance
                force_magnitude = current_length - 2*(self.end_particle.radius + self.start_particle.radius)
                force_direction = displacement / current_length
                force = force_direction * force_magnitude * 10000

                # Check if the tether has become tight
                    #if current_length > self.distance:  # Change to self.distance
                self.start_particle.apply_force(force[0], force[1])
                self.end_clump.box.apply_force(-force[0], -force[1])

    def render(self, color):
        pygame.draw.aaline(SCREEN, color, self.start_particle.position, self.end_particle.position)

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
        self.active = True

    def recursive_clump(self, clump, count):
            position = np.array([self.position[0] + random.uniform(-self.radius, self.radius), self.position[1] + random.uniform(-self.radius, self.radius)])
            if(len(clump) < count):
                clump.append(Particle(position, self.velocity, self.acceleration, self.radius, self.density, self.color))
                return self.recursive_clump(clump, count)
            else:
                return clump

    def update(self, DELTA):
        self.velocity = self.box.velocity
        self.acceleration = self.box.acceleration
        self.mass = len(self.clump) * self.density * math.pi * self.radius * self.radius  + 0.000001 #minimum mass to prevent error in particle update
        self.box.mass = self.mass
        self.box.update(DELTA)
        for particle in self.clump:
            if not particle.active:
                self.clump.remove(particle)
            else:
                particle.velocity = self.velocity
                particle.acceleration = self.acceleration
                particle.mass = self.mass
                particle.update(DELTA)


        if len(self.clump) == 0:
            self.active = False
        
    def render(self, color):
        for particle in self.clump:
            particle.render(color)

#state manager interface
class State:
    def __init__(self):
        self.next_state = None
    
    def handle_events(self):
        pass

    def update(self, DELTA):
        pass

    def render(self, screen):
        self.screen = screen

#initial state to start music
class FirstState(State):

    def __init__(self):
        super().__init__()
        music.load("audio/title.ogg")
        music.play(-1)
        #pygame.time.delay(100)

    def handle_events(self):
        self.next_state = TitleState()


    def update(self, DELTA):
        pass

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

#title state
class TitleState(State):
    global SCORE, LIVES

    def __init__(self):
        super().__init__()

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            music.stop()
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
        text_prompt = font.render("Press  [ space ]  to  play.  Press  [ m ]  for  MENU:  Instructions,  Controls,  Store", True, FONT_COLOR)
        screen.blit(text_prompt, ((WIDTH // 2) - (text_prompt.get_width() // 2), (HEIGHT // 2) - (text_prompt.get_height() // 2) + (text.get_height() // 2) + 10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP  SCORE :  {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

#menu state
class MenuState(State):
    global SCORE, LIVES, GOLD, TETHERS

    def __init__(self):
        super().__init__()
        self.key_1_pressed = False

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            self.next_state = TitleState()

    def update(self, DELTA):
        global GOLD, TETHERS
        pressed_1 = pygame.key.get_pressed()[pygame.K_1]
        if pressed_1 and not self.key_1_pressed:
            if GOLD >= TETHER_COST:
                GOLD -= TETHER_COST
                TETHERS += 1
            self.key_1_pressed = True
        elif not pressed_1:
            self.key_1_pressed = False

    def render(self, screen):
        #clear screen
        screen.fill(BACKGROUND_COLOR)

        #display title
        font = pygame.font.Font(None, 72)
        text = font.render("MENU", True, FONT_COLOR)
        screen.blit(text, ((WIDTH // 2) - (text.get_width() // 2), (HEIGHT // 2) - (text.get_height() // 2)))

        #display press spacebar
        font = pygame.font.Font(None, 18)
        text_prompt = font.render("INSTRUCTIONS :  avoid  the  red  asteroids.  use  tethers  to  drag  gold  asteroids  into  rainbow  portals.  Press  [ escape ]  for  Title  Screen.", True, FONT_COLOR)
        screen.blit(text_prompt, ((WIDTH // 2) - (text_prompt.get_width() // 2), (HEIGHT // 2) - (text_prompt.get_height() // 2) + (text.get_height() // 2) + 10))

        #display controls
        font = pygame.font.Font(None, 18)
        text_move = font.render("MOVEMENT :  wasd  /  arrow  keys", True, FONT_COLOR)
        screen.blit(text_move, ((WIDTH // 2) - (text_move.get_width() // 2), (HEIGHT // 2) - (text_move.get_height() // 2) + (text.get_height() // 2 + 10) + (text_prompt.get_height() // 2 + 10)))

        #display controls
        font = pygame.font.Font(None, 18)
        text_shoot = font.render("SHOOT :  space  key  /  left  click  towards  target", True, FONT_COLOR)
        screen.blit(text_shoot, ((WIDTH // 2) - (text_shoot.get_width() // 2), (HEIGHT // 2) - (text_shoot.get_height() // 2) + (text.get_height() // 2 + 10) + (text_prompt.get_height() // 2 + 10) + (text_move.get_height() // 2 + 10)))

        #display controls
        font = pygame.font.Font(None, 18)
        text_tether = font.render("TETHER :  return  key  /  right  click  on  gold  asteroid", True, FONT_COLOR)
        screen.blit(text_tether, ((WIDTH // 2) - (text_tether.get_width() // 2), (HEIGHT // 2) - (text_tether.get_height() // 2) + (text.get_height() // 2 + 10) + (text_prompt.get_height() // 2 + 10) + (text_move.get_height() // 2 + 10) + (text_shoot.get_height() // 2 + 10)))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP  SCORE :  {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

        #display store
        font = pygame.font.Font(None, 36)
        text_score = font.render(f'STORE:', True, FONT_COLOR)
        screen.blit(text_score, (10,10))

        #display gold
        font = pygame.font.Font(None, 36)
        text_gold = font.render(f'GOLD:  {GOLD}', True, CLUMP_COLOR)
        screen.blit(text_gold, (10,10 + text_score.get_height() + 10))

        #display tethers
        font = pygame.font.Font(None, 36)
        text_tethers = font.render(f'Tethers:  {TETHERS} (${TETHER_COST}  each,  to  buy  more  press  1)', True, TETHER_COLOR)
        screen.blit(text_tethers, (10,10 + text_score.get_height() + 10 + text_gold.get_height() + 10))

#game state
class GameState(State):
    def __init__(self):
        global FONT_COLOR, SCORE, LIVES, FONT_COLOR_TOP_SCORE, SHIP_DENSITY, ASTEROID_DENSITY, BULLET_DENSITY
        super().__init__()
        FONT_COLOR_TOP_SCORE = FONT_COLOR
        SCORE = INITIAL_SCORE
        LIVES = INITIAL_LIVES
        music.load("audio/theme.ogg")
        music.play(-1)
        pygame.time.delay(500)
        self.asteroids = []
        self.ships = [Particle((WIDTH / 2, 2 * HEIGHT / 3), (0, 0), (0, 0), SHIP_RADIUS, SHIP_DENSITY, SHIP_COLOR)]
        self.bullets = []
        self.clumps = []
        self.tethers = []
        self.portals = []
        

    def handle_events(self):
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            music.stop()
            self.next_state = FirstState()

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

            new_bullet = Particle(self.ships[0].position, unit_direction * BULLET_SPEED, [0,0], BULLET_RADIUS, BULLET_DENSITY, BULLET_COLOR)
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
        global LAST_BULLET_TIME, LAST_ASTEROID_TIME, LIVES, SCORE, TOP_SCORE, FONT_COLOR, FONT_COLOR_TOP_SCORE, FORCE, MAX_SHIP_SPEED, ASTEROID_COLOR, LAST_CLUMP_TIME, CLUMP_COLOR, GOLD, LAST_SCORE_TIME, FONT_COLOR_NEW_TOP_SCORE, TETHERS, LAST_PORTAL_TIME, LAST_COLOR_CHANGE_TIME, PORTAL_COLOR, DIFFICULTY_RATE, DIFFICULTY, COLOR_DIRECTION

        #update the score
        current_time = pygame.time.get_ticks()
        if current_time - LAST_SCORE_TIME >= 1000:
            SCORE += 1
            if SCORE > TOP_SCORE:
                TOP_SCORE = SCORE
                FONT_COLOR_TOP_SCORE = FONT_COLOR_NEW_TOP_SCORE
            LAST_SCORE_TIME = current_time
            #update the difficulty
            DIFFICULTY = 1 + SCORE * DIFFICULTY_RATE

        

        #remove inactive objects
        self.asteroids = [asteroid for asteroid in self.asteroids if asteroid.active]
        self.ships = [ship for ship in self.ships if ship.active]
        self.bullets = [bullet for bullet in self.bullets if bullet.active]
        self.clumps = [clump for clump in self.clumps if clump.active]
        self.tethers = [tether for tether in self.tethers if tether.active]
        self.portals = [portal for portal in self.portals if portal.active]

        #update colors
        if pygame.time.get_ticks() - LAST_COLOR_CHANGE_TIME > COLOR_CHANGE_COOLDOWN:
            PORTAL_COLOR = (random.uniform(0,222), random.uniform(10,222), random.uniform(0,222))
            LAST_COLOR_CHANGE_TIME = pygame.time.get_ticks()
        if (ASTEROID_COLOR[0] == 100):
            COLOR_DIRECTION = 5
        if (ASTEROID_COLOR[0] == 255):
            COLOR_DIRECTION = -5
        ASTEROID_COLOR = ((ASTEROID_COLOR[0] + COLOR_DIRECTION),0,0)

        #create portals
        if pygame.time.get_ticks() - LAST_PORTAL_TIME > PORTAL_COOLDOWN:
            #random initial particle state
            position = np.array([random.uniform(0, WIDTH), 0])
            angle = random.uniform(math.pi/4, 3*math.pi/4)
            speed = PORTAL_SPEED*random.uniform(0.5, 6)
            velocity = np.array([speed * math.cos(angle), speed * math.sin(angle)])
            #acceleration = np.array([random.uniform(-100, 100),random.uniform(-100, 100)])
            acceleration = np.array([0,0])
            radius = PORTAL_RADIUS*random.uniform(0.5, 2)
            density = PORTAL_DENSITY
            color = PORTAL_COLOR

            new_portal = Particle(position, velocity, acceleration, radius, density, color)
            self.portals.append(new_portal)
            LAST_PORTAL_TIME = pygame.time.get_ticks()

        #update portals
        for portal in self.portals:
            portal.update(DELTA)

        #portal collisions
        for portal in self.portals:
            for tether in self.tethers:
                clump = tether.end_clump
                for p1 in clump.clump:
                    distance = np.linalg.norm(np.array(p1.position) - np.array(portal.position))
                    if distance < portal.radius:
                        p1.active = False
                        GOLD += 10
        
        #create asteroids
        if pygame.time.get_ticks() - LAST_ASTEROID_TIME > ASTEROID_COOLDOWN:
            self.create_asteroid()
            LAST_ASTEROID_TIME = pygame.time.get_ticks()
        
        #update asteroids
        for asteroid in self.asteroids:
            asteroid.update(DELTA)

        #asteroid collisions
        for p1 in self.asteroids:
            for p2 in self.asteroids:
                if p1 != p2:
                    self.elastic_collision(p1,p2)
                    
        #update ships
        for ship in self.ships:
            ship.apply_friction(0.1)
            ship.update(DELTA)
            if (ship.position[0] <= ship.radius and ship.velocity[0] <= 0) or (ship.position[0] >= WIDTH - ship.radius and ship.velocity[0] >= 0):
                ship.velocity = (-1*ship.velocity[0], ship.velocity[1])
            if (ship.position[1] <= ship.radius and ship.velocity[1] <= 0) or (ship.position[1] >= HEIGHT - ship.radius and ship.velocity[1] >= 0):
                ship.velocity = (ship.velocity[0], -1*ship.velocity[1])

        #ship controls
        for ship in self.ships:
            FORCE = SHIP_ACCELERATION * ship.mass
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                    ship.apply_force(0 ,-FORCE)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    ship.apply_force(0 , FORCE)
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    ship.apply_force(-FORCE , 0)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    ship.apply_force(FORCE , 0)
            
        #ship collisions
        for p1 in self.asteroids:
            for p2 in self.ships:
                if p1 != p2:
                    if self.elastic_collision(p1,p2):
                        LIVES -= 1
                        SOUND_EXPLOSION.play()
                        if LIVES <= 0:
                            ship.active = False
                            LIVES = 4
                            save_data()
                            SOUND_GAME_OVER.play()
                            music.stop()
                            self.next_state = FirstState()
                
        #update bullets
        if (pygame.mouse.get_pressed()[0] and pygame.time.get_ticks() - LAST_BULLET_TIME > BULLET_COOLDOWN):
            self.create_bullet()
            LAST_BULLET_TIME = pygame.time.get_ticks()
            SOUND_BULLET.play()
        if (pygame.key.get_pressed()[pygame.K_SPACE] and pygame.time.get_ticks() - LAST_BULLET_TIME > BULLET_COOLDOWN):
            self.bullets.append(Particle(self.ships[0].position, (self.ships[0].velocity[0], self.ships[0].velocity[1] - BULLET_SPEED), (0,0), BULLET_RADIUS, BULLET_DENSITY, BULLET_COLOR))
            LAST_BULLET_TIME = pygame.time.get_ticks()
            SOUND_BULLET.play()
        for bullet in self.bullets:
            bullet.update(DELTA)

        #create tethers on entire asteroid clump
        if (TETHERS > 0):
            if pygame.mouse.get_pressed()[2]:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                for clump in self.clumps:
                    flag = False
                    for circle in clump.clump:
                        distance = np.linalg.norm(np.array(circle.position) - np.array((mouse_x, mouse_y)))
                        if distance <= circle.radius:
                            flag = True
                        if flag:
                            if not any(tether.end_clump == clump for tether in self.tethers):
                                for circle in clump.clump:
                                    self.tethers.append(Tether(self.ships[0], clump, circle))
                                TETHERS -= 1

        #create tethers on return key press
        if (TETHERS > 0):
            if pygame.key.get_pressed()[pygame.K_RETURN]:
                closest_clump = None
                closest_distance = math.inf
                for clump in self.clumps:
                    flag = False
                    for circle in clump.clump:
                        distance = np.linalg.norm(np.array(circle.position) - np.array((self.ships[0].position)))
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_clump = clump
                if closest_clump:
                    if not any(tether.end_clump == closest_clump for tether in self.tethers):
                        for circle in closest_clump.clump:
                            self.tethers.append(Tether(self.ships[0], closest_clump, circle))
                        TETHERS -= 1

        #update tethers
        for tether in self.tethers:
            tether.end_clump.box.apply_friction(FRICTION_COEFFICIENT / 10)
            tether.update(DELTA)
            
        #bullet-asteroid collisions
        for asteroid in self.asteroids:
            for bullet in self.bullets:
                if asteroid != bullet:
                    if self.elastic_collision(asteroid,bullet):
                        SOUND_HIT.play()
                        
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

            self.clumps.append(Clump(position, velocity, acceleration, radius, density, color, CLUMP_COUNT))

        #update clumps
        for clump in self.clumps:
            clump.update(DELTA)
        
        #clump on asteroids and ship collisions
        for list in [self.asteroids, self.ships]:
            for p1 in list:
                for clump in self.clumps:
                        p2 = clump.box
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
                                p2.active = False
                                GOLD += 1
                                SOUND_HIT.play()

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

        for portal in self.portals:
            portal.render(PORTAL_COLOR)

        for asteroid in self.asteroids:
            asteroid.render(ASTEROID_COLOR)

        for tether in self.tethers:
            tether.render(TETHER_COLOR)

        for bullet in self.bullets:
            bullet.render(BULLET_COLOR) 

        for clump in self.clumps:
            clump.render(CLUMP_COLOR)

        for ship in self.ships:
            ship.render(SHIP_COLOR)
        

        #display score
        font = pygame.font.Font(None, 36)
        text_score = font.render(f'SCORE : {SCORE}', True, FONT_COLOR)
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
        text_gold = font.render(f'GOLD :  {GOLD}', True, CLUMP_COLOR)
        screen.blit(text_gold, (10,10 + text_score.get_height() + 10))

        #display tethers
        font = pygame.font.Font(None, 36)
        text_tethers = font.render(f'TETHERS :  {TETHERS}', True, TETHER_COLOR)
        screen.blit(text_tethers, (10,10 + text_score.get_height() + 10 + text_gold.get_height() + 10))

        #display lives
        font = pygame.font.Font(None, 36)
        text_lives = font.render(f'LIVES :  {LIVES}', True, SHIP_COLOR)
        screen.blit(text_lives, (WIDTH - text_lives.get_width() - 10,10))

        #display difficulty factor
        font = pygame.font.Font(None, 36)
        text_difficulty = font.render(f'DIFFICULTY :  {-100 + 100*DIFFICULTY:.0f}%', True, FONT_COLOR)
        screen.blit(text_difficulty, (WIDTH - text_difficulty.get_width() - 10, 10 + text_lives.get_height() + 10))

        #display top score
        font = pygame.font.Font(None, 36)
        text_top_score = font.render(f'TOP  SCORE :  {TOP_SCORE}', True, FONT_COLOR_TOP_SCORE)
        screen.blit(text_top_score, ((WIDTH // 2) - (text_top_score.get_width() // 2), 10))

        #display fps
        font = pygame.font.Font(None, 36)
        fps = clock.get_fps()
        text_fps = font.render(f'FPS :  {fps:.0f}', True, FONT_COLOR)
        screen.blit(text_fps, ((WIDTH // 2) - (text_fps.get_width() // 2), 10 + text_top_score.get_height() + 10))

#start game on title screen
CURRENT_STATE = FirstState()

#exit variable
QUIT_GAME = False

#main loop
async def main():
    global CURRENT_STATE
    while True:

        #limit to the fps constant
        DELTA = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_data()
                QUIT_GAME = True
        

        #handle events and state transitions
        CURRENT_STATE.handle_events()
        if CURRENT_STATE.next_state:
            save_data()
            CURRENT_STATE = CURRENT_STATE.next_state
        
        #update and render the current state
        CURRENT_STATE.update(DELTA)
        CURRENT_STATE.render(SCREEN)

        #update display
        pygame.display.update()

        await asyncio.sleep(0)

asyncio.run(main())