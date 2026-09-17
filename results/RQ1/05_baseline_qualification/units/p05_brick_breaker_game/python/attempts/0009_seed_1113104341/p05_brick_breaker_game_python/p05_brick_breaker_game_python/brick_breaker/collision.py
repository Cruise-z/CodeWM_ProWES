"""Collision detection and response module for the brick breaker game."""

from typing import Optional
from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """
    Reflect the ball off the walls of the game area.
    
    Args:
        ball: The ball object to reflect
        width: Width of the game area
        height: Height of the game area
    """
    # Handle left and right wall collisions
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()
    
    # Handle top wall collision
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """
    Detect and respond to collision between ball and paddle.
    
    Args:
        ball: The ball object
        paddle: The paddle object
    """
    # Check if ball intersects with paddle
    if (ball.y + ball.radius >= paddle.y - paddle.width / 2 and
        ball.y - ball.radius <= paddle.y + paddle.width / 2 and
        ball.x >= paddle.x - paddle.width / 2 and
        ball.x <= paddle.x + paddle.width / 2):
        
        # Calculate the point of contact on the paddle
        contact_point = (ball.x - paddle.x) / (paddle.width / 2)
        
        # Adjust velocity based on where the ball hit the paddle
        ball.vy = -abs(ball.vy)  # Always bounce upwards
        ball.vx = contact_point * abs(ball.vx)  # Change angle based on contact point


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> Optional[str]:
    """
    Detect collision between ball and rectangle, and handle response.
    
    Args:
        ball: The ball object
        rx: Rectangle x coordinate
        ry: Rectangle y coordinate
        rw: Rectangle width
        rh: Rectangle height
        
    Returns:
        'x' if collision occurred on x-axis, 'y' if on y-axis, None if no collision
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance between ball center and closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y
    
    # Check if collision occurred
    if (dist_x**2 + dist_y**2) < (ball.radius**2):
        # Determine which axis had the minimum penetration
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)
        
        if pen_x < pen_y:
            # Collision on x-axis
            if dist_x > 0:
                ball.x = closest_x - ball.radius
            else:
                ball.x = closest_x + rw + ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Collision on y-axis
            if dist_y > 0:
                ball.y = closest_y - ball.radius
            else:
                ball.y = closest_y + rh + ball.radius
            ball.bounce_y()
            return 'y'
    
    return None