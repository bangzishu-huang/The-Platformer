from settings import *
from sprites import *
from groups import AllSprites
from support import *
from timed import Timer
from random import randint

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('The Platformer')
        self.clock = pygame.time.Clock()
        self.running = True

        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        self.game_over = False
        self.font = pygame.font.Font(join('code', 'data', 'graphics', 'font', 'font.ttf'), 50)
        self.button_rect = pygame.Rect(0, 0, 220, 70)
        self.button_rect.center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 90)
        

        self.load_assets()
        self.setup()
        self.audio['music'].play(loops = -1)

        self.bee_timer = Timer(500, func = self.create_bee, autostart=True, repeat=True)

    def create_bee(self):
        Bee(self.bee_frames, 
            pos = ((self.level_width + WINDOW_WIDTH), (randint(0, self.level_height))), 
            groups = (self.all_sprites, self.enemy_sprites),
            speed = randint(300,500))

    def create_bullet(self, pos, direction):
        x = pos[0] + direction * 34 if direction == 1 else pos[0] + direction * 34 - self.bullet_surf.get_width()
        Bullet(self.bullet_surf, (x, pos[1]), direction, (self.all_sprites, self.bullet_sprites))
        Fire(self.fire_surf, pos, self.all_sprites, self.player)
        self.audio['shoot'].play()

    def load_assets(self):
        self.player_frames = import_folder('code', 'images', 'player')
        self.bullet_surf = import_image('code', 'images', 'gun', 'bullet')
        self.fire_surf = import_image('code', 'images', 'gun', 'fire')
        self.bee_frames = import_folder('code', 'images', 'enemies', 'bee')
        self.worm_frames = import_folder('code', 'images', 'enemies', 'worm')

        self.audio = audio_import('code', 'audio')

    def setup(self):
        tmx_map = load_pygame(join('code', 'data', 'maps', 'world.tmx'))

        self.level_width = tmx_map.width * TILE_SIZE
        self.level_height = tmx_map.height * TILE_SIZE

        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))
        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        for obj in tmx_map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, self.player_frames, self.create_bullet)
            if obj.name == 'Worm':
                Worm(self.worm_frames, pygame.FRect(obj.x, obj.y, obj.width, obj.height), (self.all_sprites, self.enemy_sprites))

    def collision(self):
        for bullet in self.bullet_sprites:
            sprite_collsiion = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if sprite_collsiion:
                self.audio['impact'].play()
                bullet.kill()
                for sprite in sprite_collsiion:
                    sprite.destroy()
        if pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.game_over = True

    def reset(self):
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.setup()
        self.bee_timer.activate()
        self.game_over = False

    def display_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.display_surface.blit(overlay, (0, 0))

        title_surf = self.font.render('GAME OVER', False, 'white')
        title_rect = title_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 60))
        self.display_surface.blit(title_surf, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        hovering = self.button_rect.collidepoint(mouse_pos)

        pygame.draw.rect(self.display_surface, 'white' if hovering else BG_COLOR, self.button_rect, 0, 8)
        pygame.draw.rect(self.display_surface, 'black', self.button_rect, 3, 8)

        replay_surf = self.font.render('REPLAY', False, 'black')
        replay_rect = replay_surf.get_frect(center = self.button_rect.center)
        self.display_surface.blit(replay_surf, replay_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(FRAMERATE) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.MOUSEBUTTONDOWN and self.game_over:
                    if self.button_rect.collidepoint(event.pos):
                        self.reset()

            if not self.game_over:
                self.bee_timer.update()
                self.all_sprites.update(dt)
                self.collision()

            self.display_surface.fill(BG_COLOR)
            self.all_sprites.draw(self.player.rect.center)
            if self.game_over:
                self.display_game_over()
            pygame.display.update()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()
