# Safe Linking

**glibc 2.32** 以降、単方向リンクリスト(fastbin と tcachebin)を保護するために、新しい **Safe-Linking** の仕組みが実装されました。考え方は、これらの bin にある解放済みチャンクの `fd` ポインタをマングリング(mangling)操作で**保護**し、任意の値で上書きしにくくするというものです。

すべての `fd` ポインタは [`PROTECT_PTR` マクロ](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L339)で保護され、[`REVEAL_PTR` マクロ](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L341)で元に戻されます。

```c
#define PROTECT_PTR(pos, ptr) \
  ((__typeof (ptr)) ((((size_t) pos) >> 12) ^ ((size_t) ptr)))
#define REVEAL_PTR(ptr)  PROTECT_PTR (&ptr, ptr)
```

ここで `pos` は現在のチャンクの位置、`ptr` は指している先のチャンクの位置です(bin の最後のチャンクなら NULL です)。ここでも、保護に ASLR を利用しています。`>>12` によって、ASLR の予測可能な下位 12 ビットを取り除き、ランダムな上位 52 ビットだけを残します(実質的には 28 ビットです。さらに上位のビットはかなり予測しやすいためです)。

<figure><img src="../../.gitbook/assets/image (2).png" alt=""><figcaption><p>画像の出典: <a href="https://research.checkpoint.com/2020/safe-linking-eliminating-a-20-year-old-malloc-exploit-primitive/">https://research.checkpoint.com/2020/safe-linking-eliminating-a-20-year-old-malloc-exploit-primitive/</a></p></figcaption></figure>

これは非常に初歩的な保護で、現在の位置と指している先の位置を使ってマングリングするだけです。プログラム上は、オーバーヘッドも性能への影響もほとんどありません。`PROTECT_PTR` は [`tcache_put()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L2941) と、`_int_free()` 内の 2 か所(fastbin 用)の[ここ](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L4299)と[ここ](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L4310)に実装されています。`REVEAL_PTR` が使われている箇所も見つかります。

では、攻撃者にとってこれは何を意味するのでしょうか。

ここでも、**ヒープリークが鍵です**。ヒープリークが得られれば、`PROTECT_PTR` の XOR の両方の要素が分かるので、簡単に再現して、自分でマングリングしたポインタを偽造できます。

***

部分上書き(partial overwrite)ならまだできると言いたくなるかもしれませんが、この Safe-Linking の仕組みには新しいセキュリティチェックである**アライメント**チェックが付随しています。このチェックは、チャンクが 16 ビットにアラインされていることを保証するもので、(Safe-Linking のすべてと同様に)単方向リンクリストにのみ関係します。[`malloc.c`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c) で `unaligned` を Ctrl-F で検索すると、さまざまな箇所が見つかります。攻撃者である私たちにとって特に重要なのは、おそらく `tcache_get()` 内のものと `_int_malloc()` 内のものです。

{% tabs %}
{% tab title="tcache_get" %}
tcache からチャンク `e` を**取り出す**ときに、アライメントが検査されます。

```c
if (__glibc_unlikely (!aligned_OK (e)))
  malloc_printerr ("malloc(): unaligned tcache chunk detected");
```
{% endtab %}

{% tab title="_int_malloc()" %}
ここには 3 つのチェックがあります。1 つ目は、fastbin からチャンクを取り除くマクロ [`REMOVE_FB`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L3587) です。

```c
if (__glibc_unlikely (pp != NULL && misaligned_chunk (pp)))       \
    malloc_printerr ("malloc(): unaligned fastbin chunk detected");
```

2 つ目は、[fastbin から最初に返されるチャンク](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L3609)です。

```c
if (__glibc_unlikely (misaligned_chunk (victim)))
    malloc_printerr ("malloc(): unaligned fastbin chunk detected 2");
```

3 つ目は、[対応する tcache bin への移動](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L3625)の際の、すべての fastbin チャンクに対するものです。

```c
if (__glibc_unlikely (misaligned_chunk (tc_victim)))
    malloc_printerr ("malloc(): unaligned fastbin chunk detected 3");
```
{% endtab %}

{% tab title="_int_free()" %}
`_int_free()` は、`tcache_entry` の [`key`](tcache-keys.md) がすでに本来設定されるはずの値になっていて、double free の検出のために一連の走査チェックを行う必要がある場合に、アライメントを検査します。

<pre class="language-c"><code class="lang-c">if (__glibc_unlikely (e->key == tcache))
{
    tcache_entry *tmp;
    LIBC_PROBE (memory_tcache_double_free, 2, e, tc_idx);
    for (tmp = tcache->entries[tc_idx]; tmp; tmp = REVEAL_PTR (tmp->next))
    {
<strong>        if (__glibc_unlikely (!aligned_OK (tmp)))
</strong>            malloc_printerr ("free(): unaligned chunk detected in tcache 2");
        if (tmp == e)
            malloc_printerr ("free(): double free detected in tcache 2");
        /* If we get here, it was a coincidence.  We've wasted a
        few cycles, but don't abort.  */
    }
}
</code></pre>
{% endtab %}

{% tab title="malloc_consolidate()" %}
すべての fastbin が [unsorted bin](bins/chunk-allocation-and-reallocation.md) に統合されるとき、[アライメントが検査されます](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L4508)。

```c
if (__glibc_unlikely (misaligned_chunk (p)))
    malloc_printerr ("malloc_consolidate(): "
		     "unaligned fastbin chunk detected");
```
{% endtab %}

{% tab title="Others" %}
攻撃者にとってあまり重要な関数ではありませんが、fastbin のチャンクは [`int_mallinfo()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L4940)、[`__malloc_info()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L5482)、[`do_check_malloc_state()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L2173)、[`tcache_thread_shutdown()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L2980) でもアライメントが検査されます。

```c
if (__glibc_unlikely (misaligned_chunk (p)))
    malloc_printerr ("<funcname>(): "
		     "unaligned fastbin chunk detected")
```

```c
if (__glibc_unlikely (!aligned_OK (e)))
    malloc_printerr ("tcache_thread_shutdown(): "
		     "unaligned tcache chunk detected");
```
{% endtab %}
{% endtabs %}

[`!aligned_OK`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L1200) を使っているものと、[`misaligned_chunk()`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc.c#L1202) を使っているものがあることに気づくかもしれません。

```c
#define aligned_OK(m)  (((unsigned long)(m) & MALLOC_ALIGN_MASK) == 0)

#define misaligned_chunk(p) \
  ((uintptr_t)(MALLOC_ALIGNMENT == 2 * SIZE_SZ ? (p) : chunk2mem (p)) \
   & MALLOC_ALIGN_MASK)
```

これらのマクロは隣り合わせで定義されていますが、`aligned_OK` はアドレス用、`misaligned_chunk` はチャンク用です。

[`MALLOC_ALIGN_MASK`](https://elixir.bootlin.com/glibc/glibc-2.32/source/malloc/malloc-internal.h#L62) は次のように定義されています。

```c
#define MALLOC_ALIGN_MASK (MALLOC_ALIGNMENT - 1)
```

[`MALLOC_ALIGNMENT`](https://elixir.bootlin.com/glibc/glibc-2.32/source/sysdeps/i386/malloc-alignment.h#L22) は i386 では `16` と定義されています。2 進数では `10000` なので、`MALLOC_ALIGN_MASK` は `1111` となり、最後のバイトが検査されます。その結果、想定どおり 16 ビットのアライメントになります。

このアライメントチェックがあるため、16 ビットのエントロピーを推測する必要があり、下位 16 ビットをブルートフォースして次の値にしようとすると、成功確率は 1/16 になります&#x20;
