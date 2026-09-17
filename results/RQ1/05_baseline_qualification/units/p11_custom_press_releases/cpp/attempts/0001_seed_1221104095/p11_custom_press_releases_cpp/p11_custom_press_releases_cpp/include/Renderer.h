#ifndef RENDERER_H
#define RENDERER_H

#include <string>
#include "TemplateEngine.h"
#include "PressRelease.h"

/// @brief Renderer for generating plain-text output from press releases
class Renderer {
public:
    /// @brief Renders a press release using a template
    /// @param templateTxt Template string containing placeholders
    /// @param pr PressRelease instance to render
    /// @param engine TemplateEngine instance to use for substitution
    /// @return Formatted string output
    std::string render(const std::string& templateTxt, 
                       const PressRelease& pr, 
                       const TemplateEngine& engine) const;
};

#endif // RENDERER_H