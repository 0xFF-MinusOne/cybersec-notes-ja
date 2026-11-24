---
description: Controlling execution with snippets of code
---

# Gadgets

ガジェット(gadget)とは、`pop rdi; ret` のように、`ret` 命令で終わる小さなコードの断片です。これらのガジェットの `ret` をうまく操作すると、大きな連鎖(チェーン)を作って、望みの動作をさせられます。

### 例

`pop rdi; ret` ガジェットの実行中、スタックが次のようになっているとします。

![](../../../.gitbook/assets/image%20%2820%29.png)

何が起きるかは明らかです。`pop rdi` の時点でスタックの先頭にある `0x10` が `rdi` に pop されます。`pop` が行われると、`rsp` が移動します。

![](../../../.gitbook/assets/image%20%2822%29.png)

そして `ret` は `pop rip` と等価なので、`0x5655576724` が `rip` に入ります。このときスタックがどう並んでいるかに注目してください。

### ガジェットを利用する

リターンポインタを上書きすると、`rsp` が指す値を上書きしたことになります。その値が pop されると、`rsp` はスタック上の次の値を指します。そして、その次の値も上書きできるのです。

たとえば、`pop rdi; ret` ガジェットにジャンプし、`0x100` を `rdi` に pop してから `flag()` にジャンプするようにバイナリをエクスプロイトしたいとします。実行を順番に追ってみましょう。

![](../../../.gitbook/assets/image%20%2823%29.png)

リターンポインタを上書きした_元の_ `ret` で、ガジェットのアドレスが pop されます。`rip` はガジェットを指すように移動し、`rsp` は次のメモリアドレスに移動します。

![](../../../.gitbook/assets/image%20%2825%29.png)

`rsp` は `0x100` に、`rip` は `pop rdi` に移動します。ここで pop すると、`0x100` が `rdi` に入ります。

![](../../../.gitbook/assets/image%20%2821%29.png)

RSP はスタックの次の要素、つまり `flag()` のアドレスに移動します。`ret` が実行され、`flag()` が呼び出されます。

### まとめ

基本的には、ガジェットがスタックから値を pop するなら、その値を後ろに置いていくだけです(`ret` に含まれる `pop rip` の分も含みます)。`0x10` を `rdi` に pop してから `0x16` にジャンプしたい場合、ペイロードは次のようになります。

![](../../../.gitbook/assets/image%20%2824%29.png)

`pop` 命令が複数ある場合は、値を増やしていくだけです。

![](../../../.gitbook/assets/image%20%2826%29.png)

{% hint style="info" %}
例に `rdi` を使っているのは、覚えているとおり、64-bit では第 1 パラメータのレジスタだからです。つまり、このガジェットでこのレジスタを制御できることが重要です。
{% endhint %}

### ガジェットを探す

[`ROPgadget`](https://github.com/JonathanSalwan/ROPgadget) というツールで、使えそうなガジェットを探せます。

```text
$ ROPgadget --binary vuln-64

Gadgets information
============================================================
0x0000000000401069 : add ah, dh ; nop dword ptr [rax + rax] ; ret
0x000000000040109b : add bh, bh ; loopne 0x40110a ; nop ; ret
0x0000000000401037 : add byte ptr [rax], al ; add byte ptr [rax], al ; jmp 0x401024
[...]
```

`grep` と組み合わせると、特定のレジスタに関するものを探せます。

```text
$ ROPgadget --binary vuln-64 | grep rdi

0x0000000000401096 : or dword ptr [rdi + 0x404030], edi ; jmp rax
0x00000000004011db : pop rdi ; ret
```
