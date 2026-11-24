---
description: 初歩的な double free 対策
---

# Tcache Keys

glibc 2.29 以降、tcache は `tcache_entry` 構造体に 2 つ目のフィールドである [`key`](https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L2908) を追加することで強化されました。

```c
typedef struct tcache_entry
{
  struct tcache_entry *next;
  /* This field exists to detect double frees.  */
  struct tcache_perthread_struct *key;
} tcache_entry;
```

これは `tcache_perthread_struct` へのポインタです。[`tcache_put()`](https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L2928) 関数を見ると、`key` に何が設定されるかが分かります。

```c
/* Caller must ensure that we know tc_idx is valid and there's room
   for more chunks.  */
static __always_inline void tcache_put (mchunkptr chunk, size_t tc_idx)
{
  tcache_entry *e = (tcache_entry *) chunk2mem (chunk);
  assert (tc_idx < TCACHE_MAX_BINS);

  /* Mark this chunk as "in the tcache" so the test in _int_free will
     detect a double free.  */
  e->key = tcache;

  e->next = tcache->entries[tc_idx];
  tcache->entries[tc_idx] = e;
  ++(tcache->counts[tc_idx]);
}
```

チャンクが解放されて `tcache_put()` が呼ばれると、`key` フィールドには `tcache_perthread_struct` の位置が設定されます。これがなぜ重要なのでしょうか。[`_int_free()` 内の tcache のセキュリティチェック](https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L4189)を確認しましょう。

```c
#if USE_TCACHE
  {
    size_t tc_idx = csize2tidx (size);
    if (tcache != NULL && tc_idx < mp_.tcache_bins)
      {
	/* Check to see if it's already in the tcache.  */
	tcache_entry *e = (tcache_entry *) chunk2mem (p);

	/* This test succeeds on double free.  However, we don't 100%
	   trust it (it also matches random payload data at a 1 in
	   2^<size_t> chance), so verify it's not an unlikely
	   coincidence before aborting.  */
	if (__glibc_unlikely (e->key == tcache))
	  {
	    tcache_entry *tmp;
	    LIBC_PROBE (memory_tcache_double_free, 2, e, tc_idx);
	    for (tmp = tcache->entries[tc_idx];
		 tmp;
		 tmp = tmp->next)
	      if (tmp == e)
		malloc_printerr ("free(): double free detected in tcache 2");
	    /* If we get here, it was a coincidence.  We've wasted a
	       few cycles, but don't abort.  */
	  }

	if (tcache->counts[tc_idx] < mp_.tcache_count)
	  {
	    tcache_put (p, tc_idx);
	    return;
	  }
      }
  }
#endif
```

解放されるチャンクは変数 `e` です。ここで、`tcache_put()` が呼ばれる前に、次のチェックが行われていることが分かります。

```c
if (__glibc_unlikely (e->key == tcache))
```

このチェックは、チャンク `e` の `key` フィールドがすでに `tcache_perthread_struct` のアドレスになっているかどうかを判定します。**これは `tcache_put()` で tcache に入れられるときに設定される**ことを思い出してください。ポインタがすでにそこにある場合、そのチャンクが**すでに解放済み**であるためである可能性が**非常に**高く、その場合は double free です。

ただし、100% 確実に double free だとは限りません。上のコメントにもあるとおりです。

> This test succeeds on double free.  However, we don't 100% trust it (it also matches random payload data at a 1 in 2^\<size\_t> chance), so verify it's not an unlikely coincidence before aborting.

`key` がすでに `tcache_perthread_struct` になっているのが偶然である確率は `1/2^<size_t>` あります。これを確かめるために、tcache bin を走査して、各チャンクを解放しようとしているチャンクと比較します。

```c
tcache_entry *tmp;
LIBC_PROBE (memory_tcache_double_free, 2, e, tc_idx);
for (tmp = tcache->entries[tc_idx]; tmp; tmp = tmp->next)
    if (tmp == e)
        malloc_printerr ("free(): double free detected in tcache 2");
/* If we get here, it was a coincidence.  We've wasted a
   few cycles, but don't abort.  */
```

各エントリを順にたどって `tmp` とし、`e` と比較します。等しければ double free を検出したことになります。

