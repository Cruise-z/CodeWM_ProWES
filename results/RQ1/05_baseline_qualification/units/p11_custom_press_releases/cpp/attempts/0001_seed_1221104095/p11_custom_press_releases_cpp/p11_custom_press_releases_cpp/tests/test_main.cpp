#include <cassert>
#include <string>
#include <vector>
#include <set>
#include "Clock.h"
#include "VersionHistory.h"
#include "TemplateEngine.h"
#include "Validator.h"
#include "PressRelease.h"
#include "Renderer.h"
#include "SearchIndex.h"

int main() {
    // Test 1: Runtime wiring - construct objects and perform basic operations
    {
        const std::string timestamp = "2024-01-02T10:00:00Z";
        FixedClock clock(timestamp);
        PressRelease pressRelease("TEST-001");
        
        // Test basic field setting
        pressRelease.setHeadline("Test Headline", clock, "set headline");
        pressRelease.setBody("Test Body Content", clock, "set body");
        
        Contact contact{"Jane Smith", "jane.smith@example.com", "555-1234"};
        pressRelease.setContact(contact, clock, "set contact");
        
        pressRelease.addTag("test", clock, "add tag");
        
        // Test lifecycle transitions
        Validator validator;
        bool submitted = pressRelease.submitForReview(validator, clock, "submit for review");
        assert(submitted == true);
        
        bool published = pressRelease.publish(validator, clock, "publish");
        assert(published == true);
        
        // Test version history
        assert(pressRelease.history().size() == 5); // 4 field changes + 1 state change
    }
    
    // Test 2: Template substitution and missing key detection
    {
        TemplateEngine engine;
        std::map<std::string, std::string> fields = {
            {"headline", "Breaking News"},
            {"contact.email", "news@example.com"}
        };
        
        // Test valid substitution
        std::string validTemplate = "Headline: {{headline}}, Email: {{contact.email}}";
        auto result = engine.render(validTemplate, fields);
        assert(result.output == "Headline: Breaking News, Email: news@example.com");
        assert(result.missingKeys.empty());
        
        // Test missing key detection
        std::string templateWithMissing = "Title: {{title}}, Email: {{contact.email}}";
        result = engine.render(templateWithMissing, fields);
        assert(result.output == "Title: , Email: news@example.com");
        assert(result.missingKeys.size() == 1);
        assert(result.missingKeys[0] == "title");
    }
    
    // Test 3: Lifecycle gating - ensure publish blocked when validation fails
    {
        const std::string timestamp = "2024-01-02T10:00:00Z";
        FixedClock clock(timestamp);
        PressRelease pressRelease("TEST-002");
        
        // Set invalid contact (empty email)
        Contact invalidContact{"Invalid User", "", "123"};
        pressRelease.setContact(invalidContact, clock, "set invalid contact");
        pressRelease.setHeadline("Test Headline", clock, "set headline");
        pressRelease.setBody("Test Body", clock, "set body");
        
        Validator validator;
        bool submitted = pressRelease.submitForReview(validator, clock, "submit for review");
        assert(submitted == true); // Should succeed as it's just a transition
        
        // Try to publish - should fail due to invalid contact
        bool published = pressRelease.publish(validator, clock, "attempt publish");
        assert(published == false); // Should fail because contact is invalid
        assert(pressRelease.state() == LifecycleState::InReview); // State unchanged
    }
    
    // Test 4: Search behavior - case-insensitive contains and tag inclusion
    {
        SearchIndex index;
        
        // Add test records
        ReleaseRecord record1;
        record1.id = "PR-001";
        record1.headline = "Company Earnings Report";
        record1.body = "The company announced strong quarterly earnings.";
        record1.tags = {"finance", "earnings"};
        
        ReleaseRecord record2;
        record2.id = "PR-002";
        record2.headline = "New Product Launch";
        record2.body = "Introducing our latest innovation.";
        record2.tags = {"products", "launch"};
        
        index.add(record1);
        index.add(record2);
        
        // Test case-insensitive search
        std::set<std::string> requiredTags = {"finance"};
        auto results = index.search("earnings", requiredTags);
        assert(results.size() == 1);
        assert(results[0].id == "PR-001");
        
        // Test search with no matching tags
        requiredTags = {"nonexistent"};
        results = index.search("company", requiredTags);
        assert(results.empty());
        
        // Test search with multiple tags (should find nothing)
        requiredTags = {"finance", "products"};
        results = index.search("company", requiredTags);
        assert(results.empty());
    }
    
    return 0;
}