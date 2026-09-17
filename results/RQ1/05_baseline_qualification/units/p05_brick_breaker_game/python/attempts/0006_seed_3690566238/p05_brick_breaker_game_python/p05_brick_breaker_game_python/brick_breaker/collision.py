"""Collision detection and response for the Brick Breaker game."""

from typing import Optional
from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    Args:
        ball: The ball to reflect.
        width: The width of the game area.
        height: The height of the game area.
    """
    # Handle left and right walls
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()

    # Handle top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Detect and respond to collision between ball and paddle.

    Args:
        ball: The ball to check.
        paddle: The paddle to check.
    """
    # Check if ball is above the paddle and moving downward
    if (ball.y + ball.radius >= paddle.y - paddle.height / 2 and
            ball.vy > 0):
        
        # Check horizontal overlap
        paddle_left = paddle.x - paddle.width / 2
        paddle_right = paddle.x + paddle.width / 2
        ball_left = ball.x - ball.radius
        ball_right = ball.x + ball.radius
        
        if (ball_left <= paddle_right and 
            ball_right >= paddle_left):
            
            # Calculate bounce angle based on where ball hits paddle
            # Center of paddle
            paddle_center = paddle.x
            
            # Distance from center of paddle to ball center
            offset = (ball.x - paddle_center) / (paddle.width / 2)
            
            # Apply angle based on hit position (more extreme angles near edges)
            # Ensure minimum upward velocity
            ball.vy = -abs(ball.vy)
            ball.vx = offset * abs(ball.vx) * 1.5


def collide_ball_with_rect(
    ball: Ball, 
    rx: float, 
    ry: float, 
    rw: float, 
    rh: float
) -> Optional[str]:
    """Detect collision between ball and rectangle, and resolve it.

    Args:
        ball: The ball to check.
        rx: X coordinate of rectangle top-left corner.
        ry: Y coordinate of rectangle top-left corner.
        rw: Width of rectangle.
        rh: Height of rectangle.

    Returns:
        'x' if collision occurred on x-axis, 'y' if on y-axis, None if no collision.
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance between ball center and closest point
    dx = ball.x - closest_x
    dy = ball.y - closest_y
    distance = (dx ** 2 + dy ** 2) ** 0.5
    
    # Check if collision occurred
    if distance < ball.radius:
        # Determine which axis was hit first (penetration axis)
        # Calculate penetration along each axis
        pen_x = ball.radius - abs(dx)
        pen_y = ball.radius - abs(dy)
        
        # Resolve collision along the axis with smallest penetration
        if pen_x < pen_y:
            # Hit on x-axis
            if dx > 0:
                ball.x = closest_x + ball.radius
            else:
                ball.x = closest_x - ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Hit on y-axis
            if dy > 0:
                ball.y = closest_y + ball.radius
            else:
                ball.y = closest_y - ball.radius
            ball.bounce_y()
            return 'y'
    
    return None