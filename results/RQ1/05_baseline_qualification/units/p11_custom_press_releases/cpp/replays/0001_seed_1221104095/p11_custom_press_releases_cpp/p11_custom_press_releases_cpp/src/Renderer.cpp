#include "Renderer.h"

std::string Renderer::render(const std::string& templateTxt, 
                            const PressRelease& pr, 
                            const TemplateEngine& engine) const {
    auto fieldMap = pr.toFieldMap();
    auto result = engine.render(templateTxt, fieldMap);
    return result.output;
}