/*
 * poo_runtime.h - PooScript Runtime Library
 *
 * This header defines the runtime functions that compiled PooScript
 * programs link against.
 */

#ifndef POO_RUNTIME_H
#define POO_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

/* Built-in commands */
void poo_echo(const char* str);
void poo_cd(const char* path);
void poo_pwd(void);
void poo_exit(int code);

/* Process execution */
int poo_exec(const char* path, char** argv);
int poo_exec_path(const char* command, char** argv);

/* I/O operations */
int poo_cat(const char* filename);
int poo_ls(const char* path);

#endif /* POO_RUNTIME_H */
