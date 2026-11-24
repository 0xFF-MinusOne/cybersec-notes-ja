---
description: レジスタを使って ASLR を回避する
---

# ret2reg

**ret2reg** は、ハードコードされたアドレスではなく、レジスタが持つアドレスへジャンプするだけの手法で、[Using RSP for Shellcode](../using-rsp.md) とよく似ています。たとえば、`ret` が実行されるときに、RAX が _常に_ バッファを指している場合があります。その場合は、`call rax` や `jmp rax` を使って、そこから実行を続けられます。

この手法で RAX が最もよく使われる理由は、_慣例として_ 関数の戻り値が RAX に格納されることにあります。たとえば、次の基本的なコードを見てみましょう。

```c
#include <stdio.h>

int test() {
    return 0xdeadbeef;
}

int main() {
    test();
    return 0;
}
```

これをコンパイルして関数を逆アセンブルすると、次のようになります。

```text
0x55ea94f68125      55             push rbp
0x55ea94f68126      4889e5         mov rbp, rsp
0x55ea94f68129      b8efbeadde     mov eax, 0xdeadbeef
0x55ea94f6812e      5d             pop rbp
0x55ea94f6812f      c3             ret
```

ご覧のとおり、値 `0xdeadbeef` が EAX に移されています。
