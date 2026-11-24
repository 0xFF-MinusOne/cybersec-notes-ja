---
description: A minor issue
---

# Stack Alignment

64-bit システムで pwn していると、エクスプロイトがローカルでは完璧に動くのに、リモートでは失敗することがあります。ローカルの LIBC ではなく、提供された LIBC を使おうとしたときに失敗する場合もあります。これは**スタックアライメント(stack alignment)**と呼ばれるものが原因です。

基本的に、[x86-64 ABI(application binary interface)は、`call` 命令の時点で 16 バイトアライメントを保証します](https://stackoverflow.com/questions/54393105/libcs-system-when-the-stack-pointer-is-not-16-padded-causes-segmentation-faul)。LIBC はこれを前提にして、実行を最適化するために [SSE のデータ転送命令](https://docs.oracle.com/cd/E26502\_01/html/E28388/eojde.html)を使います。特に `system` は `movaps` などの命令を使います。

つまり、スタックが 16 バイトにアライメントされていない(RSP が 16 の倍数でない)と、ROP チェーンは `system` で失敗します。

修正は簡単で、ROP チェーンの `system` を呼び出す前に、`ret` ガジェットを 1 つだけ置きます。

```python
ret = elf.address + 0x2439

[...]
rop.raw(POP_RDI)
rop.raw(0x4)        # first parameter
rop.raw(ret)        # align the stack
rop.raw(system)
```

これは、RSP が余分に 1 回 pop されて 8 バイト進み、アライメントが揃うためにうまくいきます。
