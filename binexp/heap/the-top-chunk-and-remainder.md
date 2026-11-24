---
description: ヒープ領域を増やす
---

# top chunk と remainder

**wilderness** とも呼ばれる **top chunk** は、ヒープの最後のチャンクです。top chunk のサイズは、ヒープの空き領域のサイズと等しくなります。

\[TODO ここに画像]

新しいチャンクを確保するときに、適切な解放済みチャンクがなければ、top chunk は縮小され、新しいヒープ領域のために後ろへ押しやられます。top の使用は[ここ](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L3983)で始まり、実際のロジックは[ここ](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L4069)にあります。

```c
victim = av->top;
size = chunksize (victim);

if ((unsigned long) (size) >= (unsigned long) (nb + MINSIZE))
  {
    remainder_size = size - nb;
    remainder = chunk_at_offset (victim, nb);
    av->top = remainder;
    set_head (victim, nb | PREV_INUSE |
              (av != &main_arena ? NON_MAIN_ARENA : 0));
    set_head (remainder, remainder_size | PREV_INUSE);

    check_malloced_chunk (av, victim, nb);
    void *p = chunk2mem (victim);
    alloc_perturb (p, bytes);
    return p;
  }
```

要求されたチャンクの `size` が top chunk のサイズ以下であれば、top chunk は 2 つのチャンクに分割されます。返されるチャンク(以前 top chunk があった場所に位置します)と、サイズが小さくなった新しい top chunk である **remainder** チャンクです。

要求サイズが top chunk の処理できる大きさを超えている場合、glibc は fastbin の統合を試みます。fastbin がない(または統合してもまだ領域が足りない)場合は、[デフォルトで `sysmalloc`](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L4120) に進み、(対応しているシステムでは)[`mmap`](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L2312) を呼び出します。
