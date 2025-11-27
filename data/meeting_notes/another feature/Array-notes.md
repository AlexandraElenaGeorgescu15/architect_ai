# Array

## ELI5
A row of numbered boxes where you can instantly grab any item if you know its position number.

## Formal Definition
A contiguous memory structure providing O(1) random access via index. Insertion/deletion in middle requires shifting elements, making it O(n).

## Interview Answer
Arrays excel at random access with O(1) complexity and cache locality due to contiguous memory. Best for known-size collections needing frequent indexing. Avoid for frequent mid-insertions since they require O(n) shifts.

## Common Pitfalls
1. Out-of-bounds access causing exceptions
2. Fixed size in many languages limits flexibility
3. Costly O(n) mid insertions/deletions
4. Cache misses with large strides

## Code Examples

### C#
```csharp
int[] nums = {1, 2, 3, 4, 5};
int value = nums[2]; // O(1) access
Array.Resize(ref nums, 10); // O(n) copy
```

### TypeScript
```typescript
const nums: number[] = [1, 2, 3, 4, 5];
const value = nums[2]; // O(1) access
nums.splice(2, 0, 99); // O(n) insert
```

## Diagram
```
Array: [0][1][2][3][4]
       ↓  ↓  ↓  ↓  ↓
      [1][2][3][4][5]
Direct index: O(1)
```
