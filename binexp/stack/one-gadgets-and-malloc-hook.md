---
description: 手早いシェル取得とポインタ
---

# One Gadgets and Malloc Hook

`one_gadget` とは、glibc に存在する `execve("/bin/sh")` を呼び出すコードのことで、GOT overwrite と組み合わせると手っ取り早い成果になりえます。その関数が次に呼ばれたときに `one_gadget` が実行され、シェルが取れるからです。

`__malloc_hook` は C の機能です。[GNU の公式サイト](https://www.gnu.org/software/libc/manual/html_node/Hooks-for-Malloc.html)では、`__malloc_hook` を次のように定義しています。

> The value of this variable is a pointer to the function that `malloc` uses whenever it is called.

要するに、`malloc()` を呼ぶと `__malloc_hook` が指している関数も呼ばれます。そのため、これを(たとえば)`one_gadget` で上書きでき、さらに何らかの方法で `malloc()` の呼び出しを引き起こせれば、簡単にシェルが取れます。

#### Finding One\_Gadgets

幸い、**Ruby** で書かれた `one_gadget` というツールがあります。インストールするには次を実行します。

```text
gem install one_gadget
```

そのうえで、次のように実行するだけです。

```text
one_gadget libc
```

{% hint style="info" %}
ほとんどの one\_gadget では、満たすべき条件があります。つまり、すべてが動くわけではなく、実際には **どれも** 動かないこともありえます。
{% endhint %}

#### Triggering malloc\(\)

ちょっと待ってください。`malloc()` は _ヒープ_ の関数ではないのですか。スタックのエクスプロイトでどうやって使うのでしょうか。実は、`printf("%10000$c")` を呼ぶことで `malloc` を引き起こせます(スタックには大きすぎるバイト数を確保しようとするため、libc は代わりにヒープ上に領域を確保します)。したがって、フォーマット文字列の脆弱性があれば、malloc を呼ぶのは簡単です。

#### Practise

この手法は、練習用に用意するのが難しいものです。お使いの `libc` のバージョンには、そもそも動作する `one_gadget` がないかもしれないからです。そのため、GOT overwrite のバイナリで自由に試して、`one_gadget` を動かせるか確かめてみてください。

`one_gadget` ツールが返す値はオフセットにすぎないので、libc のベースアドレスに足す必要があることを忘れないでください。
