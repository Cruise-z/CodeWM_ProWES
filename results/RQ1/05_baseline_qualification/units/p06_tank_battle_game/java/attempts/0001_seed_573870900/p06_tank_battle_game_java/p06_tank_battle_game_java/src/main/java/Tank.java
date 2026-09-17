/**
 * Mutable tank entity with id, position, orientation, health, rotation, damage, copy.
 */
public class Tank {
    private final String id;
    private Position position;
    private Orientation orientation;
    private int health;

    /**
     * Creates a new tank with the given properties.
     *
     * @param id the unique identifier for the tank
     * @param position the initial position of the tank
     * @param orientation the initial orientation of the tank
     * @param health the initial health of the tank
     * @throws IllegalArgumentException if id is blank or any parameter is null,
     *                                  or if health is negative
     */
    public Tank(String id, Position position, Orientation orientation, int health) {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("Tank ID cannot be null or blank");
        }
        if (position == null) {
            throw new IllegalArgumentException("Tank position cannot be null");
        }
        if (orientation == null) {
            throw new IllegalArgumentException("Tank orientation cannot be null");
        }
        if (health < 0) {
            throw new IllegalArgumentException("Tank health cannot be negative");
        }

        this.id = id;
        this.position = position;
        this.orientation = orientation;
        this.health = health;
    }

    /**
     * Returns the unique identifier of this tank.
     *
     * @return the tank's id
     */
    public String getId() {
        return id;
    }

    /**
     * Returns the current position of this tank.
     *
     * @return the tank's position
     */
    public Position getPosition() {
        return position;
    }

    /**
     * Returns the current orientation of this tank.
     *
     * @return the tank's orientation
     */
    public Orientation getOrientation() {
        return orientation;
    }

    /**
     * Returns the current health of this tank.
     *
     * @return the tank's health
     */
    public int getHealth() {
        return health;
    }

    /**
     * Checks if this tank is alive (health > 0).
     *
     * @return true if the tank is alive, false otherwise
     */
    public boolean isAlive() {
        return health > 0;
    }

    /**
     * Sets the position of this tank.
     *
     * @param position the new position
     * @throws IllegalArgumentException if position is null
     */
    void setPosition(Position position) {
        if (position == null) {
            throw new IllegalArgumentException("Tank position cannot be null");
        }
        this.position = position;
    }

    /**
     * Rotates this tank 90 degrees to the left.
     */
    void rotateLeft() {
        this.orientation = orientation.left();
    }

    /**
     * Rotates this tank 90 degrees to the right.
     */
    void rotateRight() {
        this.orientation = orientation.right();
    }

    /**
     * Applies damage to this tank.
     *
     * @param amount the amount of damage to apply
     * @throws IllegalArgumentException if amount is negative
     */
    void applyDamage(int amount) {
        if (amount < 0) {
            throw new IllegalArgumentException("Damage amount cannot be negative");
        }
        this.health -= amount;
        if (this.health < 0) {
            this.health = 0;
        }
    }

    /**
     * Creates a copy of this tank.
     * The copy will have the same id, position, orientation, and health.
     * This method works even when the health is zero.
     *
     * @return a new Tank instance with the same properties
     */
    public Tank copy() {
        return new Tank(id, position, orientation, health);
    }
}