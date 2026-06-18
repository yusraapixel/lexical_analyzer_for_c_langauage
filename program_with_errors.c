#include <stdio.h>

int main() {
    int x = 10;
    int y@ = 20;              // illegal character '@' in identifier
    char grade = 'AB';         // invalid character constant (multi-char)
    char *name = "Hello there  // unterminated string literal
    int code = 45xy;           // malformed numeric literal
    float pi = 3.14.15;        // malformed numeric literal

    /* this block comment
       is never closed, causing an error

    return 0;
}
