"""Collision detection and response functions for the brick breaker game."""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.
    
    Args:
        ball: The ball object to reflect
        width: The width of the game area
        height: The height of the game area
    """
    # Check left and right walls
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()
    
    # Check top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Detect and respond to collision between ball and paddle.
    
    Args:
        ball: The ball object
        paddle: The paddle object
    """
    # Check if ball is overlapping with paddle
    # Ball center is at (ball.x, ball.y)
    # Paddle spans from (paddle.x - paddle.width/2, paddle.y) to (paddle.x + paddle.width/2, paddle.y)
    
    # Distance from ball center to paddle center (in x-direction)
    dx = ball.x - paddle.x
    # Distance from ball center to paddle y-coordinate
    dy = ball.y - paddle.y
    
    # Check if ball is above paddle and colliding
    if dy <= ball.radius and dy >= -ball.radius:
        # Check if ball hits paddle horizontally
        if abs(dx) <= (paddle.width / 2 + ball.radius):
            # Ball hits paddle - reflect vertically
            ball.bounce_y()
            
            # Adjust horizontal velocity based on where the ball hits the paddle
            # Calculate relative hit position (-1.0 to 1.0)
            relative_hit_pos = dx / (paddle.width / 2)
            # Apply some horizontal velocity based on where the ball hit the paddle
            # This creates a more dynamic angle
            ball.vx = relative_hit_pos * 100  # Arbitrary scaling
            
            # Ensure minimum upward velocity
            if ball.vy >= 0:
                ball.vy = -abs(ball.vy)  # Make sure it goes up


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between ball and rectangle, and resolve it.
    
    Args:
        ball: The ball object
        rx: Rectangle x coordinate (top-left)
        ry: Rectangle y coordinate (top-left)
        rw: Rectangle width
        rh: Rectangle height
        
    Returns:
        'x' if collision occurred on x-axis, 'y' if on y-axis, None if no collision
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance from ball center to closest point
    distance_x = ball.x - closest_x
    distance_y = ball.y - closest_y
    
    # Check if collision occurred
    if (distance_x ** 2 + distance_y ** 2) <= (ball.radius ** 2):
        # Calculate penetration along both axes
        pen_x = ball.radius - abs(distance_x)
        pen_y = ball.radius - abs(distance_y)
        
        # Determine which axis has smaller penetration (i.e., which axis to reflect on)
        if pen_x < pen_y:
            # Reflect on x-axis
            ball.x = closest_x + (ball.radius if distance_x >= 0 else -ball.radius)
            ball.bounce_x()
            return 'x'
        else:
            # Reflect on y-axis
            ball.y = closest_y + (ball.radius if distance_y >= 0 else -ball.radius)
            ball.bounce_y()
            return 'y'
    
    return None