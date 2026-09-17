#include <iostream>
#include <string>
#include "Clock.h"
#include "VersionHistory.h"
#include "TemplateEngine.h"
#include "Validator.h"
#include "PressRelease.h"
#include "Renderer.h"
#include "SearchIndex.h"

int main() {
    // Construct deterministic clock
    const std::string timestamp = "2024-01-02T10:00:00Z";
    FixedClock clock(timestamp);
    
    // Construct press release
    PressRelease pressRelease("PR-001");
    
    // Set headline
    pressRelease.setHeadline("Company Announces Q4 Results", clock, "set headline");
    
    // Set body
    pressRelease.setBody("The company reported strong financial performance for the fourth quarter...", 
                        clock, "set body");
    
    // Set contact
    Contact contact{"John Doe", "john.doe@company.com", "123-456-7890"};
    pressRelease.setContact(contact, clock, "set contact");
    
    // Add tag
    pressRelease.addTag("finance", clock, "add tag");
    
    // Construct validator
    Validator validator;
    
    // Submit for review
    bool submitted = pressRelease.submitForReview(validator, clock, "submit for review");
    std::cout << "Submitted for review: " << (submitted ? "true" : "false") << std::endl;
    
    // Publish
    bool published = pressRelease.publish(validator, clock, "publish");
    std::cout << "Published: " << (published ? "true" : "false") << std::endl;
    
    // Construct template engine
    TemplateEngine engine;
    
    // Construct renderer
    Renderer renderer;
    
    // Render template
    std::string templateTxt = R"(Press Release ID: {{id}}
Headline: {{headline}}
Body: {{body}}
Contact: {{contact.name}} ({{contact.email}}, {{contact.phone}})
Tags: {{tags}})";
    
    std::string renderedOutput = renderer.render(templateTxt, pressRelease, engine);
    std::cout << "\nRendered Output:\n" << renderedOutput << std::endl;
    
    // Construct search index
    SearchIndex index;
    
    // Add release record
    ReleaseRecord record;
    record.id = pressRelease.id();
    record.headline = pressRelease.headline();
    record.body = pressRelease.body();
    record.tags = pressRelease.tags();
    index.add(record);
    
    // Perform search
    std::set<std::string> requiredTags = {"finance"};
    auto searchResults = index.search("company", requiredTags);
    
    std::cout << "\nSearch Results (" << searchResults.size() << " found):\n";
    for (const auto& result : searchResults) {
        std::cout << "- ID: " << result.id << ", Headline: " << result.headline << std::endl;
    }
    
    // Print version history
    std::cout << "\nVersion History:\n" << pressRelease.history().toString();
    
    return 0;
}