"""Collision detection and response module for the brick breaker game.

This module provides pure functions for detecting and responding to
collisions between the ball and game elements.
"""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the game boundaries.

    Handles collisions with left, right, and top walls. Does not handle
    bottom-out collisions.

    Args:
        ball: The ball object to reflect.
        width: The width of the game area.
        height: The height of the game area.
    """
    # Reflect off left and right walls
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to edge
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to edge
        ball.bounce_x()

    # Reflect off top wall
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to edge
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Detect and respond to collision between ball and paddle.

    Adjusts ball velocity based on where it hits the paddle to create
    angled bounces.

    Args:
        ball: The ball object.
        paddle: The paddle object.
    """
    # Check if ball is overlapping with paddle
    if (ball.y + ball.radius >= paddle.y - paddle.width / 2 and
        ball.y - ball.radius <= paddle.y + paddle.width / 2 and
        ball.x + ball.radius >= paddle.x - paddle.width / 2 and
        ball.x - ball.radius <= paddle.x + paddle.width / 2):

        # Calculate the point of contact on the paddle
        contact_x = ball.x
        # Normalize contact point to [-1, 1] where -1 is left edge, 1 is right edge
        normalized_contact = (contact_x - paddle.x) / (paddle.width / 2)

        # Bounce ball upward with angle based on contact point
        # Ensure minimum upward velocity
        min_vy = 10.0  # Minimum upward velocity
        ball.vy = -abs(ball.vy)  # Always bounce up
        ball.vy = max(min_vy, ball.vy)
        
        # Adjust horizontal velocity based on contact point
        # More extreme angles for edges
        ball.vx = normalized_contact * abs(ball.vx) * 1.5


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between ball and rectangle, and resolve it.

    Uses axis-aligned bounding box collision detection and resolves
    penetration by moving the ball away from the collision.

    Args:
        ball: The ball object.
        rx: X coordinate of rectangle's top-left corner.
        ry: Y coordinate of rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        The axis ('x' or 'y') along which the collision occurred, or None
        if no collision occurred.
    """
    # Find closest point on rectangle to ball center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))

    # Calculate distance from ball center to closest point
    dist_x = ball.x - closest_x
    dist_y = ball.y - closest_y

    # Check if collision occurred
    if (dist_x**2 + dist_y**2) <= ball.radius**2:
        # Determine which axis has the smallest penetration
        # Calculate penetration along each axis
        pen_x = ball.radius - abs(dist_x)
        pen_y = ball.radius - abs(dist_y)

        if pen_x < pen_y:
            # Horizontal collision
            if dist_x > 0:
                ball.x += pen_x  # Move right
            else:
                ball.x -= pen_x  # Move left
            ball.bounce_x()
            return 'x'
        else:
            # Vertical collision
            if dist_y > 0:
                ball.y += pen_y  # Move down
            else:
                ball.y -= pen_y  # Move up
            ball.bounce_y()
            return 'y'

    return None