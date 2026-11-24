---
description: オフセットを計算するより良い方法
---

# De Bruijn 列(De Bruijn Sequences)

位数 `n` の De Bruijn 列とは、長さ `n` の文字列がどれも繰り返し現れない列のことです。これにより、EIP までのオフセットを求めるのがずっと簡単になります。De Bruijn 列を入力し、EIP に入った値を取得して、列の中で**一致する箇所がひとつだけ**であることを利用してオフセットを計算できます。**ret2win** のバイナリで試してみましょう。

### パターンの生成

ここでも `radare2` には、パターンを生成してくれる便利なコマンドラインツール(`ragg2`)が付属しています。長さ `100` の列を作ってみましょう。

```text
$ ragg2 -P 100 -r
AAABAACAADAAEAAFAAGAAHAAIAAJAAKAALAAMAANAAOAAPAAQAARAASAATAAUAAVAAWAAXAAYAAZAAaAAbAAcAAdAAeAAfAAgAAh
```

`-P` は長さを指定し、`-r` は 16 進数のペアではなく ASCII のバイトで表示するよう指示します。

### パターンの使用

パターンができたので、入力を求められたときに `radare2` 上でそのまま入力してクラッシュさせ、EIP が列のどこにあるかを計算します。簡単です。

```text
$ r2 -d -A vuln

[0xf7ede0b0]> dc
Overflow me
AAABAACAADAAEAAFAAGAAHAAIAAJAAKAALAAMAANAAOAAPAAQAARAASAATAAUAAVAAWAAXAAYAAZAAaAAbAAcAAdAAeAAfAAgAAh
child stopped with signal 11
[+] SIGNAL 11 errno=0 addr=0x41534141 code=1 ret=0
```

クラッシュしたアドレスは `0x41534141` です。`radare2` に組み込まれた `wopO` コマンドでオフセットを求められます。

```text
[0x41534141]> wopO 0x41534141
52
```

すばらしい、正しい値が得られました。

値をコピーしなくても済ませることもできます。

```text
[0x41534141]> wopO `dr eip`
52
```

バッククォートは、`dr eip` を先に評価し、その結果に対して `wopO` を実行することを意味します。

