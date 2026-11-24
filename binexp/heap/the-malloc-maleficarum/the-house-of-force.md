---
description: wilderness を悪用する
---

# The House of Force

<table data-header-hidden><thead><tr><th width="283"></th><th></th></tr></thead><tbody><tr><td>Glibc のバージョン</td><td>*-<a href="https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L4114">2.29</a></td></tr><tr><td>必要なプリミティブ</td><td><ul><li>top chunk へのヒープオーバーフロー</li><li>任意のサイズのチャンクの確保</li></ul></td></tr><tr><td>得られるプリミティブ</td><td><ul><li>任意書き込み(Arbitrary Write)</li></ul></td></tr></tbody></table>

House of Force では、[top chunk](../the-top-chunk-and-remainder.md) の `size` フィールドを巨大な値でオーバーフローさせます。次に、**巨大な**サイズのチャンクを確保します。サイズを上書きしてあるため、[top chunk のサイズチェック](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L4088)をすり抜けられます。

```c
if ((unsigned long) (size) >= (unsigned long) (nb + MINSIZE))
```

チェックを通過するので、glibc をだまして、`mmap()` を使わずにヒープ上でその大きな要求を処理させることができます。これにより、**remainder チャンク**を大きく制御できるようになります。

```c
remainder_size = size - nb;
remainder = chunk_at_offset (victim, nb);
av->top = remainder;
```

確保サイズ(ここでは `nb` 変数)を制御できる場合、そのサイズが [`chunk_at_offset()`](https://elixir.bootlin.com/glibc/glibc-2.26/source/malloc/malloc.c#L1300) に渡されることに注意してください。

```c
/* Treat space at ptr + offset as a chunk */
#define chunk_at_offset(p, s)  ((mchunkptr) (((char *) (p)) + (s)))
```

このマクロはアドレスに `nb` を加算します。しかし `nb` を制御できるため、**remainder チャンクが置かれる場所**、したがって**次の top chunk の位置**を制御できます。つまり、**次の**確保が、好きなアドレスに配置されることになります。

{% hint style="info" %}
**整数オーバーフロー**を引き起こせば、メモリ上でヒープより**手前**にあるアドレスにも書き込めることに注意してください。
{% endhint %}

&#x20;TODO 数学的な説明

TODO ソースコード

TODO パッチ

## パッチ

glibc 2.29 では、House of Force を防ぐための[新しいセキュリティチェック](https://elixir.bootlin.com/glibc/glibc-2.29/source/malloc/malloc.c#L4114)が追加されました。

```c
if (__glibc_unlikely (size > av->system_mem))
    malloc_printerr ("malloc(): corrupted top size");
```

とても単純で、サイズが途方もなく大きくないかを確認し、大きければエラーを出します。
