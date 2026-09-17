"""Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to
collisions between the ball and various game elements.
"""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    This function handles bouncing the ball off the left, right, and top walls.
    It does not handle bottom-out detection.

    Args:
        ball: The ball object to reflect.
        width: Width of the game area.
        height: Height of the game area.
    """
    # Left wall
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    
    # Right wall
    if ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()
    
    # Top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Handle collision between the ball and the paddle.

    This function reflects the ball off the paddle and adjusts its horizontal
    velocity based on where it hits the paddle to create angle changes.

    Args:
        ball: The ball object.
        paddle: The paddle object.
    """
    # Define paddle boundaries
    paddle_left = paddle.x - paddle.width / 2
    paddle_right = paddle.x + paddle.width / 2
    paddle_top = paddle.y - paddle.height / 2
    paddle_bottom = paddle.y + paddle.height / 2
    
    # Check if ball is colliding with paddle
    if (ball.x + ball.radius >= paddle_left and 
        ball.x - ball.radius <= paddle_right and
        ball.y + ball.radius >= paddle_top and
        ball.y - ball.radius <= paddle_bottom):
        
        # Reflect vertically
        ball.bounce_y()
        
        # Adjust horizontal velocity based on where the ball hits the paddle
        # Find the relative position on the paddle (between -0.5 and 0.5)
        relative_position = (ball.x - paddle.x) / (paddle.width / 2)
        
        # Adjust the horizontal velocity proportionally to the hit position
        # Ensure we don't make the ball go straight up
        ball.vx = relative_position * abs(ball.vx) * 1.1  # Add some extra speed
        
        # Ensure minimum upward velocity
        if ball.vy >= 0:
            ball.vy = -abs(ball.vy)


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between a ball and a rectangle, and resolve it.

    This function detects if a ball collides with a rectangle and determines
    which axis (x or y) to reflect on to resolve the collision.

    Args:
        ball: The ball object.
        rx: X coordinate of the rectangle's top-left corner.
        ry: Y coordinate of the rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        'x' if collision occurred along the x-axis, 'y' if along the y-axis,
        or None if no collision occurred.
    """
    # Calculate the closest point on the rectangle to the ball
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y
    
    # Check if collision occurred (distance is less than or equal to radius)
    distance_squared = dist_x**2 + dist_y**2
    if distance_squared <= ball.radius**2:
        # Determine which axis to reflect on
        # Find the minimum distance to the edges
        dist_to_left = abs(ball.x - rx)
        dist_to_right = abs(ball.x - (rx + rw))
        dist_to_top = abs(ball.y - ry)
        dist_to_bottom = abs(ball.y - (ry + rh))
        
        min_dist = min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)
        
        # Resolve collision based on which edge was closest
        if min_dist == dist_to_left or min_dist == dist_to_right:
            # Reflect on x-axis
            ball.bounce_x()
            # Adjust position to prevent sticking
            if dist_to_left < dist_to_right:
                ball.x = rx - ball.radius
            else:
                ball.x = rx + rw + ball.radius
            return 'x'
        else:
            # Reflect on y-axis
            ball.bounce_y()
            # Adjust position to prevent sticking
            if dist_to_top < dist_to_bottom:
                ball.y = ry - ball.radius
            else:
                ball.y = ry + rh + ball.radius
            return 'y'
    
    return None