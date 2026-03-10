import pygame
from pygame import mixer
import os
import random
import csv
import button
import imageio

mixer.init()
pygame.init()

# helper for safe image loading
def safe_load_image(path, scale=None):
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        return img
    else:
        # Если файла нет, возвращаем пустую поверхность (ярко-розовую для заметности)
        size = scale if scale else (SCREEN_HEIGHT // 16, SCREEN_HEIGHT // 16) # Fallback TILE_SIZE
        img = pygame.Surface(size)
        img.fill((255, 0, 255)) # PINK/Magenta placeholder
        return img

SCREEN_WIDTH = 1366
SCREEN_HEIGHT = 768

# Create a display surface object of specific dimension
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('2dminidoom')

# Creating a new clock object to track the amount of time
clock = pygame.time.Clock()
# FPS (Frames Per Second)
FPS = 60

# define game variables
GRAVITY = 0.75
SCROLL_THRESH = 200
ROWS = 16
COLS = 150
TILE_SIZE = SCREEN_HEIGHT // ROWS
TILE_TYPES = 21
MAX_LEVELS = 1
screen_scroll = 0
bg_scroll = 0
level = 1
start_game = False
start_intro = False
show_video = True  
show_death_video = False  

# define player action variables
moving_left = False
moving_right = False
shoot = False
grenade = False
grenade_thrown = False

# create sprite groups
demon_group = pygame.sprite.Group()
plasma_group = pygame.sprite.Group()
rocket_group = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()
crate_group = pygame.sprite.Group()
decoration_group = pygame.sprite.Group()
water_group = pygame.sprite.Group()
exit_group = pygame.sprite.Group()

# load music and sounds
pygame.mixer.music.load('audio/music2.mp3')
pygame.mixer.music.set_volume(0.4) 
jump_fx = pygame.mixer.Sound('audio/jump.wav')
jump_fx.set_volume(0.05)
shot_fx = pygame.mixer.Sound('audio/shot.wav')
shot_fx.set_volume(0.05)
grenade_fx = pygame.mixer.Sound('audio/grenade.wav')
grenade_fx.set_volume(0.05)

# load images
# button images 
restart_img = safe_load_image('img/restart_btn.png') # Load at original size to avoid stretching

# background 
doom_bg = safe_load_image('doom.png', (SCREEN_WIDTH, SCREEN_HEIGHT))

# store tiles in a list
img_list = []
for x in range(TILE_TYPES):
    img = safe_load_image(f'img/tile/{x}.png', (TILE_SIZE, TILE_SIZE))
    img_list.append(img)

# plasma bolt
plasma_img = safe_load_image('img/icons/bullet.png', (20, 10))
# doom rocket
rocket_img = safe_load_image('img/icons/grenade.png')
# supply crates
health_crate_img = safe_load_image('img/icons/health_box.png', (TILE_SIZE, TILE_SIZE))
ammo_crate_img = safe_load_image('img/icons/ammo_box.png', (TILE_SIZE, TILE_SIZE))
rocket_crate_img = safe_load_image('img/icons/grenade_box.png', (TILE_SIZE, TILE_SIZE))

supply_crates = {
    'Health'    : health_crate_img,
    'Ammo'      : ammo_crate_img,
    'Grenade'   : rocket_crate_img
}

PLAYER_WIDTH = 50  
PLAYER_HEIGHT = 80
ENEMY_WIDTH = 70
ENEMY_HEIGHT = 80

player_img = safe_load_image('img/player.png', (PLAYER_WIDTH, PLAYER_HEIGHT))
enemy_img = safe_load_image('img/enemy.png', (ENEMY_WIDTH, ENEMY_HEIGHT))

# define colours
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# define font
font = pygame.font.SysFont('Futura', 30)


def play_video(video_path, audio_path=None, loop=False, show_restart=False, audio_volume=0.6):
    try:
        video = imageio.get_reader(video_path)
        fps = video.get_meta_data()['fps']
        
        if audio_path and os.path.exists(audio_path):
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(-1 if loop else 1)  
            pygame.mixer.music.set_volume(audio_volume)  
        
        video_playing = True
        video_loops = 0
        max_loops = -1 if loop else 1  
        
        while video_playing:
            for frame in video.iter_data():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.mixer.music.stop()
                        video.close()
                        return False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                            pygame.mixer.music.stop()
                            video.close()
                            return True
                
                frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                frame_surface = pygame.transform.scale(frame_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
                
                screen.blit(frame_surface, (0, 0))
                
                if show_restart:
                    if restart_button.draw(screen):
                        pygame.mixer.music.stop()
                        video.close()
                        return "restart"
                
                pygame.display.update()
                clock.tick(fps)
            
            video_loops += 1
            if max_loops != -1 and video_loops >= max_loops:
                video_playing = False
            else:
                video.close()
                video = imageio.get_reader(video_path)
        
        video.close()
        if audio_path and os.path.exists(audio_path):
            pygame.mixer.music.stop()
        return True
    except Exception as e:
        print(f"РћС€РёР±РєР° РїСЂРё РІРѕСЃРїСЂРѕРёР·РІРµРґРµРЅРёРё РІРёРґРµРѕ: {e}")
        return False

def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))

