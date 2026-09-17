#include "QRCodec.h"
#include <iostream>
#include <string>

int main() {
  // Encode the literal "CodeWM"
  QRMatrix matrix = QRCodec::encode("CodeWM");
  
  // Decode the matrix back to a string
  std::string decoded = QRCodec::decode(matrix);
  
  // Print the decoded string (at most one concise line)
  std::cout << decoded << std::endl;
  
  return 0;
}