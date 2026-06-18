#include <stdio.h>

int main() {
    int a = 10;
    int b = 20;
    float ratio = 0.5;
    int sum = a + b;

    if (sum >= 30 && ratio < 1.0) {
        printf("Sum is %d\n", sum);
    }

    for (int i = 0; i < 5; i++) {
        sum += i;
    }

    return 0;
}
