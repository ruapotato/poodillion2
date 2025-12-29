# Symbolic Link Implementation for BrainFS

This document describes the symbolic link implementation added to BrainhairOS's BrainFS filesystem.

## Overview

Symbolic links (symlinks) are special files that contain a path to another file or directory. They allow for flexible file system organization and enable features like directory shortcuts, alternative paths, and compatibility layers.

## Implementation Details

### 1. Inode Type

Added a new inode type for symbolic links:
- **Type constant**: `BRFS_S_IFLNK = 40960` (0xA000)
- **Directory entry type**: 3
- **Permissions**: 0777 (lrwxrwxrwx)

Location: `/home/david/poodillion2/kernel/kernel_main.bh` line 1160

### 2. Core Functions

#### `brfs_symlink(mount_id, dir_ino, link_name, target_path)`
Creates a symbolic link in the filesystem.
- Allocates a new inode with type `BRFS_S_IFLNK`
- Stores the target path in the first data block
- Adds a directory entry with type 3 (symlink)
- Location: lines 1990-2053

#### `brfs_readlink(mount_id, ino, buf, bufsize)`
Reads the target path from a symbolic link.
- Verifies the inode is a symlink
- Reads target from first data block
- Returns number of bytes read
- Location: lines 2055-2087

#### `brfs_resolve_path(mount_id, dir_ino, path, max_depth)`
Resolves a path following symlinks with loop detection.
- Maximum depth: 8 symlinks (prevents infinite loops)
- Recursively follows symlinks to final target
- Returns final inode number or -1 on error
- Location: lines 2089-2116

### 3. Syscalls

Two new syscalls were added:

#### SYS_SYMLINK (88)
- **Prototype**: `int symlink(const char *target, const char *linkpath)`
- **Returns**: 0 on success, -1 on error
- **Handler**: `sys_symlink()` at line 11397

#### SYS_READLINK (89)
- **Prototype**: `int readlink(const char *path, char *buf, size_t bufsize)`
- **Returns**: Number of bytes read, or -1 on error
- **Handler**: `sys_readlink()` at line 11402

Assembly handlers: `/home/david/poodillion2/kernel/isr.asm` lines 979-1003

### 4. Shell Commands

#### `dsymlink <link> <target>`
Creates a symbolic link on the active BrainFS mount.
```
dsymlink mylink targetfile
```
Location: lines 6387-6417

#### `dreadlink <link>`
Reads and displays the target of a symbolic link.
```
dreadlink mylink
```
Location: lines 6418-6447

#### Enhanced `dls` command
The directory listing command now displays symlinks in magenta with `->` notation:
```
mylink -> targetfile
```
Location: lines 6294-6306

### 5. Features

- **Loop Detection**: Maximum symlink depth of 8 prevents infinite loops
- **Path Storage**: Target paths up to 1023 bytes stored in first data block
- **Visual Feedback**: Symlinks displayed in magenta with target path
- **Error Handling**: Broken symlinks shown as "(broken)"
- **Integration**: Works with existing BrainFS operations

## Usage Examples

### Creating a Symlink
```
dsymlink mylink README
```
Creates a symlink named "mylink" pointing to "README"

### Reading a Symlink
```
dreadlink mylink
```
Outputs: `README`

### Listing Directory
```
dls
```
Output:
```
home/
tmp/
mylink -> README
```

## Technical Notes

### Inode Structure
- Bytes 0-1: Mode (BRFS_S_IFLNK | 0777)
- Bytes 2-3: Link count (always 1)
- Bytes 4-7: Size (target path length)
- Bytes 16-19: First data block (contains target path)

### Directory Entry
- Bytes 0-3: Inode number
- Bytes 4-5: Entry length (32)
- Byte 6: Name length
- Byte 7: Type (3 for symlink)
- Bytes 8-31: Name (null-padded)

### Limitations
- Target path limited to 1023 bytes (fits in one 1KB block)
- Only supports single-level symlinks (no multi-component path resolution yet)
- All symlinks relative to root directory
- Maximum chain depth: 8 symlinks

## Future Enhancements

1. **Multi-component paths**: Support for `/path/to/file` style targets
2. **Absolute vs relative**: Distinguish between absolute and relative symlinks
3. **Symlink following in other operations**: Automatically follow symlinks in dcat, etc.
4. **Hard links**: Add support for hard links (multiple directory entries to same inode)
5. **Dangling link detection**: Improved handling of broken symlinks

## Testing

To test the symlink implementation:

1. Build and run BrainhairOS:
   ```bash
   make grub-brainhair
   make run-grub-brainhair
   ```

2. Create a test file:
   ```
   dtouch testfile
   dwrite testfile "Hello from symlink!"
   ```

3. Create a symlink:
   ```
   dsymlink link1 testfile
   ```

4. List directory:
   ```
   dls
   ```
   Should show: `link1 -> testfile`

5. Read symlink target:
   ```
   dreadlink link1
   ```
   Should output: `testfile`

## Files Modified

1. `/home/david/poodillion2/kernel/kernel_main.bh`
   - Added BRFS_S_IFLNK constant (line 1160)
   - Added brfs_symlink() function (lines 1990-2053)
   - Added brfs_readlink() function (lines 2055-2087)
   - Added brfs_resolve_path() function (lines 2089-2116)
   - Added sys_symlink() syscall handler (lines 11397-11400)
   - Added sys_readlink() syscall handler (lines 11402-11408)
   - Added dsymlink shell command (lines 6387-6417)
   - Added dreadlink shell command (lines 6418-6447)
   - Enhanced dls to show symlinks (lines 6294-6306)

2. `/home/david/poodillion2/kernel/isr.asm`
   - Added syscall dispatch for SYS_SYMLINK (88) and SYS_READLINK (89)
   - Added .syscall_symlink handler (lines 979-989)
   - Added .syscall_readlink handler (lines 991-1003)

3. `/home/david/poodillion2/docs/PRODUCTION_ROADMAP.md`
   - Marked symbolic links as complete (line 194)
   - Added implementation notes (lines 203-207)
