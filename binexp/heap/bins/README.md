# チャンクの解放と bin

## 解放の概要

チャンク(chunk)のデータが不要になったら、`free()` などの関数でそのデータを**解放(free)**します。これは、メモリのこの部分をもう使い終わったことを glibc に伝える操作です。

glibc は、できるだけ効率よく動くために、使い終わったチャンクを後続の要求に**再利用(recycle)**しようと、かなり工夫しています。例として、ユーザーが入力した文字列を保存するのに `100` バイト必要だったとします。使い終わったら、もう使わないことを glibc に伝えます。プログラムの後のほうで、ユーザーからまた 100 バイトの文字列を受け取る必要が出てきました。それなら、同じメモリ領域を再利用すればよさそうです。再利用しない理由はありませんよね。

このメモリの再利用の大部分を担っているのが **bin** です。bin は、解放済みチャンクの(双方向または単方向の)連結リストです。効率のために、サイズごとに異なる bin が使われます。また、高い性能を保つため、bin の種類によって操作も異なります。

チャンクが解放されると、そのチャンクは bin に「移動」されます。この移動は物理的なものではありません。チャンクへの**参照**であるポインタ(**pointer**)が、リストのどこかに保存されるということです。

## bin の操作

bin は 4 種類あります。**fastbin**、**unsorted bin**、**small bin**、**largebin** です。

チャンクが解放されるとき、glibc で処理の大部分を担う関数は [`_int_free()`](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4102) です。ここではソースコードの詳細には踏み込みません。代わりに、セキュリティチェックのない非常に古いバージョンである glibc 2.3 へのハイパーリンクを示します。コードの内容に目を通して慣れておくとよいでしょう。ただし、現在の実装では、コードの配置がかなり変わっていることに注意してください。**bootlin** の左側でバージョンを切り替えると、どう変わってきたかが分かります。

* まず、[チャンクの `size` を確認します](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4127)。最大の fastbin サイズより小さければ、[適切な fastbin に追加します](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4139)
* そうでなく、mmap されたチャンクであれば、[そのチャンクを `munmap` します](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4237)
* 最後に、[**統合(consolidate)**](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4165)したうえで、[unsorted bin に入れます](https://elixir.bootlin.com/glibc/glibc-2.3/source/malloc/malloc.c#L4172)

統合(consolidation)とは何でしょうか。具体的な内容は後で詳しく見ますが、要するに、解放しようとしているチャンクの周りにある別の解放済みチャンクを見つけて、それらを**1 つの大きなチャンク**にまとめる処理です。これによって再利用が効率的になります。

### Fastbin

fastbin は小さいサイズのチャンクを保存します。fastbin は 10 個あり、**メタデータを含めて** 16、24、32、40、48、56、64、72、80、88 バイトのチャンク用です。

### Unsorted bin

これは 1 つだけです。small チャンクや large チャンクが解放されると、確保と解放の要求を高速化するために、いったんこの bin に入ります。

つまりこの bin は、チャンクに再利用される最後の機会を与えるものです。今後の malloc の要求が、bin に入っているチャンクより小さい場合は、そのチャンクを 2 つに分割して片方を返すので、処理が速くなります。これが [Last Remainder Chunk](https://ir0nstone.gitbook.io/notes/types/heap/chunks#last-remainder-chunk) です。要求されたサイズのほうが**大きい**場合は、この bin 内のチャンクがそれぞれ対応する small bin や large bin に移されます。

### Small bin

small bin は 62 個あり、サイズは 16、24、...、504 バイトです。fastbin と同様に、同じサイズのチャンクは同じ bin に保存されます。small bin は**双方向連結リスト**で、確保と解放は FIFO です。

前に見たとおり、`FD` ポインタと `BK` ポインタの役割は、bin 内の前後のチャンクを指すことです。

unsorted bin に入る前に、連続した small チャンク(メモリ上で隣り合っている small チャンク)は**合体(coalesce、consolidate)**できます。つまり、サイズが合算されて、より大きなチャンクになります。

### Large bin

large bin は 63 個あり、異なるサイズのチャンクを保存できます。解放済みチャンクはサイズの降順に並べられるので、挿入と削除はリストのどの位置でも起こり得ます。

最初の 32 個の bin は、それぞれ 64 バイトの範囲を持ちます。

```
1st bin: 512 - 568 bytes
2nd bin: 576 - 632 bytes
[...]
```

small チャンクと同様に、large チャンクも unsorted bin に入る前に合体できます。

## HEAD と TAIL

各 bin は `HEAD` と `TAIL` の 2 つの値で表されます。名前のとおり、`HEAD` が先頭、`TAIL` が末尾です。挿入の大部分は `HEAD` で行われます。そのため、(fastbin のような)LIFO 構造では再確保も `HEAD` で起こります。一方、(small bin のような)FIFO 構造では、再確保は `TAIL` で起こります。fastbin では、`TAIL` は `null` です。
