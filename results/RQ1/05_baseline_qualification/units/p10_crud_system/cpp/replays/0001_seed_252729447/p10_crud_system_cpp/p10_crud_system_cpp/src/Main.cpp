#include "CrudService.h"
#include <iostream>

int main() {
  Repository repo;
  ManualClock clock(100);
  CrudService service(repo, clock);
  
  Record created = service.create("1", "Alice", "alice@example.com");
  std::cout << "Created record with ID: " << created.id 
            << ", Name: " << created.name 
            << ", Email: " << created.email 
            << ", Revision: " << created.revision 
            << ", Updated At: " << created.updated_at << std::endl;
  
  return 0;
}