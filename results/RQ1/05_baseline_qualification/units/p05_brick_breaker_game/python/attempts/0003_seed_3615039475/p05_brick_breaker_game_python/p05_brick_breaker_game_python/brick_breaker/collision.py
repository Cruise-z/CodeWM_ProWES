"""Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to
collisions between the ball and various game elements.
"""

from typing import Optional
from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    Args:
        ball: The ball object to reflect.
        width: The width of the game area.
        height: The height of the game area.
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
        ball: The ball object.
        paddle: The paddle object.
    """
    # Check if ball is overlapping with paddle
    # Ball is above paddle and moving downward
    if (ball.y + ball.radius >= paddle.y - paddle.height / 2 and
        ball.y - ball.radius <= paddle.y + paddle.height / 2 and
        ball.x >= paddle.x - paddle.width / 2 and
        ball.x <= paddle.x + paddle.width / 2 and
        ball.vy > 0):
        
        # Calculate the point of contact on the paddle (normalized between -1 and 1)
        contact_point = (ball.x - paddle.x) / (paddle.width / 2)
        
        # Adjust horizontal velocity based on where the ball hit the paddle
        # This creates a more natural angle reflection
        ball.vx = contact_point * abs(ball.vx)  # Scale horizontal velocity
        
        # Ensure the ball moves upward after hitting the paddle
        ball.vy = -abs(ball.vy)


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> Optional[str]:
    """Detect collision between ball and rectangle, and resolve it.

    Args:
        ball: The ball object.
        rx: X-coordinate of the rectangle's top-left corner.
        ry: Y-coordinate of the rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        'x' if collision occurred on x-axis,
        'y' if collision occurred on y-axis,
        None if no collision occurred.
    """
    # Find the closest point on the rectangle to the ball
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y
    
    # Check if collision occurred
    if (dist_x ** 2 + dist_y ** 2) <= ball.radius ** 2:
        # Determine which axis had the minimum penetration
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)
        
        # Resolve collision along the axis with minimum penetration
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