---
description: Lack of space for ROP
---

# Stack Pivoting

## 概要

**Stack Pivoting** は、スタック上の空きが足りないときに使う手法です。たとえば、RIP の後ろに 16 バイトしかないような場合で、このとき完全な ROP チェーンは作れません。

Stack Pivoting では、**RSP** レジスタを制御して、スタックの場所を「偽装」します。方法はいくつかあります。

### pop rsp ガジェット

おそらく最も単純ですが、存在する可能性が最も低い方法です。もしあれば、かなり運が良いです。

### xchg &lt;reg&gt;, rsp

`pop <reg>` ガジェットが見つかれば、この `xchg` ガジェットを使って、その値と RSP の値を入れ替えられます。保存されたリターンポインタの後ろに、16 バイトほどのスタック領域が必要です。

```text
pop <reg>                <=== return pointer
<reg value>
xchg <rag>, rsp
```

### leave; ret

これは_非常に_面白いスタックピボットの方法で、必要なのは 8 バイトだけです。

すべての関数(`main` を除く)は、`leave; ret` ガジェットで終わります。`leave` は次と等価です。

```text
mov rsp, rbp
pop rbp
```

つまり、関数の終わりは次のようになります。

```text
mov rsp, rbp
pop rbp
pop rip
```

したがって、RIP を上書きするとき、その直前の 8 バイトが RBP を上書きします(以前に気づいたかもしれません)。つまり、`leave` を使って `rbp` を上書きできます。これがどう役に立つのでしょうか。

もう一度 `leave` を見ると、RBP の値が RSP に移されることに気づきます。だから、RBP を上書きし、さらに RIP を `leave; ret` のアドレスで上書きすると、RBP の値が RSP に移されます。しかも、RIP を上書きする以上のスタック領域は必要ありません。そのため、_非常に_コンパクトに済みます。

