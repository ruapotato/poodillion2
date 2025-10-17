/*
 * keyboard.h - PS/2 Keyboard Driver Header
 */

#ifndef KEYBOARD_H
#define KEYBOARD_H

/*
 * Initialize the keyboard driver
 */
void keyboard_init(void);

/*
 * Check if a key is available
 * Returns: 1 if key available, 0 otherwise
 */
int keyboard_available(void);

/*
 * Get a character from keyboard (blocking)
 * Returns: ASCII character, or 0 for non-printable keys
 */
char keyboard_getchar(void);

/*
 * Check if Shift is currently pressed
 */
int keyboard_shift_pressed(void);

/*
 * Check if Ctrl is currently pressed
 */
int keyboard_ctrl_pressed(void);

#endif /* KEYBOARD_H */
