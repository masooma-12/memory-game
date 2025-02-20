import pygame
import random
import time
import json
from enum import Enum

# Initialize Pygame
pygame.init()

# Colors
PINK = (255, 192, 203)
DARK_PINK = (231, 84, 128)
MAROON = (176, 48, 96)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
CARD_BACK = (255, 218, 224)
LIGHT_GRAY = (240, 240, 240)

# Screen settings
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Memory Game")

# Load a font that supports emojis
try:
    # Try loading a system font that supports emojis
    FONT = pygame.font.SysFont("Segoe UI Emoji", 40)
except:
    # Fallback to a default font (may not support emojis)
    FONT = pygame.font.Font(None, 40)

# Game states
class GameState(Enum):
    MENU = 1
    DIFFICULTY = 2
    GAME = 3
    GAME_OVER = 4

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=15)
        pygame.draw.rect(surface, MAROON, self.rect, 3, border_radius=15)
        
        text_surface = FONT.render(self.text, True, MAROON)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False

class Card:
    def __init__(self, x, y, width, height, symbol):
        self.rect = pygame.Rect(x, y, width, height)
        self.symbol = symbol
        self.is_flipped = False
        self.is_matched = False
        self.flip_progress = 0  # 0 to 1
        self.target_flip = 0
        self.scale = 1.0
        self.original_rect = self.rect.copy()
        
    def draw(self, surface):
        # Calculate card scale based on flip progress (create 3D effect)
        if self.is_flipped:
            self.scale = 1 - (0.2 * (1 - abs(2 * self.flip_progress - 1)))
        else:
            self.scale = 1 - (0.2 * abs(2 * self.flip_progress - 1))
            
        # Update rect size for animation
        scaled_width = int(self.original_rect.width * self.scale)
        x_offset = (self.original_rect.width - scaled_width) // 2
        self.rect = pygame.Rect(
            self.original_rect.x + x_offset,
            self.original_rect.y,
            scaled_width,
            self.original_rect.height
        )
        
        if self.flip_progress < 0.5:
            # Show back of card
            pygame.draw.rect(surface, CARD_BACK, self.rect, border_radius=10)
            pygame.draw.rect(surface, MAROON, self.rect, 3, border_radius=10)
            # Add decorative pattern
            pattern_rect = pygame.Rect(
                self.rect.x + 10,
                self.rect.y + 10,
                self.rect.width - 20,
                self.rect.height - 20
            )
            pygame.draw.rect(surface, PINK, pattern_rect, 2, border_radius=5)
        else:
            # Show front of card
            pygame.draw.rect(surface, WHITE, self.rect, border_radius=10)
            pygame.draw.rect(surface, MAROON, self.rect, 3, border_radius=10)
            
            if self.is_matched:
                pygame.draw.rect(surface, LIGHT_GRAY, self.rect, border_radius=10)
            
            # Draw symbol
            font = FONT
            text_surface = font.render(self.symbol, True, MAROON)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)
            
    def animate(self):
        # Smoother animation
        if self.is_flipped:
            self.flip_progress = min(1, self.flip_progress + 0.15)
        else:
            self.flip_progress = max(0, self.flip_progress - 0.15)

