# Writing a Char Module

## The Code

Char モジュールを書くのは、意外なほど簡単です。まず、`init`(モジュールの読み込み)と `exit`(モジュールの取り外し)で何が起こるかを指定します。そのために、いくつか特別なヘッダが必要です。

```c
#include <linux/init.h>
#include <linux/module.h>

MODULE_LICENSE("Mine!");

static int intro_init(void) {
    printk(KERN_ALERT "Custom Module Started!\n");
    return 0;
}

static void intro_exit(void) {
    printk(KERN_ALERT "Custom Module Stopped :(\n");
}

module_init(intro_init);
module_exit(intro_exit);

```

簡単に見えますが、実際に簡単です。少なくとも今のところは。

まずライセンスを設定します。設定しないと警告が出て、私は警告が嫌いだからです。次に、読み込み時(`intro_init()`)と取り外し時(`intro_exit()`)に何をするかをモジュールに伝えます。パラメータを `void` にしている点に注意してください。カーネルモジュールは、[パラメータを必須とすること](https://stackoverflow.com/questions/40309582/kernel-module-compiler-error-function-declaration-isn-t-a-prototype-werror-st)(たとえ void だけであっても)に非常に厳しいためです。

続いて、`module_init()` と `module_exit()` を使って、それぞれの関数の役割を登録します。

`printf` ではなく `printk` を使っている点にも注意してください。カーネルモードには GLIBC が存在せず、代わりに C に組み込まれたカーネルの機能を使います。`KERN_ALERT` は送るメッセージの種類を指定するもので、[ほかにも多くの種類があります](https://www.kernel.org/doc/html/latest/core-api/printk-basics.html)。

## Compiling

カーネルオブジェクトのコンパイルは、[`Makefile`](https://opensource.com/article/18/8/what-how-makefile) を使うので少し複雑に見えるかもしれませんが、実際には意外と簡単です。

```
obj-m += intro.o
 
all:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
```

`$(MAKE)` は特別なフラグで、実質的に `make` を呼び出しますが、_私たちの_ `Makefile` が呼び出されたときと同じフラグをすべて引き継ぎます。例えば、次のように呼び出すと、

```bash
$ make -j 8
```

`$(MAKE)` は `make -j 8` になります。本質的に、`$(MAKE)` はモジュールをコンパイルする `make` です。生成されるファイルは、先頭の `obj-m` で定義されています。コンパイルは **カーネルごとに固有** であるため、コンパイル処理がその環境固有のカーネルビルドの領域を使っている点に注意してください。

## Using the Kernel Module

`ko` ファイルのコンパイルができたので、有効なモジュールの一覧に追加できます。

```
$ sudo insmod test.ko
```

成功すると、何も出力されません。では、どこに出力されたのでしょうか。

カーネルのプログラムはユーザー空間という概念を持たないことを思い出してください。誰が実行したのかも知りませんし、ユーザー空間とやり取りする気もありません。このコードはカーネル内で動作するので、出力は `sudo dmesg` で確認できます。

```
$ sudo dmesg | tail -n 1
[ 3645.657331] Custom Module Started!
```

ここでは `tail` で最後の 1 行を取り出しています。`printk` が呼ばれたことが分かります。

では、モジュールを取り外しましょう。

```
$ sudo rmmod test
$ sudo dmesg | tail -n 1
[ 4046.904898] Custom Module Stopped :(
```

こうして `intro_exit` が呼ばれます。

{% hint style="info" %}
`lsmod` コマンドで、現在読み込まれているモジュールを確認できます。
{% endhint %}
