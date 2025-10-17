/*
 * poo_runtime.c - PooScript Runtime Library Implementation
 */

#include "poo_runtime.h"

void poo_echo(const char* str) {
    printf("%s\n", str);
}

void poo_cd(const char* path) {
    if (chdir(path) != 0) {
        perror("cd");
    }
}

void poo_pwd(void) {
    char cwd[4096];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        printf("%s\n", cwd);
    } else {
        perror("pwd");
    }
}

void poo_exit(int code) {
    exit(code);
}

int poo_exec(const char* path, char** argv) {
    pid_t pid = fork();
    if (pid == 0) {
        // Child process
        execv(path, argv);
        perror("exec");
        exit(1);
    } else if (pid > 0) {
        // Parent process
        int status;
        waitpid(pid, &status, 0);
        return WEXITSTATUS(status);
    } else {
        perror("fork");
        return -1;
    }
}

int poo_exec_path(const char* command, char** argv) {
    // Try common paths
    const char* paths[] = {
        "/bin/",
        "/usr/bin/",
        "/sbin/",
        "/usr/sbin/",
        NULL
    };

    for (int i = 0; paths[i]; i++) {
        char full_path[4096];
        snprintf(full_path, sizeof(full_path), "%s%s", paths[i], command);

        if (access(full_path, X_OK) == 0) {
            return poo_exec(full_path, argv);
        }
    }

    fprintf(stderr, "%s: command not found\n", command);
    return 127;
}

int poo_cat(const char* filename) {
    FILE* f = fopen(filename, "r");
    if (!f) {
        perror(filename);
        return 1;
    }

    char buf[4096];
    while (fgets(buf, sizeof(buf), f)) {
        printf("%s", buf);
    }

    fclose(f);
    return 0;
}

int poo_ls(const char* path) {
    // Simple ls implementation
    // In real OS, this would call into VFS
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "/bin/ls %s", path);
    return system(cmd);
}
