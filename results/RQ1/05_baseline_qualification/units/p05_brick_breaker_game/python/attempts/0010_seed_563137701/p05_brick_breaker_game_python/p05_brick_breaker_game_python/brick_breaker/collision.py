"""Collision detection and response module for the brick breaker game.

This module provides pure functions for detecting and responding to
collisions between the ball and various game elements like walls, paddle,
and bricks.
"""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    This function handles collisions with the left, right, and top walls.
    It modifies the ball's velocity to reverse direction and clamps its
    position to stay within the game bounds.

    Args:
        ball: The ball object to check and modify.
        width: The width of the game window.
        height: The height of the game window.
    """
    # Handle left and right walls
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to left edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to right edge
        ball.bounce_x()

    # Handle top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to top edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Handle collision between the ball and the paddle.

    This function detects if the ball intersects with the paddle and
    responds by reflecting the ball vertically. It also adjusts the
    horizontal velocity based on where the ball hits the paddle to
    create angle variations.

    Args:
        ball: The ball object to check and modify.
        paddle: The paddle object to check against.
    """
    # Check if ball is below paddle and moving downward
    if (ball.y + ball.radius >= paddle.y - paddle.width / 2 and
            ball.vy > 0):
        # Calculate the distance from ball center to paddle center
        paddle_center_x = paddle.x
        ball_center_x = ball.x
        diff = ball_center_x - paddle_center_x
        
        # Calculate the relative position (-1 to 1)
        rel_pos = diff / (paddle.width / 2)
        
        # Adjust horizontal velocity based on where the ball hits the paddle
        # This creates a more natural angle variation
        ball.vx = rel_pos * abs(ball.vx)  # Scale horizontal velocity
        
        # Ensure minimum upward velocity
        if ball.vy < 30:  # Minimum upward velocity threshold
            ball.vy = 30
            
        ball.bounce_y()


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between the ball and a rectangle, and respond appropriately.

    This function implements circle-AABB (Axis-Aligned Bounding Box) collision
    detection. When a collision occurs, it determines the axis of minimum
    penetration and reflects the ball accordingly, adjusting the ball's
    position to resolve the overlap.

    Args:
        ball: The ball object to check and modify.
        rx: X-coordinate of the rectangle's top-left corner.
        ry: Y-coordinate of the rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        The axis ('x' or 'y') along which the ball was reflected, or None
        if there was no collision.
    """
    # Find the closest point on the rectangle to the ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))

    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y

    # Check if collision occurred
    if dist_x**2 + dist_y**2 <= ball.radius**2:
        # Determine which axis has the minimum penetration
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)

        # Reflect on the axis with minimum penetration
        if pen_x < pen_y:
            # Reflect on x-axis
            ball.x = closest_x + (dist_x / abs(dist_x)) * ball.radius
            ball.bounce_x()
            return 'x'
        else:
            # Reflect on y-axis
            ball.y = closest_y + (dist_y / abs(dist_y)) * ball.radius
            ball.bounce_y()
            return 'y'
    
    return None