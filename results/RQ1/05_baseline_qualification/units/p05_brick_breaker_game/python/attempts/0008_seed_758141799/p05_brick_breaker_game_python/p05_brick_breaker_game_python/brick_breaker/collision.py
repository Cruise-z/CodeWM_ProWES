"""Collision detection and response functions for the brick breaker game."""

from .ball import Ball
from .paddle import Paddle
from .brick import Brick


def reflect_off_walls(ball: Ball, width: int, height: int) -> None:
    """
    Reflect the ball off the walls of the game area.

    Args:
        ball: The ball object to reflect.
        width: Width of the game area.
        height: Height of the game area.
    """
    # Left and right wall collisions
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius  # Clamp to boundary
        ball.bounce_x()
    elif ball.x + ball.radius >= width:
        ball.x = width - ball.radius  # Clamp to boundary
        ball.bounce_x()

    # Top wall collision
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius  # Clamp to boundary
        ball.bounce_y()


def collide_ball_with_paddle(ball: Ball, paddle: Paddle) -> None:
    """
    Handle collision between the ball and the paddle.

    Args:
        ball: The ball object.
        paddle: The paddle object.
    """
    # Check if ball is above the paddle and moving downward
    if (ball.y + ball.radius >= paddle.y - paddle.width / 2 and
            ball.vy > 0):
        
        # Check horizontal overlap
        if (abs(ball.x - paddle.x) < (paddle.width / 2 + ball.radius)):
            
            # Calculate the contact point relative to paddle center
            contact_point = (ball.x - paddle.x) / (paddle.width / 2)
            
            # Adjust horizontal velocity based on where the ball hits the paddle
            ball.vx = contact_point * 100  # Arbitrary scaling factor
            
            # Ensure minimum upward velocity
            if ball.vy < 50:
                ball.vy = 50
                
            # Reflect vertically
            ball.bounce_y()


def collide_ball_with_rect(ball: Ball, rx: float, ry: float, rw: float, rh: float) -> str | None:
    """
    Detect collision between a ball and a rectangle, and handle the response.

    Args:
        ball: The ball object.
        rx: X coordinate of the rectangle's top-left corner.
        ry: Y coordinate of the rectangle's top-left corner.
        rw: Width of the rectangle.
        rh: Height of the rectangle.

    Returns:
        'x', 'y', or None indicating the axis along which the ball should be reflected,
        or None if no collision occurs.
    """
    # Find the closest point on the rectangle to the ball's center
    closest_x = max(rx, min(ball.x, rx + rw))
    closest_y = max(ry, min(ball.y, ry + rh))

    # Calculate distance between ball's center and closest point
    dx = ball.x - closest_x
    dy = ball.y - closest_y
    distance = (dx ** 2 + dy ** 2) ** 0.5

    # Check for collision
    if distance < ball.radius:
        # Determine the penetration depth along each axis
        pen_x = ball.radius - abs(dx)
        pen_y = ball.radius - abs(dy)

        # Resolve collision based on the shallow penetration axis
        if pen_x < pen_y:
            # Resolve horizontally
            if dx > 0:
                ball.x += pen_x
            else:
                ball.x -= pen_x
            ball.bounce_x()
            return 'x'
        else:
            # Resolve vertically
            if dy > 0:
                ball.y += pen_y
            else:
                ball.y -= pen_y
            ball.bounce_y()
            return 'y'

    return None