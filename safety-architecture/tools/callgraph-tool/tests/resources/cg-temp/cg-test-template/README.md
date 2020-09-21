# Template source code for testing Callgraph tool capabilities

## Detecting various call variants (including structs)

Use cases:

1. Static struct defined in a particular translation unit:
-available only in that translation unit (used directly or passed as function paramater)

2. global struct available in multiple translation units

3. Local struct defined inside of a function
- used in that function
- passed through another function to other parts of the code

4. Struct defined trough usage of macros

5. Detection of the typedefs usage

6. Alias macros

7. Struct that use cache alignment (for members, and globally for the whole struct)

8. Struct with bitfield members

9. Forward declared structs used in other (see "mm/shmem.c:address_space_operations")

10. Structs returned from function

11. local functions in different files with the same name

12. recursive calls (and cyclic calls)

13. Two local structs of the same name
