import pygame
import gamesettings as gs
from info_panel import Scoring
from random import choice


class Enemy(pygame.sprite.Sprite):
    def __init__(self, game, image_dict, group, type, row_num, col_num, size):
        super().__init__(group)
        self.GAME = game
        #  Type of enemy (Attributes for enemy depend on the type)
        self.type = type

        #  Attributes (dependent on our enemy type)
        self.speed = gs.ENEMIES[self.type]["speed"]        #  Speed of the enemy
        self.wall_hack = gs.ENEMIES[self.type]["wall_hack"]  #  Enemy can move through walls
        self.chase_player = gs.ENEMIES[self.type]["chase_player"]   #  Enemy wil chase the player
        self.LoS = gs.ENEMIES[self.type]["LoS"] * size            #  Distance Enemy can see player
        self.see_player_hack = gs.ENEMIES[self.type]["see_player_hack"]      #  Enemy can see player through walls

        #  Level Matrix spawn coordinates
        self.row = row_num
        self.col = col_num

        #  Spawn Coordinates of Enemy
        self.size = size
        self.x = self.col * self.size
        self.y = (self.row * self.size) + gs.Y_OFFSET

        #  Other Attributes
        self.destroyed = False
        self.direction = "left"
        self.dir_mvmt = {"left": -self.speed, "right": self.speed,
                         "up": -self.speed, "down": self.speed}
        self.change_dir_timer = pygame.time.get_ticks()
        self.dir_time = 1500

        #  Enemy Animation and Images
        self.index = 0
        self.action = f"walk_{self.direction}"
        self.image_dict = image_dict
        self.anim_frame_time = 100
        self.anim_timer = pygame.time.get_ticks()

        self.image = self.image_dict[self.action][self.index]
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

        #  Enemy line of sight
        self.start_pos = self.rect.center
        self.end_pos = self.GAME.player.rect.center


    def update(self):
        self.movement()
        self.update_line_of_sight_with_player()
        self.animate()


    def draw(self, window, x_offset):
        window.blit(self.image, (self.rect.x - x_offset, self.rect.y))
        #pygame.draw.line(window, "black", (self.start_pos[0] - x_offset, self.start_pos[1]),
        #                 (self.end_pos[0] - x_offset, self.end_pos[1]), 2)


    def movement(self):
        """Method that incorporates all movement conditions to enable the enemy to move around
        the game area"""
        #  Return out of method, if enemy is destroyed
        if self.destroyed:
            return

        #  Move enemy along the x or y axis, dependent on move direction
        move_direction = self.action.split("_")[1]
        if move_direction in ["left", "right"]:
            self.x += self.dir_mvmt[move_direction]
        else:
            self.y += self.dir_mvmt[move_direction]

        #  Reset the directions listing for the char to choose from
        directions = ["left", "right", "up", "down"]

        #  Collision detection with the Hard Blocks
        self.new_direction(self.GAME.groups["hard_block"], move_direction, directions)

        #  Collision detection with the Soft Blocks
        if self.wall_hack == False:
            self.new_direction(self.GAME.groups["soft_block"], move_direction, directions)

        #  Collision detection with the Bombs
        self.new_direction(self.GAME.groups["bomb"], move_direction, directions)

        #  Chase the player if Applciable
        if self.chase_player:
            #  if Dist greater, pass
            if self.check_LoS_distance():
                pass
            elif self.intersecting_items_with_LoS("hard_block"):
                pass
            elif self.intersecting_items_with_LoS("soft_block") and self.see_player_hack == False:
                pass
            elif self.intersecting_items_with_LoS("bomb") and self.see_player_hack == False:
                pass
            else:
                self.chase_the_player()

        #  Perform a change of direction if sufficient amount of time has elapsed
        self.change_directions(directions)

        #  Update the rect position of the enemy with the new x, y coordinates
        self.rect.update(self.x, self.y, self.size, self.size)


    def collision_detection_blocks(self, group, direction):
        #  Collision detection
        for block in group:
            #  compare each block for collision with enemy char rect
            if block.rect.colliderect(self.rect):
                if direction == "left" and self.rect.right > block.rect.right:
                    self.x = block.rect.right
                    return direction
                if direction == "right" and self.rect.left < block.rect.left:
                    self.x = block.rect.left - self.size
                    return direction
                if direction == "up" and self.rect.bottom > block.rect.bottom:
                    self.y = block.rect.bottom
                    return direction
                if direction == "down" and self.rect.top < block.rect.top:
                    self.y = block.rect.top - self.size
                    return direction
        return None


    def new_direction(self, group, move_direction, directions):
        dir = self.collision_detection_blocks(group, move_direction)
        if dir:
            directions.remove(dir)
            new_direction = choice(directions)
            self.action = f"walk_{new_direction}"
            self.change_dir_timer = pygame.time.get_ticks()


    def change_directions(self, direction_list):
        """Randomly change directions after a set amount of time elapsed"""
        #  if timer has not elapsed, return out of method
        if pygame.time.get_ticks() - self.change_dir_timer < self.dir_time:
            return

        #  if enemy coordinates do not align with the grid coordinates.
        if self.x % self.size != 0 or (self.y - gs.Y_OFFSET) % self.size != 0:
            return

        #  Calculate which row and which column the enemy is currently in.
        row = int((self.y - gs.Y_OFFSET) // self.size)
        col = int(self.x // self.size)

        #  If cell at row/column is not a 4 way intersection, return out of the method
        if row % 2 == 0 or col % 2 == 0:
            return

        #  Check the 4 directions to see if movement is possible, update the directions list
        if self.wall_hack == False:
            self.determine_if_direction_valid(direction_list, row, col)

        #  Randomly select a new direction from the remaining list of directions
        new_direction = choice(direction_list)
        self.action = f"walk_{new_direction}"

        #  Reset the change direction timer
        self.change_dir_timer = pygame.time.get_ticks()
        return


    def determine_if_direction_valid(self, directions, row, col):
        """Check the 4 directions to determine if move is possible"""
        if self.GAME.level_matrix[row - 1][col] != "_":
            directions.remove("up")
        if self.GAME.level_matrix[row + 1][col] != "_":
            directions.remove("down")
        if self.GAME.level_matrix[row][col - 1] != "_":
            directions.remove("left")
        if self.GAME.level_matrix[row][col + 1] != "_":
            directions.remove("right")

        # if directions list empty, input "left"
        if len(directions) == 0:
            directions.append("left")
        return


    def animate(self):
        """Cycle through the enemy animation images"""
        if pygame.time.get_ticks() - self.anim_timer >= self.anim_frame_time:
            self.index += 1
            if self.destroyed and self.index == len(self.image_dict[self.action]):
                self.kill()
                Scoring(self.GAME, self.GAME.groups["scores"], gs.SCORES[self.type], self.x, self.y)
            self.index = self.index % len(self.image_dict[self.action])
            self.image = self.image_dict[self.action][self.index]
            self.anim_timer = pygame.time.get_ticks()


    def destroy(self):
        """Deactivate the enemy when killed"""
        self.destroyed = True
        self.index = 0
        self.action = "death"
        self.image = self.image_dict[self.action][self.index]


    def update_line_of_sight_with_player(self):
        """Update the positions of the enemy and player characters"""
        self.start_pos = self.rect.center
        self.end_pos = self.GAME.player.rect.center


    def chase_the_player(self):
        """Change the direction towards the player if in line of sight"""
        #  Convert pixel coords to rows/col
        enemy_col = self.start_pos[0] // self.size
        enemy_row = self.start_pos[1] // self.size
        player_col = self.end_pos[0] // self.size
        player_row = self.end_pos[1] // self.size

        if enemy_col > player_col and ((self.y - gs.Y_OFFSET) % self.size) + 32 == self.size//2:
            self.action = "walk_left"
        elif enemy_col < player_col and ((self.y - gs.Y_OFFSET) % self.size) + 32 == self.size//2:
            self.action = "walk_right"
        elif enemy_row > player_row and (self.x % self.size) + 32 == self.size//2:
            self.action = "walk_up"
        elif enemy_row < player_row and (self.x % self.size) + 32 == self.size//2:
            self.action = "walk_down"

            #  Update the enemy char change direction timer
            self.change_dir_timer = pygame.time.get_ticks()


    def check_LoS_distance(self):
        """Return a True or False, if dist between player and enemy is less than LoS attribute"""
        x_dist = abs(self.end_pos[0] - self.start_pos[0])
        y_dist = abs(self.end_pos[1] - self.start_pos[1])

        if x_dist > self.LoS or y_dist > self.LoS:
            return True

        return False


    def intersecting_items_with_LoS(self, group):
        """Return True or False, if item obstructing LoS"""
        for item in self.GAME.groups[group]:
            if item.rect.clipline(self.start_pos, self.end_pos):
                return True
        return False