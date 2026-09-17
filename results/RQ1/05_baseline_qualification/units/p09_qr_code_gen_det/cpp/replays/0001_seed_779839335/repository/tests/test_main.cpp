#include <cassert>
#include <stdexcept>
#include <string>
#include "QRCodec.h"
#include "QRRenderer.h"

int main() {
  // Test 1: Round-trip encode/decode with detect true
  {
    std::string original_text = "hello-世界";
    QRMatrix matrix = QRCodec::encode(original_text);
    std::string decoded_text = QRCodec::decode(matrix);
    assert(decoded_text == original_text);
    assert(QRCodec::detect(matrix) == true);
  }

  // Test 2: Finder corruption handling
  {
    std::string original_text = "hello-世界";
    QRMatrix matrix = QRCodec::encode(original_text);
    QRMatrix corrupted = matrix;
    corrupted.set(0, 0, false);  // Corrupt the finder pattern
    assert(QRCodec::detect(corrupted) == false);
    try {
      QRCodec::decode(corrupted);
      assert(false);  // Should not reach here
    } catch (const std::runtime_error&) {
      // Expected exception
    }
  }

  // Test 3: Renderer newline count and length bound
  {
    QRMatrix matrix = QRCodec::encode("hello-世界");
    std::string rendered = QRRenderer::render(matrix);
    int newline_count = 0;
    for (char c : rendered) {
      if (c == '\n') {
        newline_count++;
      }
    }
    assert(newline_count == 20);
    
    try {
      QRCodec::encode(std::string(41, 'a'));
      assert(false);  // Should not reach here
    } catch (const std::invalid_argument&) {
      // Expected exception
    }
  }

  return 0;
}