def draw_bg():
    width = doom_bg.get_width()
    for x in range(5):
        screen.blit(doom_bg, ((x * width) - bg_scroll * 0.5, 0))

# function to reset level
def reset_level():
    demon_group.empty()
    plasma_group.empty()
    rocket_group.empty()
    explosion_group.empty()
    crate_group.empty()
    decoration_group.empty()
    water_group.empty()
    exit_group.empty()
    # create empty tile list
    data = []
    for row in range(ROWS):
        r = [-1] * COLS
        data.append(r)
    return data

def load_level(level):
    # create empty tile list
    data = reset_level()
    # load in level data and create hell_map
    with open(f'level{level}_data.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for x, row in enumerate(reader):
            for y, tile in enumerate(row):
                data[x][y] = int(tile)
    hell_map = HellMap()
    player, health_bar = hell_map.process_data(data)
    return data, hell_map, player, health_bar

class DoomGuy(pygame.sprite.Sprite):
    def __init__(self, char_type, x, y, speed, ammo, grenades):
        pygame.sprite.Sprite.__init__(self)
        self.alive = True
        self.char_type = char_type
        self.speed = speed
        self.ammo = ammo
        self.start_ammo = ammo
        self.shoot_cooldown = 0
        self.grenades = grenades
        self.health = 100
        self.max_health = self.health
        self.direction = 1
        self.vel_y = 0
        self.jump = False
        self.in_air = True
        self.flip = False
    
        if self.char_type == 'player':
            self.image = player_img
        else:
            self.image = enemy_img
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        
        # ai specific variables
        self.move_counter = 0
        self.vision = pygame.Rect(0, 0, 150, 20)
        self.idling = False
        self.idling_counter = 0

    def update(self):
        self.check_alive()
        # update cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def shoot(self):
        if self.shoot_cooldown == 0 and self.ammo > 0:
            self.shoot_cooldown = 20
            plasma = PlasmaBolt(self.rect.centerx + (0.75 * self.rect.size[0] * self.direction), self.rect.centery, self.direction)
            plasma_group.add(plasma)
            # reduce ammo
            self.ammo -= 1
            shot_fx.play()

    def throw_rocket(self):
        if self.grenades > 0:
            rocket = DoomRocket(self.rect.centerx + (0.5 * self.rect.size[0] * self.direction), self.rect.top, self.direction)
            rocket_group.add(rocket)
            # reduce rockets
            self.grenades -= 1
            return True
        return False

    def move(self, moving_left, moving_right):
        # reset movement variables
        screen_scroll = 0
        dx = 0
        dy = 0
        # assign movement variables if moving left or right
        if moving_left:
            dx = -self.speed
            self.flip = True
            self.direction = -1
        if moving_right:
            dx = self.speed
            self.flip = False
            self.direction = 1

        # jump
        if self.jump == True and self.in_air == False:
            self.vel_y = -14
            self.jump = False
            self.in_air = True

        # apply gravity
        self.vel_y += GRAVITY
        dy += self.vel_y

        # check for collision
        for tile in hell_map.obstacle_list:
            # check collision in the x direction
            if tile[1].colliderect(self.rect.x + dx, self.rect.y, self.width, self.height):
                dx = 0
                # if the ai has hit a wall then make it turn around
                if self.char_type == 'enemy':
                    self.direction *= -1
                    self.move_counter = 0
            # check for collision in the y direction
            if tile[1].colliderect(self.rect.x, self.rect.y + dy, self.width, self.height):
                # check if below the ground, i.e. jumping
                if self.vel_y < 0:
                    self.vel_y = 0
                    dy = tile[1].bottom - self.rect.top
                # check if above the ground, i.e. falling
                elif self.vel_y >= 0:
                    self.vel_y = 0
                    self.in_air = False
                    dy = tile[1].top - self.rect.bottom

        # check for collision with water
        if pygame.sprite.spritecollide(self, water_group, False):
            self.health = 0

        # check for collision with exit
        level_complete = False
        if pygame.sprite.spritecollide(self, exit_group, False):
            level_complete = True

        # check if fallen off the map
        if self.rect.bottom > SCREEN_HEIGHT:
            self.health = 0

        # check if going off the edges of the screen
        if self.char_type == 'player':
            if self.rect.left + dx < 0 or self.rect.right + dx > SCREEN_WIDTH:
                dx = 0

        # update rectangle position
        self.rect.x += dx
        self.rect.y += dy

        # update scroll based on player position
        if self.char_type == 'player':
            if (self.rect.right > SCREEN_WIDTH - SCROLL_THRESH and bg_scroll < (hell_map.level_length * TILE_SIZE) - SCREEN_WIDTH)\
                or (self.rect.left < SCROLL_THRESH and bg_scroll > abs(dx)):
                self.rect.x -= dx
                screen_scroll = -dx

        return screen_scroll, level_complete

    def shoot(self):
        if self.shoot_cooldown == 0 and self.ammo > 0:
            self.shoot_cooldown = 20
            plasma = PlasmaBolt(self.rect.centerx + (0.75 * self.rect.size[0] * self.direction), self.rect.centery, self.direction)
            plasma_group.add(plasma)
            # reduce ammo
            self.ammo -= 1
            shot_fx.play()

    def ai(self):
        if self.alive and player.alive:
            if self.idling == False and random.randint(1, 200) == 1:
                self.idling = True
                self.idling_counter = 50
            # check if the ai in near the player
            if self.vision.colliderect(player.rect):
                # shoot
                self.shoot()
            else:
                if self.idling == False:
                    if self.direction == 1:
                        ai_moving_right = True
                    else:
                        ai_moving_right = False
                    ai_moving_left = not ai_moving_right
                    self.move(ai_moving_left, ai_moving_right)
                    self.move_counter += 1
                    # update ai vision as the enemy moves
                    self.vision.center = (self.rect.centerx + 75 * self.direction, self.rect.centery)
                    if self.move_counter > TILE_SIZE:
                        self.direction *= -1
                        self.move_counter *= -1
                else:
                    self.idling_counter -= 1
                    if self.idling_counter <= 0:
                        self.idling = False
        # scroll
        self.rect.x += screen_scroll

    def check_alive(self):
        if self.health <= 0:
            self.health = 0
            self.speed = 0
            self.alive = False
            if self.char_type == 'enemy':
                self.kill()

    def draw(self):
        if self.alive:
            screen.blit(pygame.transform.flip(self.image, self.flip, False), self.rect)

class HellMap():
    def __init__(self):
        self.obstacle_list = []

    def process_data(self, data):
        self.level_length = len(data[0])
        # iterate through each value in level_data.csv files and making a matrix of surface
        for y, row in enumerate(data):
            for x, tile in enumerate(row):
                if tile >= 0:
                    img = img_list[tile]
                    img_rect = img.get_rect()
                    img_rect.x = x * TILE_SIZE
                    img_rect.y = y * TILE_SIZE
                    tile_data = (img, img_rect)
                    if 0 <= tile <= 8:
                        self.obstacle_list.append(tile_data)
                    elif 9 <= tile <= 10:
                        water_group.add(Water(img, x * TILE_SIZE, y * TILE_SIZE))
                    elif 11 <= tile <= 14:
                        decoration_group.add(Decoration(img, x * TILE_SIZE, y * TILE_SIZE))
                    elif tile == 15:
                        player = DoomGuy('player', x * TILE_SIZE, y * TILE_SIZE, 5, 20, 5)
                        health_bar = HealthBar(10, 10, player.health, player.health)
                    elif tile == 16:
                        demon_group.add(DoomGuy('enemy', x * TILE_SIZE, y * TILE_SIZE, 2, 20, 0))
                    elif tile == 17:
                        crate_group.add(SupplyCrate('Ammo', x * TILE_SIZE, y * TILE_SIZE))
                    elif tile == 18:
                        crate_group.add(SupplyCrate('Grenade', x * TILE_SIZE, y * TILE_SIZE))
                    elif tile == 19:
                        crate_group.add(SupplyCrate('Health', x * TILE_SIZE, y * TILE_SIZE))
                    elif tile == 20:
                        exit_group.add(Exit(img, x * TILE_SIZE, y * TILE_SIZE))

        return player, health_bar

    def draw(self):
        for tile in self.obstacle_list:
            tile[1][0] += screen_scroll
            screen.blit(tile[0], tile[1])

class Decoration(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.midtop = (x + TILE_SIZE // 2, y + (TILE_SIZE - self.image.get_height()))

    def update(self):
        self.rect.x += screen_scroll

class Water(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.midtop = (x + TILE_SIZE // 2, y + (TILE_SIZE - self.image.get_height()))

    def update(self):
        self.rect.x += screen_scroll

class Exit(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.midtop = (x + TILE_SIZE // 2, y + (TILE_SIZE - self.image.get_height()))

    def update(self):
        self.rect.x += screen_scroll

class SupplyCrate(pygame.sprite.Sprite):
    def __init__(self, item_type, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.item_type = item_type
        self.image = supply_crates[self.item_type]
        self.rect = self.image.get_rect()
        self.rect.midtop = (x + TILE_SIZE // 2, y + (TILE_SIZE - self.image.get_height()))
 
    def update(self):
        # scroll
        self.rect.x += screen_scroll
        # check if the player has picked up the box
        if pygame.sprite.collide_rect(self, player):
            # check what kind of box it was
            if self.item_type == 'Health':
                player.health += 25
                if player.health > player.max_health:
                    player.health = player.max_health
            elif self.item_type == 'Ammo':
                player.ammo += 15
            elif self.item_type == 'Grenade':
                player.grenades += 3
            # delete the item box
            self.kill()

class HealthBar():
    def __init__(self, x, y, health, max_health):
        self.x = x
        self.y = y
        self.health = health
        self.max_health = max_health

    def draw(self, health):
        # update with new health
        self.health = health
        # calculate health ratio
        ratio = self.health / self.max_health
        pygame.draw.rect(screen, BLACK, (self.x - 2, self.y - 2, 154, 24))
        pygame.draw.rect(screen, RED, (self.x, self.y, 150, 20))
        pygame.draw.rect(screen, GREEN, (self.x, self.y, 150 * ratio, 20))

class PlasmaBolt(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        pygame.sprite.Sprite.__init__(self)
        self.speed = 10
        self.image = plasma_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction

    def update(self):
        # move bullet
        self.rect.x += (self.direction * self.speed) + screen_scroll
        # check if bullet has gone off screen
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        # check for collision with level
        for tile in hell_map.obstacle_list:
            if tile[1].colliderect(self.rect):
                self.kill()
        # check collision with characters
        if pygame.sprite.spritecollide(player, plasma_group, False):
            if player.alive:
                player.health -= 5
                self.kill()
        for demon in demon_group:
            if pygame.sprite.spritecollide(demon, plasma_group, False):
                if demon.alive:
                    demon.health -= 25
                    self.kill()

class DoomRocket(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        pygame.sprite.Sprite.__init__(self)
        self.timer = 100
        self.vel_y = -11
        self.speed = 7
        self.image = rocket_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        self.direction = direction

    def update(self):
        self.vel_y += GRAVITY
        dx = self.direction * self.speed
        dy = self.vel_y

        # check for collision with level
        for tile in hell_map.obstacle_list:
            # check collision with walls
            if tile[1].colliderect(self.rect.x + dx, self.rect.y, self.width, self.height):
                self.direction *= -1
                dx = self.direction * self.speed
            # check for collision in the y direction
            if tile[1].colliderect(self.rect.x, self.rect.y + dy, self.width, self.height):
                self.speed = 0
                # check if below the ground, i.e. thrown up
                if self.vel_y < 0:
                    self.vel_y = 0
                    dy = tile[1].bottom - self.rect.top
                # check if above the ground, i.e. falling
                elif self.vel_y >= 0:
                    self.vel_y = 0
                    dy = tile[1].top - self.rect.bottom    

        # update grenade position
        self.rect.x += dx + screen_scroll
        self.rect.y += dy

        # countdown timer 
        self.timer -= 1
        if self.timer <= 0:
            self.kill()
            grenade_fx.play()
            explosion = Explosion(self.rect.x, self.rect.y, 0.5)
            explosion_group.add(explosion)
            # do damage to anyone that is nearby
            if abs(self.rect.centerx - player.rect.centerx) < TILE_SIZE * 2 and \
                abs(self.rect.centery - player.rect.centery) < TILE_SIZE * 2:
                player.health -= 50
            for demon in demon_group:
                if abs(self.rect.centerx - demon.rect.centerx) < TILE_SIZE * 2 and \
                    abs(self.rect.centery - demon.rect.centery) < TILE_SIZE * 2:
                    demon.health -= 50

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, scale):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        for num in range(1, 6):
            img = safe_load_image(f'img/explosion/exp{num}.png')
            if img:
                img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            self.images.append(img)
        self.frame_index = 0
        self.image = self.images[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.counter = 0

    def update(self):
        # scroll
        self.rect.x += screen_scroll
        EXPLOSION_SPEED = 4
        # update explosion amimation
        self.counter += 1
        if self.counter >= EXPLOSION_SPEED:
            self.counter = 0
            self.frame_index += 1
            # if the animation is complete then delete the explosion
            if self.frame_index >= len(self.images):
                self.kill()
            else:
                self.image = self.images[self.frame_index]

class ScreenFade():
    def __init__(self, direction, colour, speed):
        self.direction = direction
        self.colour = colour
        self.speed = speed
        self.fade_counter = 0

    def fade(self):
        fade_complete = False
        self.fade_counter += self.speed
        if self.direction == 1:
            pygame.draw.rect(screen, self.colour, (0 - self.fade_counter, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.colour, (SCREEN_WIDTH // 2 + self.fade_counter, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.colour, (0, 0 - self.fade_counter, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
            pygame.draw.rect(screen, self.colour, (0, SCREEN_HEIGHT // 2 + self.fade_counter, SCREEN_WIDTH, SCREEN_HEIGHT))
        if self.direction == 2:
            pygame.draw.rect(screen, self.colour, (0, 0, SCREEN_WIDTH, 0 + self.fade_counter))
        if self.fade_counter >= SCREEN_WIDTH:
            fade_complete = True

        return fade_complete

# create screen fades 
intro_fade = ScreenFade(1, BLACK, 8)  

# create buttons 
restart_button = button.Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50, restart_img, 2)

# create sprite groups
demon_group = pygame.sprite.Group()
plasma_group = pygame.sprite.Group()
rocket_group = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()
crate_group = pygame.sprite.Group()
decoration_group = pygame.sprite.Group()
water_group = pygame.sprite.Group()
exit_group = pygame.sprite.Group()

# create empty tile list
world_data = []
for row in range(ROWS):
    r = [-1] * COLS
    world_data.append(r)

# load in level data and create hell_map
world_data, hell_map, player, health_bar = load_level(level)

run = True

if show_video:
    intro_video_path = 'intro_video.mp4' 
    intro_audio_path = 'audio/intro_music.mp3' 
    if os.path.exists(intro_video_path):
        play_video(intro_video_path, intro_audio_path, loop=False, show_restart=False, audio_volume=0.6)
    start_game = True
    start_intro = True
    pygame.mixer.music.load('audio/music2.mp3')
    pygame.mixer.music.play(-1, 0.0, 5000)  
else:
    screen.fill(BLACK)
    pygame.display.update()
    pygame.time.wait(1000)  
    start_game = True
    start_intro = True
    pygame.mixer.music.load('audio/music2.mp3')
    pygame.mixer.music.play(-1, 0.0, 5000)

def handle_events():
    global run, moving_left, moving_right, shoot, grenade, grenade_thrown
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN and not show_death_video:
            if event.key in [pygame.K_a, pygame.K_LEFT]: moving_left = True
            if event.key in [pygame.K_d, pygame.K_RIGHT]: moving_right = True
            if event.key == pygame.K_SPACE: shoot = True
            if event.key in [pygame.K_q, pygame.K_g]: grenade = True
            if (event.key in [pygame.K_w, pygame.K_UP]) and player.alive:
                player.jump = True
                jump_fx.play()
            if event.key == pygame.K_ESCAPE: run = False
        if event.type == pygame.KEYUP and not show_death_video:
            if event.key in [pygame.K_a, pygame.K_LEFT]: moving_left = False
            if event.key in [pygame.K_d, pygame.K_RIGHT]: moving_right = False
            if event.key == pygame.K_SPACE: shoot = False
            if event.key in [pygame.K_q, pygame.K_g]: grenade = False; grenade_thrown = False

def update_game():
    global bg_scroll, level, level_complete, show_death_video, grenade_thrown, world_data, hell_map, player, health_bar, screen_scroll, start_intro, start_game
    
    if show_death_video:
        death_video_path = 'death_video.mp4'  
        death_audio_path = 'audio/death_music.mp3'  
        if os.path.exists(death_video_path):
            result = play_video(death_video_path, death_audio_path, loop=True, show_restart=True, audio_volume=1.0)  
            if result == "restart":
                show_death_video = False
                start_intro = True
                bg_scroll = 0
                world_data, hell_map, player, health_bar = load_level(level)
                pygame.mixer.music.load('audio/music2.mp3')
                pygame.mixer.music.play(-1, 0.0, 5000)
            else:
                return False # signal to quit
        else:
            # Handle death screen restart button in Draw or here?
            # It's better to keep it in a loop for now or handled specially.
            pass
    elif start_game:
        player.update()
        for demon in demon_group:
            demon.ai()
            demon.update()
        
        plasma_group.update()
        rocket_group.update()
        explosion_group.update()
        crate_group.update()
        decoration_group.update()
        water_group.update()
        exit_group.update()
        
        if player.alive:
            # shoot bullets
            if shoot:
                player.shoot()
            # throw rockets
            elif grenade and grenade_thrown == False and player.grenades > 0:
                rocket = DoomRocket(player.rect.centerx + (0.5 * player.rect.size[0] * player.direction),\
                            player.rect.top, player.direction)
                rocket_group.add(rocket)
                # reduce rockets
                player.grenades -= 1
                grenade_thrown = True
            
            screen_scroll, level_complete = player.move(moving_left, moving_right)
            bg_scroll -= screen_scroll
            
            if level_complete:
                level += 1
                bg_scroll = 0
                world_data = reset_level() # Ensure reset_level is defined or handled
                if level <= MAX_LEVELS:
                    world_data, hell_map, player, health_bar = load_level(level)
                else:
                    win_video_path = 'win_video.mp4'
                    win_audio_path = 'audio/win_audio.mp3'
                    if os.path.exists(win_video_path):
                        play_video(win_video_path, win_audio_path, loop=True, show_restart=True, audio_volume=0.8)
                    level = 1
                    bg_scroll = 0
                    world_data, hell_map, player, health_bar = load_level(level)
                    pygame.mixer.music.load('audio/music2.mp3')
                    pygame.mixer.music.play(-1, 0.0, 5000)
        else:
            screen_scroll = 0 # Reset screen_scroll on death
            show_death_video = True
            pygame.mixer.music.stop()
    return True

def draw_frame():
    global start_intro, show_death_video, bg_scroll, world_data, hell_map, player, health_bar, level
    if start_game and not show_death_video:
        draw_bg()
        hell_map.draw()
        health_bar.draw(player.health)
        
        draw_text('AMMO: ', font, WHITE, 10, 35)
        for x in range(player.ammo):
            screen.blit(plasma_img, (90 + (x * 10), 40))
        draw_text('ROCKETS: ', font, WHITE, 10, 60)
        for x in range(player.grenades):
            screen.blit(rocket_img, (135 + (x * 15), 60))
            
        player.draw()
        for demon in demon_group:
            demon.draw()
            
        plasma_group.draw(screen)
        rocket_group.draw(screen)
        explosion_group.draw(screen)
        crate_group.draw(screen)
        decoration_group.draw(screen)
        water_group.draw(screen)
        exit_group.draw(screen)
        
        if start_intro:
            if intro_fade.fade():
                start_intro = False
                intro_fade.fade_counter = 0
    elif show_death_video and not os.path.exists('death_video.mp4'):
        screen.fill(BLACK)
        if restart_button.draw(screen):
            show_death_video = False
            start_intro = True
            bg_scroll = 0
            world_data, hell_map, player, health_bar = load_level(level)
            pygame.mixer.music.load('audio/music2.mp3')
            pygame.mixer.music.play(-1, 0.0, 5000)
    pygame.display.update()

while run:
    clock.tick(FPS)
    handle_events()
    if not update_game():
        run = False
    draw_frame()

pygame.quit()
