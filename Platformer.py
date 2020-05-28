# -----------*****----------- #
# 2D Platformer by Luka Ruzic #
# -----------*****----------- #

# Import necessary libraries
from typing import Optional
import arcade

# Name of our game
SCREEN_TITLE = "Platformer by Luka Ruzic"

# How big are our image tiles
SPRITE_IMAGE_SIZE: int = 128

# Scale sprites
SPRITE_SCALE = 0.5

# Scaled sprite size for tiles
SPRITE_SIZE = int(SPRITE_IMAGE_SIZE * SPRITE_SCALE) + 1

# Size of grid to show on screen, in number of tiles
SCREEN_GRID_WIDTH = 30
SCREEN_GRID_HEIGHT = 20

# Size of screen to show, in pixels
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# ------------ PHYSICS (higher num., higher accel.) ------------ #
# Gravity
GRAVITY = 1500

# Damping - Amount of speed lost per second
DEFAULT_DAMPING = 1.0
PLAYER_DAMPING = 0.4

# Friction between objects
PLAYER_FRICTION = 1.0
WALL_FRICTION = 0.7
DYNAMIC_ITEM_FRICTION = 0.6

# Mass (defaults to 1)
PLAYER_MASS = 2.0

# Keep player from going too fast
PLAYER_MAX_HORIZONTAL_SPEED = 250
PLAYER_MAX_VERTICAL_SPEED = 1300

# Force applied to the player on the ground
PLAYER_MOVE_FORCE_ON_GROUND = 8000

# Force applied when moving left/right in the air
PLAYER_MOVE_FORCE_IN_AIR = 900

# Strength of a jump
PLAYER_JUMP_IMPULSE = 1400
# -------------------------------------------------------------- #

# Define constants that will tell how many pixels will be between the player and the screen before the scrolling
LEFT_VIEWPORT_MARGIN = 900
RIGHT_VIEWPORT_MARGIN = 900
BOTTOM_VIEWPORT_MARGIN = 50
TOP_VIEWPORT_MARGIN = 100

# Value for not-moving to have the animation go idle.
DEAD_ZONE = 0.1

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1

# How many pixels to move before we change the texture in the walking animation
DISTANCE_TO_CHANGE_TEXTURE = 10


