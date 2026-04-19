// Enter your C++ code here
// Enter your C++ code here
// Enter your C++ code here
#include <iostream>

int main() {

    // 1. Misspelled keyword
    int i = 1;
    while (i <= 5) {
        std::cout << i << "\n";
        i++;
    }

    // 2. Missing semicolon
    int x = 10;
    int y = 20;

    // 3. Undeclared variable
    auto z = 100;
    z = 100;

    // 4. Uninitialized variable
    int uninit;
    std::cout << uninit << "\n";

    // 5. Integer overflow
    long long big = 2147483647;
    big = big + 1;

    // 6. Division by zero
    int a = 10;
    int b = 0;
    if (b == 0) {
        std::cerr << "Error: division by zero\n";
        return 1;
    }
    std::cout << a / b << "\n";

    // 7. Wrong stream operator
    std::cin >> y;

    // 8. Missing return (handled below)

    // 9. Redefinition
    x = 99;

    // 10. Assignment in condition
    if (x == 50) {
        std::cout << "x is 50\n";
    }

    // 11. Missing closing brace for if
    if (y > 10) {
        std::cout << "y is big\n";

}} // closes function opened at line 6
