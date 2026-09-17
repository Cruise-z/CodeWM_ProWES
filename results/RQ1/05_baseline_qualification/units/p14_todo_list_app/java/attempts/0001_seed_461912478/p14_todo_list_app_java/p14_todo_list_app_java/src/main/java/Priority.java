public enum Priority {
    LOW,
    MEDIUM,
    HIGH;

    public int rank() {
        switch (this) {
            case LOW: return 0;
            case MEDIUM: return 1;
            case HIGH: return 2;
            default: throw new IllegalStateException("Unknown priority: " + this);
        }
    }
}