# ---------------------- PLAYER ANIMATION ---------------------- #
class PlayerSprite(arcade.Sprite):
    def __init__(self):
        # Call the parent class
        super().__init__()
        # Define player scale
        self.scale = SPRITE_SCALE

        # Define main path of player model
        main_path = "Player/player"

        # Load idle, fall and jump animation
        self.idle_texture_pair = arcade.load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = arcade.load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = arcade.load_texture_pair(f"{main_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        for x in range(8):
            texture = arcade.load_texture_pair(f"{main_path}_walk{x}.png")
            self.walk_textures.append(texture)

        # Set the initial texture
        self.texture = self.idle_texture_pair[0]

        # Hit box will be set based on the first image used.
        self.hit_box = self.texture.hit_box_points

        # Default to face-right
        self.character_face_direction = RIGHT_FACING

        # Index of our current texture
        self.current_texture = 0

        # How far have we traveled horizontally since changing the texture
        self.x_odometer = 0

    def pymunk_moved(self, physics_engine, dx, dy, d_angle):
        # Figure out if we need to face left or right
        if dx < -DEAD_ZONE and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif dx > DEAD_ZONE and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Are we on the ground?
        is_on_ground = physics_engine.is_on_ground(self)

        # Add to the odometer how far we've moved
        self.x_odometer += dx

        # Jumping animation
        if not is_on_ground:
            if dy > DEAD_ZONE:
                self.texture = self.jump_texture_pair[self.character_face_direction]
                return
            elif dy < -DEAD_ZONE:
                self.texture = self.fall_texture_pair[self.character_face_direction]
                return

        # Idle animation
        if abs(dx) <= DEAD_ZONE:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Have we moved far enough to change the texture?
        if abs(self.x_odometer) > DISTANCE_TO_CHANGE_TEXTURE:

            # Reset the odometer
            self.x_odometer = 0

            # Advance the walking animation
            self.current_texture += 1
            if self.current_texture > 7:
                self.current_texture = 0
            self.texture = self.walk_textures[self.current_texture][self.character_face_direction]
# -------------------------------------------------------------- #


# Main game class
class GameWindow(arcade.Window):
    def __init__(self, width, height, title):
        # Call the parent class and setup the screen variables
        super().__init__(width, height, title, fullscreen=True)

        # Player sprite
        self.player_sprite: Optional[PlayerSprite] = None

        # We use lists to keep track of our sprites. Every sprite should have its own list
        self.player_list: Optional[arcade.SpriteList] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.item_list: Optional[arcade.SpriteList] = None
        self.gem_list: Optional[arcade.SpriteList] = None

        # Track the current state of what key is pressed
        self.left_pressed: bool = False
        self.right_pressed: bool = False

        # Used to keep track of our scrolling
        self.view_bottom = 0
        self.view_left = 0

        # Initialize physics engine
        self.physics_engine = Optional[arcade.PymunkPhysicsEngine]

        # Level
        self.level = 1

        # End of the level
        self.end_of_map = 0

        # Load sounds
        self.collect_gem_sound = arcade.load_sound("Sounds/gem.ogg")

        # Set background color
        arcade.set_background_color(arcade.color.AQUA)

    # Main game setup (when called the game resets)
    def setup(self, level):
        # Create the sprite lists
        self.player_list = arcade.SpriteList()
        self.gem_list = arcade.SpriteList()

        # Read in the tiled map
        map_name = f"Maps/map{level}.tmx"
        my_map = arcade.tilemap.read_tmx(map_name)

        # Calculate the right edge of the my_map in pixels
        self.end_of_map = my_map.map_size.width * SCREEN_GRID_WIDTH + 800

        # Read in the map layers
        self.wall_list = arcade.tilemap.process_layer(my_map, "Platforms", SPRITE_SCALE)
        self.item_list = arcade.tilemap.process_layer(my_map, "Dynamic Items", SPRITE_SCALE)
        self.gem_list = arcade.tilemap.process_layer(my_map, "Valuables", SPRITE_SCALE)

        # Create player sprite
        self.player_sprite = PlayerSprite()

        # Variables used for setting player location
        grid_x = 2
        grid_y = 2

        # Set player location
        self.player_sprite.center_x = SPRITE_SIZE * grid_x + SPRITE_SIZE / 2
        self.player_sprite.center_y = SPRITE_SIZE * grid_y + SPRITE_SIZE / 2

        # Add player sprite to player sprite list
        self.player_list.append(self.player_sprite)

        # ----------------------- PHYSICS ENGINE ----------------------- #
        # The default damping for every object controls the percent of velocity the object will keep each second.
        damping = DEFAULT_DAMPING

        # Set the gravity
        gravity = (0, -GRAVITY)

        # Create the physics engine
        self.physics_engine = arcade.PymunkPhysicsEngine(damping=damping,
                                                         gravity=gravity)
        # Create physics for player. Damping should be lower so player doesn't travel too far when keys are released
        self.physics_engine.add_sprite(self.player_sprite,
                                       friction=PLAYER_FRICTION,
                                       mass=PLAYER_MASS,
                                       moment=arcade.PymunkPhysicsEngine.MOMENT_INF,
                                       collision_type="player",
                                       max_horizontal_velocity=PLAYER_MAX_HORIZONTAL_SPEED,
                                       max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED)

        # Create physics for walls. They should be set to STATIC
        self.physics_engine.add_sprite_list(self.wall_list,
                                            friction=WALL_FRICTION,
                                            collision_type="wall",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        # Create physics for items
        self.physics_engine.add_sprite_list(self.item_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="item")

        # Create physics for valuables
        self.physics_engine.add_sprite_list(self.gem_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="item")
        # -------------------------------------------------------------- #

    # Called whenever a key is pressed
    def on_key_press(self, key, modifiers):
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
        elif key == arcade.key.UP or key == arcade.key.SPACE or key == arcade.key.W:
            # Find out if player is standing on ground
            if self.physics_engine.is_on_ground(self.player_sprite):
                # If yes, make player jump
                impulse = (0, PLAYER_JUMP_IMPULSE)
                self.physics_engine.apply_impulse(self.player_sprite, impulse)

    # Called whenever a key is released
    def on_key_release(self, key, modifiers):
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

    # Movement and game logic
    def on_update(self, delta_time):
        # -------------------- UPDATE PLAYER FORCES -------------------- #
        is_on_ground = self.physics_engine.is_on_ground(self.player_sprite)

        if self.left_pressed and not self.right_pressed:
            # Create a force to the left and apply it.
            if is_on_ground:
                force = (-PLAYER_MOVE_FORCE_ON_GROUND, 0)
            else:
                force = (-PLAYER_MOVE_FORCE_IN_AIR, 0)

            self.physics_engine.apply_force(self.player_sprite, force)

            # Set friction to zero for the player while moving
            self.physics_engine.set_friction(self.player_sprite, 0)

        elif self.right_pressed and not self.left_pressed:
            # Create a force to the right and apply it.
            if is_on_ground:
                force = (PLAYER_MOVE_FORCE_ON_GROUND, 0)
            else:
                force = (PLAYER_MOVE_FORCE_IN_AIR, 0)

            self.physics_engine.apply_force(self.player_sprite, force)

            # Set friction to zero for the player while moving
            self.physics_engine.set_friction(self.player_sprite, 0)

        else:
            # Player's feet are not moving so we increase the friction to stop
            self.physics_engine.set_friction(self.player_sprite, 1.0)
        # -------------------------------------------------------------- #

        # See if the user got to the end of the level
        if self.player_sprite.center_x >= self.end_of_map:
            # Advance to the next level
            self.level += 1

            # Load the next level
            self.setup(self.level)

        # ------------------- MANAGE SCREEN SCROLLING ------------------ #

        # Track if we need to change the viewport
        changed = False

        # Scroll left
        left_boundary = self.view_left + LEFT_VIEWPORT_MARGIN
        if self.player_sprite.left < left_boundary:
            self.view_left -= left_boundary - self.player_sprite.left
            changed = True

        # Scroll right
        right_boundary = self.view_left + SCREEN_WIDTH - RIGHT_VIEWPORT_MARGIN
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary
            changed = True

        # Scroll up
        top_boundary = self.view_bottom + SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary
            changed = True

        # Scroll down
        bottom_boundary = self.view_bottom + BOTTOM_VIEWPORT_MARGIN
        if self.player_sprite.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player_sprite.bottom
            changed = True

        if changed:
            # Only scroll to integers. Otherwise we end up with pixels that don't line up on the screen
            self.view_bottom = int(self.view_bottom)
            self.view_left = int(self.view_left)

            # Do the scrolling
            arcade.set_viewport(self.view_left,
                                SCREEN_WIDTH + self.view_left,
                                self.view_bottom,
                                SCREEN_HEIGHT + self.view_bottom)
        # -------------------------------------------------------------- #

        # See if we hit any coins
        gem_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.gem_list)

        # Loop through each coin we hit (if any) and remove it
        for gem in gem_hit_list:
            # Remove the coin
            gem.remove_from_sprite_lists()

            # Play a sound
            arcade.play_sound(self.collect_gem_sound)

        self.physics_engine.step()

    # Draws everything on the screen
    def on_draw(self):
        arcade.start_render()
        self.wall_list.draw()
        self.item_list.draw()
        self.gem_list.draw()
        self.player_list.draw()


# Main function
def main():
    window = GameWindow(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup(window.level)
    arcade.run()


if __name__ == "__main__":
    main()
