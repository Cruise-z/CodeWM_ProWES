"""Collision detection and response functions for the brick breaker game.

This module contains pure functions for detecting and responding to
collisions between the ball and game elements.
"""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """Reflect the ball off the walls of the game area.

    This function handles bouncing the ball off the left, right, and top walls.
    It does not handle bottom-out events (where the ball falls below the paddle).

    Args:
        ball: The ball object to check and reflect.
        width: The width of the game area.
        height: The height of the game area.
    """
    # Check for left and right wall collisions
    if ball.x - ball.radius <= 0:
        ball.bounce_x()
        ball.x = ball.radius  # Clamp to prevent sticking
    elif ball.x + ball.radius >= width:
        ball.bounce_x()
        ball.x = width - ball.radius  # Clamp to prevent sticking

    # Check for top wall collision
    if ball.y - ball.radius <= 0:
        ball.bounce_y()
        ball.y = ball.radius  # Clamp to prevent sticking


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """Detect and respond to collision between ball and paddle.

    If the ball intersects with the paddle, it will be reflected vertically.
    The horizontal velocity will be adjusted based on where the ball hits the
    paddle to create a realistic angle effect.

    Args:
        ball: The ball object to check and respond to.
        paddle: The paddle object to check against.
    """
    # Calculate the paddle's boundaries
    paddle_left = paddle.x - paddle.width / 2
    paddle_right = paddle.x + paddle.width / 2
    paddle_top = paddle.y - paddle.height / 2
    paddle_bottom = paddle.y + paddle.height / 2

    # Check if the ball is intersecting with the paddle
    if (paddle_left <= ball.x + ball.radius and
        paddle_right >= ball.x - ball.radius and
        paddle_top <= ball.y + ball.radius and
        paddle_bottom >= ball.y - ball.radius):

        # Calculate the point of contact on the paddle (0.0 to 1.0)
        contact_point = (ball.x - paddle_left) / (paddle_right - paddle_left)

        # Adjust horizontal velocity based on where the ball hits the paddle
        # Center hit results in little horizontal change, edge hits more
        max_angle = 0.8  # Maximum angle deviation in radians
        angle_offset = (contact_point - 0.5) * max_angle

        # Apply the angle adjustment to the horizontal velocity
        # The formula assumes a constant vertical velocity component
        ball.vx += angle_offset * 100  # Scale factor for sensitivity

        # Ensure the ball moves upward after hitting the paddle
        if ball.vy > 0:
            ball.vy = -ball.vy

        # Move the ball above the paddle to avoid multiple collisions
        ball.y = paddle_top - ball.radius


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """Detect collision between a ball and a rectangle, and resolve it.

    This function implements circle-AABB (Axis-Aligned Bounding Box) collision
    detection and response. It returns the axis along which the ball should be
    reflected ('x' or 'y') or None if no collision occurs.

    Args:
        ball: The ball object to check.
        rx: X-coordinate of the rectangle's top-left corner.
        ry: Y-coordinate of the rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        'x' if collision occurred along the x-axis,
        'y' if collision occurred along the y-axis,
        None if no collision occurred.
    """
    # Find the closest point on the rectangle to the ball's center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))

    # Calculate the distance between the ball's center and this closest point
    dx = ball.x - closest_x
    dy = ball.y - closest_y

    # If the distance is less than the ball's radius, a collision has occurred
    distance_squared = dx * dx + dy * dy
    if distance_squared < ball.radius * ball.radius:
        # Determine which axis had the smallest penetration
        # This gives us the correct axis to reflect on
        
        # Calculate penetration depth on both axes
        pen_x = ball.radius - abs(dx)
        pen_y = ball.radius - abs(dy)
        
        if pen_x < pen_y:
            # Reflect on x-axis
            ball.bounce_x()
            # Adjust ball position to resolve overlap
            if dx > 0:
                ball.x += pen_x
            else:
                ball.x -= pen_x
            return 'x'
        else:
            # Reflect on y-axis
            ball.bounce_y()
            # Adjust ball position to resolve overlap
            if dy > 0:
                ball.y += pen_y
            else:
                ball.y -= pen_y
            return 'y'

    return None