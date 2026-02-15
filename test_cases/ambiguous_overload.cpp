#include <iostream>
using namespace std;

void foo(long x) {}
void foo(double x) {}

int main() {
    foo(10);
    return 0;
}
