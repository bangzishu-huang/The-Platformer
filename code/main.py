from settings import *
from sprites import *
from groups import AllSprites
from support import *
from timed import Timer
from random import randint, choice
import asyncio

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

        self.score_multiplier = 1

        self.state = 'start'
        self.font = pygame.font.Font(join('code', 'data', 'graphics', 'font', 'font.ttf'), 50)
        self.small_font = pygame.font.Font(join('code', 'data', 'graphics', 'font', 'font.ttf'), 28)
        self.combo_font = pygame.font.Font(join('code', 'data', 'graphics', 'font', 'font.ttf'), 34)
        self.combo_font.set_bold(True)

        self.button_rect = pygame.Rect(0, 0, 220, 70)
        self.button_rect.center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 90)

        self.difficulty_buttons = {}
        for i, name in enumerate(DIFFICULTIES):
            rect = pygame.Rect(0, 0, 280, 70)
            rect.center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 120 + i * 95)
            self.difficulty_buttons[name] = rect

        self.score = 0 
        self.high_score = self.load_highscore()

        self.combo = 0
        self.floating_text = []
        self.lottery_active = False
        self.lottery_result = None
        self.lottery_start = 0
        self.active_powerup = None
        self.powerup_timer = Timer(POWERUP_DURATION, func = self.end_powerup)

        self.difficulty = 'medium'

        self.hack_menu_open = False
        self.enemies_frozen = False 
        self.hack_abilities = {name: False for name in POWERUPS}
        self.cheats = {'god_mode': False, 'esp': False, 'no_clip': False, 'infinite_ammo': False}

        names = list(POWERUPS.keys())
        cell_w, cell_h = 260, 90
        grid_w = 3 * cell_w 
        start_x = WINDOW_WIDTH / 2 - grid_w / 2
        start_y = 150
        self.hack_ability_buttons = {}
        for i, name in enumerate(names):
            col, row = i % 3, i // 3
            rect = pygame.Rect(start_x + col * cell_w, start_y + row * cell_h, cell_w - 10, cell_h - 10)
            self.hack_ability_buttons[name] = rect

        cheat_names = list(self.cheats.keys())
        cheat_y = start_y + 3 * cell_h + 40
        self.hack_cheat_buttons = {}
        for i, name in enumerate(cheat_names):
            rect = pygame.Rect(0, 0, 260, 70)
            rect.center = (WINDOW_WIDTH / 2 - 420 + i * 280, cheat_y)
            self.hack_cheat_buttons[name] = rect

        self.load_assets()  
        self.setup()
        self.audio['music'].play(loops = -1)
        self.bee_timer = Timer(DIFFICULTIES[self.difficulty]['bee_interval'], func = self.create_bee, autostart = True, repeat = True)

    def create_bee(self):
        bee_speed_range = DIFFICULTIES[self.difficulty]['bee_speed']
        Bee(self.bee_frames, 
            pos = ((self.level_width + WINDOW_WIDTH), (randint(0, self.level_height))), 
            groups = (self.all_sprites, self.enemy_sprites),
            speed = randint(*bee_speed_range))

    def create_worm(self):
        active_worms = [sprite for sprite in self.enemy_sprites if isinstance(sprite, Worm)]
        available_rects = [rect for rect in self.worm_spawn_rects if not any(rect.contains(w.main_rect) for w in active_worms)]

        if available_rects:
            rect = choice(available_rects)
            Worm(self.worm_frames, rect, (self.all_sprites, self.enemy_sprites), speed_mult = DIFFICULTIES[self.difficulty]['worm_speed_mult'])

    def create_bullet(self, pos, direction):
        bullet_surf = self.mega_bullet_surf if self.player.mega_bullets else self.bullet_surf
        x = pos[0] + direction * 34 if direction == 1 else pos[0] + direction * 34 - self.bullet_surf.get_width()
        y_offsets = (0, -22, 22) if self.player.multi_shot else (0,)
        for y_offset in y_offsets:
            Bullet(bullet_surf, (x, pos[1] + y_offset), direction, (self.all_sprites, self.bullet_sprites))
        Fire(self.fire_surf, pos, self.all_sprites, self.player)
        self.audio['shoot'].play()

    def load_assets(self):
        self.player_frames = import_folder('code', 'images', 'player')
        self.bullet_surf = import_image('code', 'images', 'gun', 'bullet')
        self.mega_bullet_surf = pygame.transform.scale_by(self.bullet_surf, 1.8)
        self.fire_surf = import_image('code', 'images', 'gun', 'fire')
        self.bee_frames = import_folder('code', 'images', 'enemies', 'bee')
        self.worm_frames = import_folder('code', 'images', 'enemies', 'worm')

        self.audio = audio_import('code', 'audio')

    def setup(self):
        tmx_map = load_pygame(join('code', 'data', 'maps', 'world.tmx'))

        self.level_width = tmx_map.width * TILE_SIZE
        self.level_height = tmx_map.height * TILE_SIZE

        self.worm_spawn_rects = []

        for x, y, image in tmx_map.get_layer_by_name('Main').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))
        for x, y, image in tmx_map.get_layer_by_name('Decoration').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        for obj in tmx_map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, self.player_frames, self.create_bullet, self.audio['jump'].play)
            if obj.name == 'Worm':
                self.worm_spawn_rects.append(pygame.FRect(obj.x, obj.y, obj.width, obj.height))

        self.reapply_hack_abilities()

    def collision(self):
        for bullet in self.bullet_sprites:
            sprite_collsiion = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if sprite_collsiion:
                self.audio['impact'].play()
                if not self.player.piercing:
                    bullet.kill()
                for sprite in sprite_collsiion:
                    if not sprite.death_timer.active:
                        sprite.destroy()
                        self.register_kill()
        if not self.cheats['god_mode'] and not self.player.shield and pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.trigger_game_over()

        if self.player.rect.top > self.level_height + 350:
            self.trigger_game_over()

    def load_highscore(self):
        try:
            with open(HIGHSCORE_FILE) as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def save_highscore(self):
        with open(HIGHSCORE_FILE, 'w') as f:
            f.write(str(self.high_score))

    def trigger_game_over(self):
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_highscore()
        self.state = 'game_over'

    def register_kill(self):
        self.score += self.score_multiplier
        if self.score > self.high_score:
            self.high_score = self.score

        if any(self.hack_abilities.values()) or any(self.cheats.values()):
            return

        self.combo += 1
        self.spawn_floating_text(f'x{self.combo}')
        if self.combo >= KILLS_PER_LOTTERY:
            self.start_lottery()

    def spawn_floating_text(self, text):
        pos = (randint(160, WINDOW_WIDTH - 220), randint(160, WINDOW_HEIGHT - 220))
        self.floating_text.append({'text': text, 'pos': pos, 'start': pygame.time.get_ticks(), 'duration': 1400})

    def start_lottery(self):
        self.combo = 0
        self.lottery_active = True
        self.lottery_start = pygame.time.get_ticks()
        self.lottery_result = choice(list(POWERUPS.keys()))
        self.audio['spin'].play()

    def update_lottery(self):
        if self.lottery_active and pygame.time.get_ticks() - self.lottery_start >= LOTTERY_SPIN_TIME:
            self.lottery_active = False
            self.apply_powerup(self.lottery_result)

    def apply_powerup(self, name):
        self.active_powerup = name
        if name == 'score_x2':
            self.score_multiplier = 2
        elif name == 'freeze_enemies':
            self.enemies_frozen = True
        else:
            self.player.apply_powerup(name)
        self.powerup_timer.activate()

    def end_powerup(self):
        if self.active_powerup == 'score_x2':
            self.score_multiplier = 1
        elif self.active_powerup == 'freeze_enemies':
            self.enemies_frozen = False
        else:
            self.player.clear_powerup()
        self.active_powerup = None
        self.reapply_hack_abilities()

    def toggle_hack_game_ability(self, name):
        enabled = self.hack_abilities[name]
        if name == 'score_x2':
            self.score_multiplier = 2 if enabled else 1
        elif name == 'freeze_enemies':
            self.enemies_frozen = enabled 

    def apply_cheat(self, name):
        if name == 'no_clip':
            self.player.no_clip = self.cheats['no_clip']
        elif name == 'infinite_ammo':
            self.player.infinite_ammo = self.cheats['infinite_ammo']

    def reapply_hack_abilities(self):
        for name, enabled in self.hack_abilities.items():
            if not enabled:
                continue
            if name == 'score_x2':
                self.score_multiplier = 2
            elif name =='freeze_enemies':
                self.enemies_frozen = True
            else:
                self.player.set_ability(name, True)
        self.player.no_clip = self.cheats['no_clip']
        self.player.infinite_ammo = self.cheats['infinite_ammo']

    def start_game(self, difficulty):
        self.difficulty = difficulty
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.setup()

        self.score = 0
        self.combo = 0
        self.score_multiplier = 1
        self.floating_text = []
        self.lottery_active = False
        self.active_powerup = None
        self.powerup_timer.deactivate()
        self.bee_timer = Timer(DIFFICULTIES[difficulty]['bee_interval'], func = self.create_bee, autostart=True, repeat=True)
        self.worm_timer = Timer(DIFFICULTIES[self.difficulty]['worm_interval'], func = self.create_worm, autostart=True, repeat=True)
        for _ in range(len(self.worm_spawn_rects)):
            self.create_worm()
        self.state = 'playing'

    def reset(self):
        self.state = 'difficulty'

    def display_start_screen(self):
        overlay = pygame.Surface((WINDOW_HEIGHT, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.display_surface.blit(overlay, (0, 0))

        title_surf = self.font.render('THE PLATFORMER', False, 'white')
        title_rect = title_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 60))
        self.display_surface.blit(title_surf, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        hovering = self.button_rect.collidepoint(mouse_pos)

        pygame.draw.rect(self.display_surface, 'white' if hovering else BG_COLOR, self.button_rect, 0, 8)
        pygame.draw.rect(self.display_surface, 'black', self.button_rect, 3, 5)

        play_surf = self.font.render('PLAY', False, 'black')
        play_rect = play_surf.get_frect(center = self.button_rect.center)
        self.display_surface.blit(play_surf, play_rect)

    def display_difficulty_screen(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.display_surface.blit(overlay, (0,0))

        title_surf = self.font.render('SELECT DIFFICULTY', False, 'white')
        title_rect = title_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 210))
        self.display_surface.blit(title_surf, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        for name, rect in self.difficulty_buttons.items():
            info = DIFFICULTIES[name]
            hovering = rect.collidepoint(mouse_pos)

            pygame.draw.rect(self.display_surface, info['color'], rect, 0, 8)
            pygame.draw.rect(self.display_surface, 'black', rect, 4 if hovering else 3, 8)
            label_surf = self.small_font.render(info['label'], False, 'black')
            label_rect = label_surf.get_frect(center = rect.center)
            self.display_surface.blit(label_surf, label_rect)

        last_button = list(self.difficulty_buttons.values())[-1]
        hack_hint_surf = self.small_font.render('Press H for Hack Mode', False, '#ff2ec4')
        hack_hint_rect = hack_hint_surf.get_frect(center = (WINDOW_WIDTH / 2, last_button.bottom + 40))
        self.display_surface.blit(hack_hint_surf, hack_hint_rect)

    def display_hud(self):
        score_surf = self.small_font.render(f'Score: {self.score}', False, 'black')
        self.display_surface.blit(score_surf, (20, 20))

        high_surf = self.small_font.render(f'High Score: {self.high_score}', False, 'black')
        high_rect = high_surf.get_frect(topright = (WINDOW_WIDTH - 20, 20))
        self.display_surface.blit(high_surf, high_rect)

        if self.active_powerup:
            info = POWERUPS[self.active_powerup]
            remaining = max(0, self.powerup_timer.duration - (pygame.time.get_ticks() - self.powerup_timer.start_time))
            powerup_surf = self.small_font.render(f"{info['label']} ({remaining // 1000 + 1}s)", False, info['color'])
            powerup_rect = powerup_surf.get_frect(center = (WINDOW_WIDTH / 2, 30))
            self.display_surface.blit(powerup_surf, powerup_rect)

    def display_floating_text(self):
        now = pygame.time.get_ticks()
        self.floating_text = [t for t in self.floating_text if now - t['start'] < t['duration']]
        for t in self.floating_text:
            progress = (now - t['start']) / t['duration']
            pop_in = min(1, progress / 0.15)
            scale = (0.5 + 0.5 * pop_in) * (1 + progress * 1.6)
            alpha = 255 if progress < 0.5 else max(0, int(255 * (1 - (progress - 0.5) / 0.5)))

            base_surf = self.combo_font.render(t['text'], False, 'white').convert_alpha()
            outline_surf = self.combo_font.render(t['text'], False, 'black').convert_alpha()

            w, h = base_surf.get_size()
            scaled_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            base_scaled = pygame.transform.smoothscale(base_surf, scaled_size)
            outline_scaled = pygame.transform.smoothscale(outline_surf, scaled_size)

            center = t['pos']
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                outline_rect = outline_scaled.get_frect(center = (center[0] + dx, center[1] + dy))
                self.display_surface.blit(outline_scaled, outline_rect)

            base_rect = base_scaled.get_frect(center = center)
            self.display_surface.blit(base_scaled, base_rect)

    def display_lottery(self):
        box = pygame.Rect(0, 0, 420, 130)
        box.center = (WINDOW_WIDTH / 2, 160)
        elapsed = pygame.time.get_ticks() - self.lottery_start
        landed = elapsed >= LOTTERY_SPIN_TIME - 250

        info = POWERUPS[self.lottery_result] if landed else POWERUPS[choice(list(POWERUPS.keys()))]
        pygame.draw.rect(self.display_surface, 'white', box, 0, 10)
        pygame.draw.rect(self.display_surface, info['color'] if landed else 'black', box, 5, 10)

        label_surf = self.font.render(info['label'], False, info['color'] if landed else 'black')
        label_rect = label_surf.get_frect(center = box.center)
        self.display_surface.blit(label_surf, label_rect)

    def display_esp_overlay(self):
        offset = self.all_sprites.offset
        for enemy in self.enemy_sprites:
            pos = enemy.rect.center + offset
            radius = max(enemy.rect.width, enemy.rect.height) / 2 + 10
            pygame.draw.circle(self.display_surface, '#ff2ec4', pos, radius, 3)

    def display_hack_menu(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.display_surface.blit(overlay, (0, 0))

        title_surf = self.font.render('HACK MODE', False, '#ff2ec4')
        title_rect = title_surf.get_frect(center = (WINDOW_WIDTH / 2, 80))
        self.display_surface.blit(title_surf, title_rect)

        disclaimer_surf = self.small_font.render('Note: enabling any hack disables the kill combo / lottery', False, 'white')
        disclaimer_rect = disclaimer_surf.get_frect(center = (WINDOW_WIDTH / 2, 115))
        self.display_surface.blit(disclaimer_surf, disclaimer_rect)

        for name, rect in self.hack_ability_buttons.items():
            info = POWERUPS[name]
            enabled = self.hack_abilities[name]
            pygame.draw.rect(self.display_surface, info['color'] if enabled else '#3a3a3a', rect, 0, 8)
            pygame.draw.rect(self.display_surface, 'white', rect, 3, 8)
            label_surf = self.small_font.render(info['label'], False, 'black' if enabled else 'white')
            label_rect = label_surf.get_frect(center = (rect.centerx, rect.centery - 12))
            self.display_surface.blit(label_surf, label_rect)
            status_surf = self.small_font.render('ON' if enabled else 'OFF', False, 'black' if enabled else 'white')
            status_rect = status_surf.get_frect(center = (rect.centerx, rect.centery + 18))
            self.display_surface.blit(status_surf, status_rect)
        for name, rect in self.hack_cheat_buttons.items():
            enabled = self.cheats[name]
            pygame.draw.rect(self.display_surface, '#ff2ec4' if enabled else '#3a3a3a', rect, 0, 8)
            pygame.draw.rect(self.display_surface, 'white', rect, 3, 8)
            label_surf = self.small_font.render(name.replace('_', ' ').upper(), False, 'black' if enabled else 'white')
            label_rect = label_surf.get_frect(center = rect.center)
            self.display_surface.blit(label_surf, label_rect)

        hint_surf = self.small_font.render('Press H to close', False, 'white')
        hint_rect = hint_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT - 40))
        self.display_surface.blit(hint_surf, hint_rect)
        

    def display_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.display_surface.blit(overlay, (0, 0))

        title_surf = self.font.render('GAME OVER', False, 'white')
        title_rect = title_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 120))
        self.display_surface.blit(title_surf, title_rect)

        score_surf = self.small_font.render(f'Score: {self.score}', False, 'white')
        score_rect = score_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 60))
        self.display_surface.blit(score_surf, score_rect)

        high_score_surf = self.small_font.render(f'High Score: {self.high_score}', False, 'white')
        high_score_rect = high_score_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 20))
        self.display_surface.blit(high_score_surf, high_score_rect)

        mouse_pos = pygame.mouse.get_pos()
        hovering = self.button_rect.collidepoint(mouse_pos)

        pygame.draw.rect(self.display_surface, 'white' if hovering else BG_COLOR, self.button_rect, 0, 8)
        pygame.draw.rect(self.display_surface, 'black', self.button_rect, 3, 8)

        replay_surf = self.font.render('REPLAY', False, 'black')
        replay_rect = replay_surf.get_frect(center = self.button_rect.center)
        self.display_surface.blit(replay_surf, replay_rect)

    async def run(self):
        while self.running:
            dt = self.clock.tick(FRAMERATE) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                    self.hack_menu_open = not self.hack_menu_open

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.hack_menu_open:
                        for name, rect in self.hack_ability_buttons.items():
                            if rect.collidepoint(event.pos):
                                self.hack_abilities[name] = not self.hack_abilities[name]
                                if name in ('score_x2', 'freeze_enemies'):
                                    self.toggle_hack_game_ability(name)
                                else:
                                    self.player.set_ability(name, self.hack_abilities[name])
                        for name, rect in self.hack_cheat_buttons.items():
                            if rect.collidepoint(event.pos):
                                self.cheats[name] = not self.cheats[name]
                                self.apply_cheat(name)
                    elif self.state == 'start' and self.button_rect.collidepoint(event.pos):
                        self.state = 'difficulty'

                    elif self.state == 'difficulty':
                        for name, rect in self.difficulty_buttons.items():
                            if rect.collidepoint(event.pos):
                                self.start_game(name)
                                break

                    elif self.state == 'game_over' and self.button_rect.collidepoint(event.pos):
                        self.reset()

            if self.state == 'playing' and not self.hack_menu_open:
                self.bee_timer.update()
                self.worm_timer.update()
                self.powerup_timer.update()
                self.update_lottery()
                for sprite in self.all_sprites:
                    if self.enemies_frozen and sprite in self.enemy_sprites and not sprite.death_timer.active:
                        continue
                    sprite.update(dt)
                self.collision()

            self.display_surface.fill(BG_COLOR)
            if self.state in ('playing', 'game_over'):
                self.all_sprites.draw(self.player.rect.center)
                if self.cheats['esp'] and self.state == 'playing':
                    self.display_esp_overlay()

            if self.state == 'playing':
                self.display_hud()
                self.display_floating_text()
                if self.lottery_active:
                    self.display_lottery()
            elif self.state == 'game_over':
                self.display_game_over()
            elif self.state == 'start':
                self.display_start_screen()
            elif self.state == 'difficulty':
                self.display_difficulty_screen()

            if self.hack_menu_open:
                self.display_hack_menu()

            pygame.display.update()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    asyncio.run(game.run())
