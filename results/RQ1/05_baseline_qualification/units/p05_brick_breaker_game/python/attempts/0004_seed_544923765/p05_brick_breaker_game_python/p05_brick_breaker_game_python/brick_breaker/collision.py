"""
Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to
collisions between the ball and game elements (walls, paddle, bricks).
"""

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
    # Left and right wall collisions
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()
    
    # Top wall collision
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """
    Handle collision between the ball and the paddle.

    Args:
        ball: The ball object
        paddle: The paddle object
    """
    # Check if ball is overlapping with paddle
    # Ball's vertical position relative to paddle
    if (ball.y + ball.radius >= paddle.y - paddle.width / 2 and
        ball.y - ball.radius <= paddle.y + paddle.width / 2 and
        ball.x >= paddle.x - paddle.width / 2 and
        ball.x <= paddle.x + paddle.width / 2):
        
        # Calculate the contact point on the paddle
        contact_point = (ball.x - paddle.x) / (paddle.width / 2)
        
        # Adjust the ball's x velocity based on where it hit the paddle
        # This creates a realistic angle effect
        ball.vx = contact_point * 100  # Arbitrary scaling factor
        
        # Ensure minimum upward velocity to prevent stuck balls
        if ball.vy >= 0:
            ball.vy = -abs(ball.vy)  # Ensure ball moves upward
        else:
            ball.vy = ball.vy  # Maintain existing upward velocity


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> Optional[str]:
    """
    Detect collision between ball and rectangle, and handle response.

    Args:
        ball: The ball object
        rx: X coordinate of rectangle top-left corner
        ry: Y coordinate of rectangle top-left corner
        rw: Width of rectangle
        rh: Height of rectangle

    Returns:
        'x' if collision occurred on x-axis, 'y' if on y-axis, or None if no collision
    """
    # Find the closest point on the rectangle to the ball
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance between ball center and closest point
    distance_x = ball.x - closest_x
    distance_y = ball.y - closest_y
    
    # Check if collision occurred
    if (distance_x ** 2 + distance_y ** 2) < (ball.radius ** 2):
        # Determine penetration axis
        # Calculate the minimum translation vector
        pen_x = abs(distance_x)
        pen_y = abs(distance_y)
        
        # Resolve collision along the axis with minimum penetration
        if pen_x < pen_y:
            # Collision on x-axis
            ball.x = closest_x + (ball.x - closest_x) / abs(ball.x - closest_x) * ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Collision on y-axis
            ball.y = closest_y + (ball.y - closest_y) / abs(ball.y - closest_y) * ball.radius
            ball.bounce_y()
            return 'y'
    
    return None