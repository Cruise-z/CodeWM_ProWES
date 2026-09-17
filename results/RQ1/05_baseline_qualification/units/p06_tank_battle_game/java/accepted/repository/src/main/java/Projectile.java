/**
 * Projectile with shooterId, mutable position via setPosition only, copy.
 */
public class Projectile {
    private final String shooterId;
    private Position position;
    private final Orientation orientation;

    /**
     * Creates a new projectile with the given properties.
     *
     * @param shooterId the id of the tank that fired this projectile
     * @param position the initial position of the projectile
     * @param orientation the direction the projectile is moving
     * @throws IllegalArgumentException if shooterId is null or blank,
     *                                  or if position or orientation is null
     */
    public Projectile(String shooterId, Position position, Orientation orientation) {
        if (shooterId == null || shooterId.isBlank()) {
            throw new IllegalArgumentException("Projectile shooterId cannot be null or blank");
        }
        if (position == null) {
            throw new IllegalArgumentException("Projectile position cannot be null");
        }
        if (orientation == null) {
            throw new IllegalArgumentException("Projectile orientation cannot be null");
        }

        this.shooterId = shooterId;
        this.position = position;
        this.orientation = orientation;
    }

    /**
     * Returns the id of the tank that fired this projectile.
     *
     * @return the shooter's id
     */
    public String getShooterId() {
        return shooterId;
    }

    /**
     * Returns the current position of this projectile.
     *
     * @return the projectile's position
     */
    public Position getPosition() {
        return position;
    }

    /**
     * Returns the orientation of this projectile.
     *
     * @return the projectile's orientation
     */
    public Orientation getOrientation() {
        return orientation;
    }

    /**
     * Sets the position of this projectile.
     *
     * @param position the new position
     * @throws IllegalArgumentException if position is null
     */
    void setPosition(Position position) {
        if (position == null) {
            throw new IllegalArgumentException("Projectile position cannot be null");
        }
        this.position = position;
    }

    /**
     * Creates a copy of this projectile.
     * The copy will have the same shooterId, position, and orientation.
     *
     * @return a new Projectile instance with the same properties
     */
    public Projectile copy() {
        return new Projectile(shooterId, position, orientation);
    }
}