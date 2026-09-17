/**
 * Enum representing cardinal directions and providing utility methods for movement
 * and reversal detection.
 */
public enum Direction {
    /** Moving up (negative y direction) */
    UP {
        @Override
        public int dx() {
            return 0;
        }

        @Override
        public int dy() {
            return -1;
        }
    },
    
    /** Moving down (positive y direction) */
    DOWN {
        @Override
        public int dx() {
            return 0;
        }

        @Override
        public int dy() {
            return 1;
        }
    },
    
    /** Moving left (negative x direction) */
    LEFT {
        @Override
        public int dx() {
            return -1;
        }

        @Override
        public int dy() {
            return 0;
        }
    },
    
    /** Moving right (positive x direction) */
    RIGHT {
        @Override
        public int dx() {
            return 1;
        }

        @Override
        public int dy() {
            return 0;
        }
    };

    /**
     * Returns the change in x-coordinate for this direction.
     *
     * @return -1 for LEFT, 1 for RIGHT, 0 for UP/DOWN
     */
    public abstract int dx();

    /**
     * Returns the change in y-coordinate for this direction.
     *
     * @return -1 for UP, 1 for DOWN, 0 for LEFT/RIGHT
     */
    public abstract int dy();

    /**
     * Checks if this direction is the exact opposite of another direction.
     * This is used to prevent the snake from reversing into itself.
     *
     * @param other the other direction to compare against
     * @return true if this direction is the opposite of other, false otherwise
     */
    public boolean isOpposite(Direction other) {
        if (other == null) {
            return false;
        }
        return (this == UP && other == DOWN) ||
               (this == DOWN && other == UP) ||
               (this == LEFT && other == RIGHT) ||
               (this == RIGHT && other == LEFT);
    }
}