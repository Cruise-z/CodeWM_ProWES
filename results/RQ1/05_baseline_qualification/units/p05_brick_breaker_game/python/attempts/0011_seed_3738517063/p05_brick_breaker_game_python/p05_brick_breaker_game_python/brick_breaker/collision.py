"""Collision detection and response module for the brick breaker game.

This module contains pure functions for detecting and responding to collisions
between the ball and game elements.
"""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    This function handles collisions with the left, right, and top walls.
    It does not handle bottom-out collisions.

    Args:
        ball: The ball object to check for wall collisions
        width: The width of the game area
        height: The height of the game area
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
    """Handle collision between the ball and the paddle.

    This function detects if the ball intersects with the paddle and responds
    by reflecting the ball vertically. The horizontal velocity is adjusted
    based on where the ball hits the paddle to create angle variations.

    Args:
        ball: The ball object
        paddle: The paddle object
    """
    # Calculate paddle boundaries
    paddle_left = paddle.x - paddle.width / 2
    paddle_right = paddle.x + paddle.width / 2
    paddle_top = paddle.y - ball.radius  # Assuming paddle is centered horizontally
    paddle_bottom = paddle.y + ball.radius
    
    # Check if ball is above the paddle and moving downward
    if (ball.y + ball.radius >= paddle_top and 
        ball.y - ball.radius <= paddle_bottom and 
        ball.vy > 0):
        
        # Check horizontal overlap
        if (ball.x + ball.radius >= paddle_left and 
            ball.x - ball.radius <= paddle_right):
            
            # Reflect vertically
            ball.bounce_y()
            
            # Adjust horizontal velocity based on where ball hits paddle
            # Calculate relative position (-1 to 1, where -1 is left edge)
            relative_position = (ball.x - paddle.x) / (paddle.width / 2)
            
            # Clamp relative position to [-1, 1]
            relative_position = max(-1.0, min(1.0, relative_position))
            
            # Adjust x velocity based on relative position
            # We want the ball to go faster when hitting near edges
            ball.vx = relative_position * abs(ball.vx)


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between a ball and a rectangle, and resolve it.

    This function implements circle-AABB (Axis-Aligned Bounding Box) collision
    detection and response. It returns the axis along which the ball should be
    reflected, or None if there is no collision.

    Args:
        ball: The ball object
        rx: X-coordinate of the rectangle's top-left corner
        ry: Y-coordinate of the rectangle's top-left corner
        rw: Width of the rectangle
        rh: Height of the rectangle

    Returns:
        'x' if collision occurred along the x-axis,
        'y' if collision occurred along the y-axis,
        None if no collision occurred
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))
    
    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y
    
    # Check if collision occurred
    if (dist_x**2 + dist_y**2) <= ball.radius**2:
        # Determine which axis was hit first by checking the minimum penetration
        # Calculate penetration depth on both axes
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)
        
        # Resolve collision along the axis with smallest penetration
        if pen_x < pen_y:
            # Collision on x-axis
            if closest_x == rx:
                ball.x = rx - ball.radius  # Position ball to the left of the rectangle
            else:
                ball.x = rx + rw + ball.radius  # Position ball to the right of the rectangle
            ball.bounce_x()
            return 'x'
        else:
            # Collision on y-axis
            if closest_y == ry:
                ball.y = ry - ball.radius  # Position ball above the rectangle
            else:
                ball.y = ry + rh + ball.radius  # Position ball below the rectangle
            ball.bounce_y()
            return 'y'
    
    return None