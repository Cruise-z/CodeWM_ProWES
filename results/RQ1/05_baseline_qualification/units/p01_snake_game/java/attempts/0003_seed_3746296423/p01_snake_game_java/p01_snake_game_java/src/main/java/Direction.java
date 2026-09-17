/**
 * Enum representing the four cardinal directions.
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
     * Returns the change in x coordinate for this direction.
     *
     * @return -1, 0, or 1 depending on the direction
     */
    public abstract int dx();

    /**
     * Returns the change in y coordinate for this direction.
     *
     * @return -1, 0, or 1 depending on the direction
     */
    public abstract int dy();

    /**
     * Checks if this direction is the opposite of another direction.
     * 
     * @param other the other direction to check against
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