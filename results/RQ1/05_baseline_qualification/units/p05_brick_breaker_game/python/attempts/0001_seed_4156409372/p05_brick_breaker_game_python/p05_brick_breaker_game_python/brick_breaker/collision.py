"""Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to
collisions between game entities.
"""

import math
from typing import Optional, Tuple
from .ball import Ball
from .paddle import Paddle


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Apply wall reflections to the ball.

    Args:
        ball: The ball to reflect.
        width: Width of the game area.
        height: Height of the game area.
    """
    # Left and right walls
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius
        ball.bounce_x()

    # Top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Detect and respond to ball-paddle collision.

    Args:
        ball: The ball object.
        paddle: The paddle object.
    """
    # Calculate the closest point on the paddle to the ball
    closest_x = max(paddle.x - paddle.width / 2, min(ball.x, paddle.x + paddle.width / 2))
    closest_y = paddle.y - paddle.width / 2  # assuming paddle is centered vertically

    # Calculate distance between ball center and closest point
    dx = ball.x - closest_x
    dy = ball.y - closest_y
    distance = math.sqrt(dx * dx + dy * dy)

    # If collision occurs
    if distance < ball.radius:
        # Determine collision normal (simple approach: just bounce off center)
        # Adjust ball position to prevent sticking
        if dy < 0:
            # Ball is above the paddle
            ball.y = closest_y - ball.radius
        else:
            # Ball is below the paddle
            ball.y = closest_y + ball.radius
            
        # Reflect ball vertically
        ball.bounce_y()
        
        # Add some angle based on where the ball hits the paddle
        # Calculate offset from paddle center (-1 to 1)
        offset = (ball.x - paddle.x) / (paddle.width / 2)
        
        # Modify x velocity based on offset to create angle
        # Ensure minimum upward velocity
        ball.vx += offset * 30.0  # Adjust multiplier as needed
        if ball.vy > 0:
            ball.vy = -abs(ball.vy)  # Ensure upward direction
        else:
            ball.vy = min(-abs(ball.vy), -30.0)  # Ensure minimum upward velocity


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> Optional[str]:
    """Detect and respond to ball-rectangle collision.

    Args:
        ball: The ball object.
        rx: Rectangle x coordinate (top-left corner).
        ry: Rectangle y coordinate (top-left corner).
        rw: Rectangle width.
        rh: Rectangle height.

    Returns:
        The axis of collision ('x', 'y') or None if no collision occurred.
    """
    # Find the closest point on the rectangle to the ball
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))

    # Calculate distance between ball center and closest point
    dx = ball.x - closest_x
    dy = ball.y - closest_y
    distance = math.sqrt(dx * dx + dy * dy)

    # Check if collision occurred
    if distance < ball.radius:
        # Calculate penetration depth in both directions
        pen_x = ball.radius - abs(dx)
        pen_y = ball.radius - abs(dy)

        # Determine which axis has less penetration (smallest penetration)
        if pen_x < pen_y:
            # Horizontal collision
            if dx > 0:
                ball.x = closest_x - ball.radius
            else:
                ball.x = closest_x + ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Vertical collision
            if dy > 0:
                ball.y = closest_y - ball.radius
            else:
                ball.y = closest_y + ball.radius
            ball.bounce_y()
            return 'y'

    return None