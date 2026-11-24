---
description: fastbin を統合する
---

# malloc\_consolidate()

[先ほど](bins/operations-of-the-fastbin.md)、unsorted bin に入ったチャンクは統合されるが、fastbin は統合されないと説明しました。これは_厳密には_正しくありません。fastbin は自動的には統合されないというだけで、統合させるには関数 [`malloc_consolidate()`](https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L4448) を呼び出す必要があります。この関数は複雑に見えますが、本質的には、隣接する fastbin のチャンクをすべて集めてより大きなチャンクに結合し、unsorted bin に置くだけです。

なぜこれが重要なのでしょうか。UAF(use after free)などがあるのは確かに_ありがたい_のですが、fastbin のチャンクに対する Read-After-Free で漏洩できるのはヒープのアドレスだけです。単方向リンクリストが使うのは、(ヒープ上の)別のチャンクを指すか NULL である `fd` ポインタだけだからです。libc のリークも得たいところです。

隣接する fastbin のチャンクを一度に十分な数だけ解放し、`malloc_consolidate()` の呼び出しを引き起こすと、それらが統合されて、unsorted bin に入るチャンクができます。unsorted bin は双方向リンクリストであり、それに応じて動作します。リスト内の唯一の要素であれば、`fd` と `bk` の両方が `malloc_state` 内の場所を指し、これは libc の中にあります。

つまり、私たちにとってより重要なのは、largebin の統合を_どうやって_引き起こせるかを知ることです。

特に重要な方法には次のものがあります。

* `scanf` に非常に長い数字(約 `0x400` 文字)を入力する
  * これが有効なのは、その処理を担当するコードが `scratch_buffer` を管理して `0x400` バイトを割り当てている一方で、データが大きすぎる場合は `malloc` を使うためです(データがヒープのチャンクよりさらに大きくなると `realloc` も使い、最後に `free` も使うので、これらの関数を呼び出させる手段にもなります。フックを発動させるのに最適です)。
* フォーマット文字列の脆弱性に `%10000c` のようなものを入力しても、チャンクが作られます

どちらも、**largebin の確保が** `malloc_consolidate` **を引き起こす**ために成立します。[`malloc.c`](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c)(2.35)でこの関数の呼び出し箇所を調べると、ほかのきっかけも見つかります。

{% hint style="info" %}
glibc のバージョンが前後すると、特定の関数の呼び出し箇所が増えたり減ったりしている可能性があります。使っているバージョンを必ず確認してください。別の方法が見つかるかもしれません。
{% endhint %}

{% tabs %}
{% tab title="_int_malloc" %}
最も一般的で重要なきっかけです。**largebin サイズ**のチャンクを要求する `malloc()` の呼び出しは、[`malloc_consolidate()` の呼び出しを引き起こします](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L3965)。

```c
/*
   If this is a large request, consolidate fastbins before continuing [...]
 */

else
  {
    idx = largebin_index (nb);
    if (atomic_load_relaxed (&av->have_fastchunks))
      malloc_consolidate (av);
  }
```

[`use_top`](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L4353) の節にも、この関数の呼び出しがもう 1 つあります。この節は、要求に応えるために top chunk を使う必要があるときに実行されます。[最初の `if` 条件](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L4375)は、top chunk が要求に応えられるだけの大きさかどうかを確認します。

```c
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

そうでなければ、[次の条件](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L4392)で、arenaに fastchunk があるかどうかを確認します。あれば、要求に応えるための領域を取り戻そうとして `malloc_consolidate` を呼び出します。

```c
else if (atomic_load_relaxed (&av->have_fastchunks))
{
    malloc_consolidate (av);
    /* restore original bin index */
    if (in_smallbin_range (nb))
        idx = smallbin_index (nb);
    else
        idx = largebin_index (nb);
}
```

つまり、ヒープを埋めてからさらにチャンクを要求すれば、`malloc_consolidate()` の呼び出しを引き起こせます。

(両方の条件が失敗した場合、`_int_malloc` は基本的に `mmap` を使って要求に応える形にフォールバックします)。
{% endtab %}

{% tab title="_int_free" %}
TODO
{% endtab %}

{% tab title="malloc_trim" %}
[`mtrim`](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L5038) を呼び出すと fastbin が統合されます(`malloc_trim` という名前を考えれば納得できます)。役に立つ場面はまずなさそうですが、使い道を見つけたらぜひ教えてください。
{% endtab %}

{% tab title="mallopt" %}
`mallopt` で malloc のオプションを変更するとき、[まず fastbin が統合されます](https://elixir.bootlin.com/glibc/glibc-2.35/source/malloc/malloc.c#L5450)。`mallopt` は、呼ばれるとしてもプログラムが何かを始める前の初期化部分で 1 回呼ばれる程度なので、ほとんど役に立ちません。
{% endtab %}
{% endtabs %}
