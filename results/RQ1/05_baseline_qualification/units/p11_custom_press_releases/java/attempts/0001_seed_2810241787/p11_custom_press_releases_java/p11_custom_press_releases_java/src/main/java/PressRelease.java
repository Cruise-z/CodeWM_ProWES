/**
 * Represents a press release with associated metadata, content, and lifecycle management.
 * The press release follows a state machine: DRAFT -> REVIEW -> PUBLISHED.
 * It supports custom fields, tagging, version history, and rendering.
 */
public final class PressRelease {
    private final String id;
    private final String headline;
    private final String body;
    private final String contact;
    private final Template template;
    private final java.util.Map<String, String> customFields;
    private ReleaseState state;
    private final java.util.Set<String> tags;
    private final java.util.List<Version> versionHistory;

    /**
     * Constructs a new PressRelease with the specified parameters.
     *
     * @param id the unique identifier for this press release
     * @param headline the headline of the press release
     * @param body the body content of the press release
     * @param contact the contact information for the press release
     * @param template the template used for rendering this press release
     * @param customFields the custom fields to be used in template substitution
     */
    public PressRelease(String id, String headline, String body, String contact, Template template, java.util.Map<String, String> customFields) {
        this.id = id;
        this.headline = headline;
        this.body = body;
        this.contact = contact;
        this.template = template;
        // Create a defensive copy of the custom fields map to prevent external mutation
        this.customFields = customFields == null ? new java.util.LinkedHashMap<>() : new java.util.LinkedHashMap<>(customFields);
        this.state = ReleaseState.DRAFT;
        this.tags = new java.util.LinkedHashSet<>();
        this.versionHistory = new java.util.ArrayList<>();
    }

    /**
     * Returns the unique identifier of this press release.
     *
     * @return the ID
     */
    public String getId() {
        return id;
    }

    /**
     * Returns the headline of this press release.
     *
     * @return the headline
     */
    public String getHeadline() {
        return headline;
    }

    /**
     * Returns the body content of this press release.
     *
     * @return the body
     */
    public String getBody() {
        return body;
    }

    /**
     * Returns the contact information of this press release.
     *
     * @return the contact
     */
    public String getContact() {
        return contact;
    }

    /**
     * Returns the current state of this press release.
     *
     * @return the state
     */
    public ReleaseState getState() {
        return state;
    }

    /**
     * Validates the content of this press release.
     * The headline, body, and contact must be valid according to the Validator rules.
     *
     * @return true if the content is valid, false otherwise
     */
    public boolean validate() {
        return Validator.validateHeadline(headline) &&
               Validator.validateBody(body) &&
               Validator.validateContact(contact);
    }

    /**
     * Submits this press release for review.
     * The press release must be in DRAFT state and must pass validation.
     *
     * @throws IllegalStateException if the press release is not in DRAFT state or fails validation
     */
    public void submitForReview() {
        if (state != ReleaseState.DRAFT) {
            throw new IllegalStateException("Cannot submit for review: press release is not in DRAFT state");
        }
        if (!validate()) {
            throw new IllegalStateException("Cannot submit for review: press release content is invalid");
        }
        state = ReleaseState.REVIEW;
    }

    /**
     * Publishes this press release.
     * The press release must be in REVIEW state.
     * On first publication, a version is added to the version history.
     *
     * @throws IllegalStateException if the press release is not in REVIEW state
     */
    public void publish() {
        if (state != ReleaseState.REVIEW) {
            throw new IllegalStateException("Cannot publish: press release is not in REVIEW state");
        }
        // Add version history on first publication
        if (versionHistory.isEmpty()) {
            String renderedText = renderPlainText();
            versionHistory.add(new Version(1, renderedText));
        }
        state = ReleaseState.PUBLISHED;
    }

    /**
     * Adds a tag to this press release.
     * Tags are stored in insertion order and duplicates are avoided.
     * Null or blank tags are ignored.
     *
     * @param tag the tag to add
     */
    public void addTag(String tag) {
        if (tag != null && !tag.trim().isEmpty()) {
            tags.add(tag.trim());
        }
    }

    /**
     * Returns a defensive copy of the tags associated with this press release.
     * The tags are returned in insertion order.
     *
     * @return a list of tags
     */
    public java.util.List<String> getTags() {
        return new java.util.ArrayList<>(tags);
    }

    /**
     * Renders this press release as plain text using the assigned template and custom fields.
     * Combines the headline, body, contact, and custom fields into a single map for substitution.
     *
     * @return the rendered plain text
     */
    public String renderPlainText() {
        java.util.Map<String, String> fields = new java.util.LinkedHashMap<>();
        fields.put("headline", headline);
        fields.put("body", body);
        fields.put("contact", contact);
        fields.putAll(customFields);
        return template.applyCustomFields(fields);
    }

    /**
     * Returns a defensive copy of the version history of this press release.
     * The versions are returned in chronological order.
     *
     * @return a list of versions
     */
    public java.util.List<Version> getVersionHistory() {
        return new java.util.ArrayList<>(versionHistory);
    }
}