import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;
import java.util.HashMap;

public class MainTest {

    @Test
    public void testMainRuntime() {
        // Test that Main.main runs without throwing exceptions
        Main.main(new String[0]);
    }

    @Test
    public void testTemplateAndValidator() {
        // Test template substitution
        Template template = new Template("basic", "{{headline}}|{{body}}|{{contact}}");
        Map<String, String> fields = new HashMap<>();
        fields.put("headline", "Hello");
        fields.put("body", "Body");
        fields.put("contact", "a@b.com");
        
        String result = template.applyCustomFields(fields);
        assertEquals("Hello|Body|a@b.com", result);
        
        // Test Validator acceptance
        assertTrue(Validator.validateHeadline("Hello"));
        assertTrue(Validator.validateBody("Body"));
        assertTrue(Validator.validateContact("a@b.com"));
        
        // Test Validator rejection
        assertFalse(Validator.validateHeadline(""));
        assertFalse(Validator.validateHeadline(null));
        assertFalse(Validator.validateContact("invalid"));
        assertFalse(Validator.validateContact("@"));
        assertFalse(Validator.validateContact("a@"));
        assertFalse(Validator.validateContact("@b.com"));
    }

    @Test
    public void testLifecycleTagVersionSearch() {
        // Create a press release with the specified values
        Template template = new Template("basic", "{{headline}}|{{body}}|{{contact}}");
        PressRelease release = new PressRelease(
            "r1",
            "Hello",
            "Body",
            "a@b.com",
            template,
            Collections.emptyMap()
        );

        // Assert initial state is DRAFT
        assertEquals(ReleaseState.DRAFT, release.getState());

        // Submit for review
        release.submitForReview();
        assertEquals(ReleaseState.REVIEW, release.getState());

        // Add tag "media"
        release.addTag("media");

        // Publish
        release.publish();
        assertEquals(ReleaseState.PUBLISHED, release.getState());

        // Render exact text
        String rendered = release.renderPlainText();
        assertEquals("Hello|Body|a@b.com", rendered);

        // Assert version history size is 1 with Version number 1 and same text
        assertEquals(1, release.getVersionHistory().size());
        Version version = release.getVersionHistory().get(0);
        assertEquals(1, version.getNumber());
        assertEquals(rendered, version.getRenderedText());

        // Assert TaggingSystem.searchByTag returns only that release
        assertEquals(
            Arrays.asList(release),
            TaggingSystem.searchByTag(Arrays.asList(release), "media")
        );
    }
}