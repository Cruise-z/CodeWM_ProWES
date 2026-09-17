"""Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to collisions
between the ball and game boundaries, paddle, and bricks.
"""

from typing import Optional
from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the game boundaries.

    Updates the ball's velocity when it hits the left, right, or top walls.
    Does not handle bottom-out collisions.

    Args:
        ball: The ball object to reflect.
        width: The width of the game area.
        height: The height of the game area.
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
    """Detect and respond to collision between ball and paddle.

    Adjusts ball velocity based on where it hits the paddle to create angle
    variation. Ensures minimum upward velocity.

    Args:
        ball: The ball object.
        paddle: The paddle object.
    """
    # Check if ball intersects with paddle
    # Ball's vertical range
    ball_top = ball.y - ball.radius
    ball_bottom = ball.y + ball.radius
    # Paddle's vertical range
    paddle_top = paddle.y - paddle.width / 2
    paddle_bottom = paddle.y + paddle.width / 2
    
    # If ball is below paddle and moving down
    if (ball_bottom >= paddle_top and 
        ball_top <= paddle_bottom and 
        ball.vy > 0):
        
        # Calculate contact point relative to center of paddle
        paddle_center_x = paddle.x
        contact_offset = (ball.x - paddle_center_x) / (paddle.width / 2)
        
        # Reflect vertically
        ball.bounce_y()
        
        # Adjust horizontal velocity based on contact point
        ball.vx += contact_offset * 10  # Arbitrary scaling factor
        
        # Ensure minimum upward velocity
        if ball.vy >= 0:
            ball.vy = -abs(ball.vy) * 1.1  # Slightly increase speed going up


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> Optional[str]:
    """Detect collision between ball and rectangle, return axis of collision.

    Calculates the minimum translation vector to separate the ball from the
    rectangle and reflects the ball accordingly.

    Args:
        ball: The ball object.
        rx: Rectangle x-coordinate (top-left).
        ry: Rectangle y-coordinate (top-left).
        rw: Rectangle width.
        rh: Rectangle height.

    Returns:
        'x' if collision occurred along x-axis,
        'y' if collision occurred along y-axis,
        None if no collision.
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y
    
    # Check if collision occurred
    if (dist_x**2 + dist_y**2) <= ball.radius**2:
        # Determine which axis had less penetration
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)
        
        if pen_x < pen_y:
            # Reflect on x-axis
            if dist_x > 0:
                ball.x = closest_x + ball.radius
            else:
                ball.x = closest_x - ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Reflect on y-axis
            if dist_y > 0:
                ball.y = closest_y + ball.radius
            else:
                ball.y = closest_y - ball.radius
            ball.bounce_y()
            return 'y'
    
    return None