{% hint style="danger" %}
`key` は(ASLR により)実質的にランダムな値で、それと照合され、正しい値であれば何かが怪しい、と考えるとよいでしょう。
{% endhint %}

では、これに対して何ができるでしょうか。実は、この保護が私たちに与える影響は_それほど_大きくありません。単純な double free は防げますが、何らかの UAF プリミティブがあれば `e->key` を簡単に上書きできます。1 バイトだけでも、`key` と一致しない値に書き換えられる確率は 255/256 あります。偽の tcache チャンクを作る場合も問題ありません。最新の glibc でも [`tcache_get()` には `key` のチェックがない](https://elixir.bootlin.com/glibc/glibc-2.39/source/malloc/malloc.c#L3174)ため、tcache poisoning は依然として可能です。

それどころか、`key` は私たちにとって**役に立つ**こともあります。tcache チャンクの `fd` ポインタはマングリングされているため、UAF があってもヒープリークが得られるとは限りません。一方、`key` フィールドはマングリングされていないので、代わりに `tcache_perthread_struct` の位置をリークできれば、それは常に `heap_base + 0x10` にあるため、ヒープリークになります。

***

glibc 2.34 では、`key` フィールドが [`tcache_perthread_struct *` から `uintptr_t` に変更されました](https://elixir.bootlin.com/glibc/glibc-2.34/source/malloc/malloc.c#L3017)。`tcache_put()` は `key` に `tcache_perthread_struct` の位置を設定する代わりに、[`tcache_key` という新しい変数](https://elixir.bootlin.com/glibc/glibc-2.34/source/malloc/malloc.c#L3068)の値を設定します。

```c
static __always_inline void tcache_put (mchunkptr chunk, size_t tc_idx)
{
  tcache_entry *e = (tcache_entry *) chunk2mem (chunk);

  /* Mark this chunk as "in the tcache" so the test in _int_free will
     detect a double free.  */
  e->key = tcache_key;

  e->next = PROTECT_PTR (&e->next, tcache->entries[tc_idx]);
  tcache->entries[tc_idx] = e;
  ++(tcache->counts[tc_idx]);
}
```

{% hint style="info" %}
[Safe-Linking の `PROTECT_PTR`](safe-linking.md) にも注目してください。
{% endhint %}

`tcache_key` とは何でしょうか。[ここ](https://elixir.bootlin.com/glibc/glibc-2.34/source/malloc/malloc.c#L3035)で定義され、そのすぐ下にある [`tcache_key_initialise()`](https://elixir.bootlin.com/glibc/glibc-2.34/source/malloc/malloc.c#L3047) 関数で設定されます。

```c
static void tcache_key_initialize (void)
{
  if (__getrandom (&tcache_key, sizeof(tcache_key), GRND_NONBLOCK)
      != sizeof (tcache_key))
    {
      tcache_key = random_bits ();
#if __WORDSIZE == 64
      tcache_key = (tcache_key << 32) | random_bits ();
#endif
    }
}
```

ここでは `__getrandom()` を呼び出そうとします。これは[ここ](https://elixir.bootlin.com/glibc/glibc-2.34/source/stdlib/getrandom.c#L25)にスタブとして、Linux 向けには[ここ](https://elixir.bootlin.com/glibc/glibc-2.34/source/sysdeps/unix/sysv/linux/getrandom.c#L27)に定義されており、システムコールで `n` バイトのランダムなバイト列を読み取るだけです。何らかの理由で失敗した場合は、代わりに [`random_bits()`](https://elixir.bootlin.com/glibc/glibc-2.34/source/include/random-bits.h#L31) 関数を呼び出し、時刻をシードにした疑似乱数を生成します。要するに、**`tcache_key` はランダムです**。[`_int_free()` 内のチェックも依然として存在し](https://elixir.bootlin.com/glibc/glibc-2.34/source/malloc/malloc.c#L4346)、動作は同じですが、ASLR に基づくのではなく完全にランダムになった点が違います。上のコメントにもあるとおりです。

> The value of tcache\_key does not really have to be a cryptographically secure random number.  It only needs to be arbitrary enough so that it does not collide with values present in applications.  \[...]

大きな変更ではなく、影響を受けるのは単純な double free だけです。ただし、`key` 経由でヒープをリークすることはできなくなりました。
