# Eval report: cmp305

Book index: 2166 chunks, embedder `minilm` (search ran with `minilm`), built 2026-10-11, SHA-256 d3510f9b88bb..., PDF pages 20-369 (offset 19).
Eval set: 50 positive claims (paraphrased; expected printed pages from the verification records), 20 negatives (8 of them CMP 220 topics the book does not cover).
Search: score = 0.5 x normalized BM25 + 0.5 x dense cosine.

| MIN_SCORE | top-3 hit rate | false-accept rate | meets bar (hit >= 80%, FA <= 10%) |
|---|---|---|---|
| 0.40 | 96% (48/50) | 25% (5/20) | no |
| 0.45 | 96% (48/50) | 20% (4/20) | no |
| 0.50 | 96% (48/50) | 20% (4/20) | no |
| 0.55 | 96% (48/50) | 15% (3/20) | no |
| 0.60 | 82% (41/50) | 10% (2/20) | yes |
| 0.65 | 70% (35/50) | 0% (0/20) | no |
| 0.70 | 50% (25/50) | 0% (0/20) | no |
| 0.75 | 46% (23/50) | 0% (0/20) | no |

**Chosen MIN_SCORE = 0.60** (highest hit rate with false-accept <= 10%): hit 82%, false-accept 10%.

## Caveats

- The same eval set is used to pick MIN_SCORE and to report the rates (no held-out split); with 50 + 12 claims one claim moves the hit rate by 2 points and the false-accept rate by 8.

## Per-claim results at MIN_SCORE = 0.60