class MemoryGame:
    def __init__(self):
        self.state = GameState.MENU
        self.winning_streak = 0
        self.score = 0
        self.moves = 0
        self.max_moves = 0  # Added: Maximum moves for the current difficulty
        self.start_time = None
        self.elapsed_time = 0
        self.load_high_scores()
        
        # Game symbols (emoji pairs)
        self.symbols = [
            '🎮', '🎲', '🎯', '🎪', '🎭', '🎨', '🎩', '🎬',
            '🌟', '🌙', '⭐', '☀️', '🌈', '⚡', '❄️', '🔥',
            '🎵', '🎸', '🎺', '🎻', '🥁', '🎹', '🎷', '🎼',
            '🐶', '🐱', '🐰', '🦊', '🐼', '🐨', '🦁', '🐯'
        ]
        
        # Buttons
        button_width = 250
        button_height = 60
        center_x = SCREEN_WIDTH // 2 - button_width // 2
        
        self.menu_buttons = [
            Button(center_x, 250, button_width, button_height, "Play Game", PINK, DARK_PINK),
            Button(center_x, 350, button_width, button_height, "Exit", PINK, DARK_PINK)
        ]
        
        self.difficulty_buttons = [
            Button(center_x, 200, button_width, button_height, "Easy", PINK, DARK_PINK),
            Button(center_x, 300, button_width, button_height, "Medium", PINK, DARK_PINK),
            Button(center_x, 400, button_width, button_height, "Hard", PINK, DARK_PINK)
        ]
        
        self.cards = []
        self.flipped_cards = []
        self.matched_pairs = 0
        self.can_flip = True
        
    def load_high_scores(self):
        try:
            with open("highscores.json", "r") as f:
                self.high_scores = json.load(f)
        except FileNotFoundError:
            self.high_scores = {'easy': [], 'medium': [], 'hard': []}
            
    def save_high_scores(self):
        with open("highscores.json", "w") as f:
            json.dump(self.high_scores, f)
            
    def create_board(self, difficulty):
        self.difficulty = difficulty
        if difficulty == "easy":
            rows, cols = 4, 4
            self.time_limit = 120
            self.max_moves = 30  # Added: Maximum moves for easy difficulty
        elif difficulty == "medium":
            rows, cols = 6, 6
            self.time_limit = 180
            self.max_moves = 50  # Added: Maximum moves for medium difficulty
        else:
            rows, cols = 8, 8
            self.time_limit = 240
            self.max_moves = 70  # Added: Maximum moves for hard difficulty
            
        # Calculate card dimensions and layout
        board_margin = 100  # Increased margin for info panel
        card_margin = 10
        available_width = SCREEN_WIDTH - (2 * board_margin)
        available_height = SCREEN_HEIGHT - (2 * board_margin)
        
        card_width = (available_width - (cols - 1) * card_margin) // cols
        card_height = (available_height - (rows - 1) * card_margin) // rows
        
        # Make cards square
        card_size = min(card_width, card_height)
        
        # Center the board
        board_width = cols * card_size + (cols - 1) * card_margin
        board_height = rows * card_size + (rows - 1) * card_margin
        start_x = (SCREEN_WIDTH - board_width) // 2
        start_y = (SCREEN_HEIGHT - board_height) // 2 + 100  # Moved down for info panel
        
        # Select and shuffle symbols
        pairs_needed = (rows * cols) // 2
        selected_symbols = random.sample(self.symbols, pairs_needed) * 2
        random.shuffle(selected_symbols)
        
        # Create cards
        self.cards = []
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * (card_size + card_margin)
                y = start_y + row * (card_size + card_margin)
                symbol = selected_symbols.pop()
                self.cards.append(Card(x, y, card_size, card_size, symbol))
                
        self.matched_pairs = 0
        self.moves = 0
        self.start_time = time.time()
        self.flipped_cards = []
        self.can_flip = True
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
                
            if self.state == GameState.MENU:
                for button in self.menu_buttons:
                    if button.handle_event(event):
                        if button.text == "Play Game":
                            self.state = GameState.DIFFICULTY
                        elif button.text == "Exit":
                            return False
                            
            elif self.state == GameState.DIFFICULTY:
                for button in self.difficulty_buttons:
                    if button.handle_event(event):
                        self.create_board(button.text.lower())
                        self.state = GameState.GAME
                        
            elif self.state == GameState.GAME:
                if event.type == pygame.MOUSEBUTTONDOWN and self.can_flip:
                    for card in self.cards:
                        if card.rect.collidepoint(event.pos) and not card.is_matched and not card.is_flipped:
                            self.flip_card(card)
                            
            elif self.state == GameState.GAME_OVER:
                # Handle return to menu
                mouse_pos = pygame.mouse.get_pos()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if pygame.Rect(SCREEN_WIDTH//2 - 125, 500, 250, 60).collidepoint(mouse_pos):
                        self.state = GameState.MENU
                        
        return True
        
    def flip_card(self, card):
        if not card.is_flipped and len(self.flipped_cards) < 2:
            card.is_flipped = True
            self.flipped_cards.append(card)
            
            if len(self.flipped_cards) == 2:
                self.moves += 1
                self.can_flip = False
                
    def update(self):
        # Update card animations
        for card in self.cards:
            card.animate()
            
        # Check for matches
        if len(self.flipped_cards) == 2 and not self.can_flip:
            all_animations_complete = all(
                (c.flip_progress >= 0.99 if c.is_flipped else c.flip_progress <= 0.01)
                for c in self.flipped_cards
            )
            
            if all_animations_complete:
                if self.flipped_cards[0].symbol == self.flipped_cards[1].symbol:
                    self.flipped_cards[0].is_matched = True
                    self.flipped_cards[1].is_matched = True
                    self.matched_pairs += 1
                    
                    if self.matched_pairs == len(self.cards) // 2:
                        self.handle_game_over(True)
                else:
                    # Wait a bit before flipping cards back
                    pygame.time.wait(500)
                    for card in self.flipped_cards:
                        card.is_flipped = False
                        
                self.flipped_cards = []
                self.can_flip = True
            
        # Update game time
        if self.state == GameState.GAME and self.start_time:
            self.elapsed_time = int(time.time() - self.start_time)
            if self.elapsed_time >= self.time_limit or self.moves >= self.max_moves:
                self.handle_game_over(False)
                
    def handle_game_over(self, won):
        if won:
            self.winning_streak += 1
            self.score = self.calculate_score()
            self.high_scores[self.difficulty].append({
                'score': self.score,
                'moves': self.moves,
                'time': self.elapsed_time
            })
            self.save_high_scores()
        else:
            self.winning_streak = 0
        self.state = GameState.GAME_OVER
        
    def calculate_score(self):
        base_score = (len(self.cards) // 2) * 100
        move_penalty = self.moves * 10
        time_penalty = self.elapsed_time * 2
        return max(0, base_score - move_penalty - time_penalty)
        
    def draw_info_panel(self):
        # Draw info panel background
        info_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 80)
        pygame.draw.rect(SCREEN, PINK, info_rect)
        pygame.draw.line(SCREEN, MAROON, (0, 80), (SCREEN_WIDTH, 80), 3)
        
        # Draw game info
        font = FONT
        
        # Time remaining
        time_left = max(0, self.time_limit - self.elapsed_time)
        time_text = font.render(f"Time: {time_left}s", True, MAROON)
        SCREEN.blit(time_text, (20, 25))
        
        # Moves
        moves_text = font.render(f"Moves: {self.moves}/{self.max_moves}", True, MAROON)
        moves_rect = moves_text.get_rect(center=(SCREEN_WIDTH//2, 40))
        SCREEN.blit(moves_text, moves_rect)
        
        # Winning streak
        streak_text = font.render(f"Streak: {self.winning_streak}", True, MAROON)
        SCREEN.blit(streak_text, (SCREEN_WIDTH - 200, 25))
        
    def draw(self):
        SCREEN.fill(WHITE)
        
        if self.state == GameState.MENU:
            # Draw title
            title_font = pygame.font.Font(None, 80)
            title = title_font.render("Memory Game", True, MAROON)
            title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 150))
            SCREEN.blit(title, title_rect)
            
            # Draw buttons
            for button in self.menu_buttons:
                button.draw(SCREEN)
                
        elif self.state == GameState.DIFFICULTY:
            # Draw title
            title_font = pygame.font.Font(None, 80)
            title = title_font.render("Select Difficulty", True, MAROON)
            title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 150))
            SCREEN.blit(title, title_rect)
            
            # Draw buttons
            for button in self.difficulty_buttons:
                button.draw(SCREEN)
                
        elif self.state == GameState.GAME:
            self.draw_info_panel()
            
            # Draw cards
            for card in self.cards:
                card.draw(SCREEN)
                
        elif self.state == GameState.GAME_OVER:
            # Draw game over screen
            title_font = pygame.font.Font(None, 80)
            title = title_font.render("Game Over", True, MAROON)
            title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 150))
            SCREEN.blit(title, title_rect)
            
            # Draw score, moves, and time in separate lines
            score_font = pygame.font.Font(None, 60)
            score_text = score_font.render(f"Score: {self.score}", True, MAROON)
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, 250))
            SCREEN.blit(score_text, score_rect)
            
            moves_text = score_font.render(f"Moves: {self.moves}/{self.max_moves}", True, MAROON)
            moves_rect = moves_text.get_rect(center=(SCREEN_WIDTH//2, 320))
            SCREEN.blit(moves_text, moves_rect)
            
            time_text = score_font.render(f"Time: {self.elapsed_time}s", True, MAROON)
            time_rect = time_text.get_rect(center=(SCREEN_WIDTH//2, 390))
            SCREEN.blit(time_text, time_rect)
            
            # Draw return to menu button
            return_button = Button(SCREEN_WIDTH//2 - 125, 500, 250, 60, "Menu", PINK, DARK_PINK)
            return_button.draw(SCREEN)
            
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            clock.tick(60)
            
        pygame.quit()

if __name__ == "__main__":
    game = MemoryGame()
    game.run()
