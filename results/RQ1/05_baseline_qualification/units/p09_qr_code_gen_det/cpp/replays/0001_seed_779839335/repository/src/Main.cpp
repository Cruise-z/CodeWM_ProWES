#include "QRCodec.h"
#include "QRRenderer.h"
#include <iostream>
#include <string>

int main() {
  // Encode the literal "CodeWM"
  QRMatrix matrix = QRCodec::encode("CodeWM");
  
  // Decode the matrix back to text
  std::string decoded = QRCodec::decode(matrix);
  
  // Render the matrix as ASCII
  std::string rendered = QRRenderer::render(matrix);
  
  // Print the decoded string (at most one concise line)
  std::cout << decoded << std::endl;
  
  return 0;
}