| # | type | claim | expected | top-3 pages (score) | result |
|---|---|---|---|---|---|
| 1 | prose | Every recursive function needs a base case that is solved without making another recursive... | [8, 9] | 9 (0.88), 11 (0.77), 8 (0.70) | hit |
| 2 | prose | A memory leak happens when dynamically allocated memory is never freed with delete | [22, 33] | 36 (0.71) | MISS |
| 3 | prose | An lvalue reference can only bind to a named object, while an rvalue reference binds to a ... | [23, 24] | 24 (0.74), 23 (0.74) | hit |
| 4 | prose | Passing a large object by constant reference avoids making a copy while preventing the fun... | [26, 27] | 27 (0.67), 25 (0.63) | hit |
| 5 | prose | If a class owns memory through a raw pointer, the defaults are wrong and it needs its own ... | [30, 32, 33, 35] | - | MISS |
| 6 | prose | A function object is a class that overloads operator() so its instances can be called like... | [41, 42] | 12 (0.82), 27 (0.71), 41 (0.66) | hit |
| 7 | prose | Big-O gives an upper bound on growth: T(N) is O(f(N)) if T(N) <= c f(N) for all N past som... | [51, 52] | 52 (0.61) | hit |
| 8 | prose | The cubic maximum subsequence sum algorithm tries every pair of endpoints and sums the ele... | [60, 61] | 61 (0.69), 60 (0.60) | hit |
| 9 | prose | Kadane-style scanning solves the maximum contiguous subsequence sum problem in linear time | [56, 62, 65, 66] | 66 (0.62), 55 (0.61) | hit |
| 10 | prose | The divide-and-conquer maximum subsequence sum algorithm runs in O(N log N) time | [62, 63, 64] | 63 (0.79), 345 (0.73), 73 (0.73) | hit |
| 11 | prose | Binary search on a sorted array takes O(log N) time because each step halves the search ra... | [67, 68] | - | MISS |
| 12 | prose | Euclid's algorithm for the greatest common divisor runs in a logarithmic number of iterati... | [68, 69] | 68 (0.86) | hit |
| 13 | prose | Removing every other element of a std::vector by calling erase is quadratic, while doing i... | [83, 84] | 83 (0.64), 101 (0.60) | hit |
| 14 | prose | A doubly linked list with header and tail sentinel nodes avoids special cases when inserti... | [80, 92] | 92 (0.69), 80 (0.61), 93 (0.61) | hit |
| 15 | prose | Stack push and pop operations take constant time | [103, 104] | 104 (0.81), 108 (0.78), 103 (0.78) | hit |
| 16 | prose | A postfix expression is evaluated left to right using a stack in linear time | [105, 106, 107] | 108 (0.84), 107 (0.81), 119 (0.79) | hit |
| 17 | prose | A queue implemented with a circular array supports enqueue and dequeue in O(1) | [112, 113] | 113 (0.87) | hit |
| 18 | prose | The depth of a node is the length of the path from the root to it; the root has depth 0 | [122] | 122 (0.84), 142 (0.72), 263 (0.73) | hit |
| 19 | prose | In a binary search tree, all keys in the left subtree are smaller than the node and all ke... | [126, 132] | 132 (0.84), 176 (0.72), 142 (0.70) | hit |
| 20 | prose | Inserting already sorted keys into an unbalanced binary search tree makes it degenerate in... | [144, 168] | - | MISS |
| 21 | prose | An AVL tree requires that the heights of the left and right subtrees of every node differ ... | [144, 145] | 145 (0.93), 146 (0.88), 182 (0.77) | hit |
| 22 | prose | Splay trees guarantee O(log N) amortized time per operation even though one operation can ... | [158, 163] | 158 (0.90) | hit |
| 23 | prose | Inorder traversal of a binary search tree visits the keys in sorted order in linear time | [129, 166] | 166 (0.61) | hit |
| 24 | prose | In a B-tree of order M, every non-leaf node other than the root has between M/2 and M chil... | [169, 170] | 173 (0.73), 170 (0.74), 122 (0.72) | hit |
| 25 | prose | Hash tables support insertion, deletion and lookup in constant average time but cannot eff... | [193, 236] | 193 (0.80) | hit |
| 26 | prose | With separate chaining, every bucket holds a linked list of the keys whose hash value land... | [196, 197] | - | MISS |
| 27 | prose | Linear probing suffers from primary clustering, where occupied cells form long contiguous ... | [201, 202] | 201 (0.66) | hit |
| 28 | prose | With quadratic probing, if the table size is prime and the table is at least half empty, a... | [204, 205] | 204 (0.83), 203 (0.83) | hit |
| 29 | prose | Rehashing builds a table about twice as large and reinserts every element, which costs O(N... | [209, 210] | 209 (0.64), 208 (0.61), 238 (0.60) | hit |
| 30 | prose | Cuckoo hashing uses two hash functions and two tables, so a lookup checks at most two loca... | [215, 216, 217] | 227 (0.79), 215 (0.80), 219 (0.79) | hit |
| 31 | prose | Universal hashing picks the hash function at random from a family so no fixed input is bad... | [230, 231] | 231 (0.66), 230 (0.65) | hit |
| 32 | prose | A binary heap is a complete binary tree stored in an array where the children of position ... | [247, 248] | 283 (0.71), 247 (0.68) | hit |
| 33 | prose | Inserting into a binary heap percolates the new element up and takes O(log N) in the worst... | [249, 251] | 251 (0.78), 249 (0.74), 255 (0.73) | hit |
| 34 | prose | deleteMin on a binary heap removes the root and percolates the hole down, taking logarithm... | [251, 252] | 251 (0.70) | hit |
| 35 | prose | The buildHeap operation turns an unordered array into a heap in linear time | [255, 257] | 255 (0.69), 258 (0.62) | hit |
| 36 | prose | Leftist heaps support merging two heaps in O(log N) time | [261, 266] | 271 (0.86), 269 (0.86), 261 (0.85) | hit |
| 37 | prose | A binomial queue keeps a collection of binomial trees, and merging, inserting and deleteMi... | [271, 273] | 273 (0.80), 271 (0.79), 287 (0.78) | hit |
| 38 | prose | Insertion sort runs in linear time on input that is already sorted | [294, 295] | 295 (0.82), 341 (0.74), 54 (0.71) | hit |
| 39 | prose | Insertion sort takes quadratic time on average | [294, 295] | 295 (0.86), 144 (0.73), 298 (0.69) | hit |
| 40 | prose | Shellsort with Hibbard's increments has a worst-case running time of Theta(N^(3/2)) | [298, 299] | 298 (0.86), 342 (0.78), 299 (0.79) | hit |
| 41 | prose | Mergesort runs in O(N log N) time but needs a temporary array linear in the input size | [304, 309] | 309 (0.82), 305 (0.80), 306 (0.76) | hit |
| 42 | prose | Quicksort averages O(N log N) but degrades to quadratic time in the worst case | [309, 319, 321] | 323 (0.66), 309 (0.62), 343 (0.61) | hit |
| 43 | prose | Median-of-three pivot selection protects quicksort against sorted and reverse-sorted input | [312, 313] | 343 (0.70) | MISS |
| 44 | prose | A decision tree argument shows that sorting by comparisons alone cannot beat Omega(N log N... | [323, 325] | 323 (0.65), 325 (0.63) | hit |
| 45 | prose | Bucket sort with M buckets sorts N integers in O(M + N) time | [331] | 332 (0.83), 333 (0.83), 331 (0.80) | hit |
| 46 | prose | The adjacent-exchange lower bound argument applies to selection sort, so it needs a quadra... | [295, 296] | 296 (0.76), 295 (0.63) | hit |
| 47 | prose | Dropping N balls at random into N^2 bins gives under a 50% chance that every bin ends up h... | [213] | - | MISS |
| 48 | code | int n = v.size();
for (int k = n / 2 - 1; k >= 0; k--)
    percDown(v, k, n);   // heapify... | [302] | 302 (0.76) | hit |
| 49 | code | int best = 0;
for (int lo = 0; lo < n; lo++)
    for (int hi = lo; hi < n; hi++) {
       ... | [61] | - | MISS |
| 50 | code | int left = 0, right = n - 1;
while (left <= right) {
    int middle = left + (right - left... | [67] | 64 (0.64) | MISS |
| 51 | prose | The capital of France is Paris | - | - | ok (empty) |
| 52 | prose | The derivative of sin x is cos x | - | - | ok (empty) |
| 53 | prose | Integration by parts states that the integral of u dv equals uv minus the integral of v du | - | - | ok (empty) |
| 54 | prose | The limit of sin(x)/x as x approaches 0 equals 1 | - | - | ok (empty) |
| 55 | prose | Photosynthesis converts light energy into chemical energy stored in glucose | - | - | ok (empty) |
| 56 | prose | A half adder produces a sum bit and a carry bit from two input bits | - | - | ok (empty) |
| 57 | prose | Karnaugh maps simplify Boolean expressions by grouping adjacent ones | - | - | ok (empty) |
| 58 | prose | World War II ended in 1945 | - | - | ok (empty) |
| 59 | prose | The mitochondria is the powerhouse of the cell | - | - | ok (empty) |
| 60 | prose | Newton's second law states that force equals mass times acceleration | - | - | ok (empty) |
| 61 | prose | The chain rule says the derivative of f(g(x)) is f'(g(x)) times g'(x) | - | 53 (0.63) | FALSE ACCEPT |
| 62 | prose | A flip-flop stores one bit and changes state on a clock edge | - | - | ok (empty) |
| 63 | prose | After opening a file with an ifstream, call fail() to find out whether the file could actu... | - | - | ok (empty) |
| 64 | prose | setw from <iomanip> only affects the next item printed, while setprecision stays in effect... | - | - | ok (empty) |
| 65 | prose | In a switch statement, a case without a break falls through and also runs the statements o... | - | - | ok (empty) |
| 66 | prose | getline(cin, s) reads a whole line including the spaces, whereas cin >> s stops at the fir... | - | - | ok (empty) |
| 67 | prose | strncpy does not add the terminating null character when the source string is at least as ... | - | - | ok (empty) |
| 68 | prose | A derived class constructor should call the base class constructor in its initialization s... | - | 12 (0.61) | FALSE ACCEPT |
| 69 | prose | A do-while loop always executes its body at least once because the condition is tested at ... | - | - | ok (empty) |
| 70 | prose | Calling srand(time(0)) once at the start of main seeds rand() so each run produces a diffe... | - | - | ok (empty) |
