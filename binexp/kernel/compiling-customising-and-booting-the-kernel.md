---
description: >-
  独自の設定でカーネルをコンパイルする手順と、特定のカーネルバージョン向けに
  カーネルモジュールをコンパイルする手順です。
---

# カーネルのコンパイル、カスタマイズ、起動

{% hint style="info" %}
カーネルエクスプロイトの書き方を学ぶだけなら、この内容は必須ではありません。重要な部分はすべて提供されます。これは、自分で問題を作りたい方や、学習用に自分で VM を用意したい方のための補足です。
{% endhint %}

## 前提条件

```bash
$ apt-get install flex bison libelf-dev
```

{% hint style="info" %}
ほかにも必要なものがあるかもしれませんが、私の環境にはすでに入っていました。完全な一覧は[こちら](https://github.com/torvalds/linux/blob/master/Documentation/process/changes.rst)で確認してください。
{% endhint %}

## カーネル

### クローン

```bash
git clone https://github.com/torvalds/linux --depth=1
```

`--depth 1` を使うと、最新のコミットだけを取得できます。

### カスタマイズ

現在のコンパイル設定は、今回の目的には複雑すぎるので削除します。

```bash
$ cd linux
$ rm -f .config
```

これで、ほとんどのオプションを無効にした**最小構成**を作れます。可能な限り少ない機能とドライバだけを含む `.config` ファイルが生成されます。

```bash
$ make allnoconfig
  YACC    scripts/kconfig/parser.tab.[ch]
  HOSTCC  scripts/kconfig/lexer.lex.o
  HOSTCC  scripts/kconfig/menu.o
  HOSTCC  scripts/kconfig/parser.tab.o
  HOSTCC  scripts/kconfig/preprocess.o
  HOSTCC  scripts/kconfig/symbol.o
  HOSTCC  scripts/kconfig/util.o
  HOSTLD  scripts/kconfig/conf
#
# configuration written to .config
#
```

有効にしたいオプションを書いた `kconfig` ファイルを作ります。例は次のとおりです。

```
CONFIG_64BIT=y
CONFIG_SMP=y
CONFIG_PRINTK=y
CONFIG_PRINTK_TIME=y

CONFIG_PCI=y

# We use an initramfs for busybox with elf binaries in it.
CONFIG_BLK_DEV_INITRD=y
CONFIG_RD_GZIP=y
CONFIG_BINFMT_ELF=y
CONFIG_BINFMT_SCRIPT=y

# This is for /dev file system.
CONFIG_DEVTMPFS=y

# For the power-down button (triggered by qemu's `system_powerdown` command).
CONFIG_INPUT=y
CONFIG_INPUT_EVDEV=y
CONFIG_INPUT_KEYBOARD=y

CONFIG_MODULES=y

CONFIG_KPROBES=n
CONFIG_LTO_NONE=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_EMBEDDED=n
CONFIG_TMPFS=y

CONFIG_RELOCATABLE=y
CONFIG_RANDOMIZE_BASE=y

CONFIG_USERFAULTFD=y
```

<details>

<summary>オプションの説明</summary>

* `CONFIG_64BIT` - カーネルを 64 ビット向けにコンパイルする
* `CONFIG_SMP` - 対称型マルチプロセッシング(simultaneous multiprocessing)。カーネルが複数のコアで動作できるようにする
* `CONFIG_PRINTK`, `CONFIG_PRINTK_TIME` - ログメッセージとタイムスタンプを有効にする
* `CONFIG_PCI` - 初期 RAM ディスクの読み込みのサポートを有効にする
* `CONFIG_RD_GZIP` - gzip 圧縮された initrd イメージのサポートを有効にする
* `CONFIG_BINFMT_ELF` - ELF バイナリの実行のサポートを有効にする
* `CONFIG_BINFMT_SCRIPT` - シバン(`#!`)行付きのスクリプトの実行を有効にする
* `CONFIG_DEVTMPFS` - 起動時に devtmpfs を使って `/dev` にデバイスノードを自動作成できるようにする
* `CONFIG_INPUT` - 入力デバイスの処理に必要な汎用入力レイヤーのサポートを有効にする
* `CONFIG_INPUT_EVDEV` - 統一的な入力イベントの枠組みを提供するイベントデバイスインターフェースのサポートを有効にする
* `CONFIG_INPUT_KEYBOARD` - キーボードのサポートを有効にする
* `CONFIG_MODULES` - カーネルモジュールの読み込みと取り外しのサポートを有効にする
* `CONFIG_KPROBES` - カーネルベースのデバッグ機構である kprobes のサポートを無効にする。無効にする理由は ... TODO
* `CONFIG_LTO_NONE` - カーネルのコンパイルで**リンク時最適化**(Link Time Optimization、LTO)を無効にする。これは[デバッグをしやすくする](https://stackoverflow.com/questions/7857601/why-not-always-use-compiler-optimization)ためです&#x20;
* `CONFIG_SERIAL_8250`, `CONFIG_SERIAL_8250_CONSOLE` - TODO
* `CONFIG_EMBEDDED` - 組み込みシステム向けの最適化や機能を無効にする
* `CONFIG_TMPFS` - メモリ上のファイルシステムである tmpfs のサポートを有効にする
* `CONFIG_RELOCATABLE` - 異なる物理アドレスに読み込める再配置可能なカーネルをビルドする
* `CONFIG_RANDOMIZE_BASE` - KASLR のサポートを有効にする
* `CONFIG_USERFAULTFD` - ユーザー空間でページフォールトを処理できる `userfaultfd` システムコールのサポートを有効にする

</details>

最小構成の `.config` をこれらのオプションで更新するには、付属の `merge_config.sh` スクリプトを使います。

```bash
$ scripts/kconfig/merge_config.sh .config ../kconfig
```

### ビルド

```bash
$ make -j4
```

しばらく時間がかかりますが、最終的に `arch/x86/boot/bzImage` にカーネルがビルドされます。これは、CTF の問題で渡されるものと同じ `bzImage` です。

## カーネルモジュール

[自分のカーネル向けにカーネルモジュールをコンパイルする場合](writing-a-char-module/#compiling)は、次のような `Makefile` の構成を使います。

```
all:
    make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
```

別のカーネル向けにコンパイルするには、`-C` フラグを、システムのものではなく新しくコンパイルしたカーネルを指すように変えるだけです。

```
all:
    make -C /home/ir0nstone/linux M=$(PWD) modules
```

これで、モジュールが特定のカーネルバージョン向けにコンパイルされます。

## 仮想マシンでカーネルを起動する

### 参考資料

* [Build the Linux kernel and Busybox and run them on QEMU](https://www.centennialsoftwaresolutions.com/post/Build-the-Linux-kernel-and-Busybox-and-run-on-QEMU)
* [How to Build A Custom Linux Kernel For Qemu (2015 Edition)](https://mgalgs.io/2015/05/16/how-to-build-a-custom-linux-kernel-for-qemu-2015-edition.html)

### ファイルシステムと実行ファイルを作る

これで、最小構成のカーネル `bzImage` と、それ向けにコンパイルしたカーネルモジュールが手に入りました。次は、それを動かすための最小限の VM を作ります。

そのために、ほとんどの Linux コマンドの小型版を 1 つにまとめた実行ファイル [`busybox`](https://busybox.net/about.html) を使います。これにより、必要なプログラムをできるだけ小さな容量でそろえられます。

`busybox` をダウンロードして展開します。最新バージョンは[こちら](https://busybox.net/downloads/)で確認できます。

<pre class="language-bash"><code class="lang-bash"><strong>$ curl https://busybox.net/downloads/busybox-1.36.1.tar.bz2 | tar xjf -
</strong></code></pre>

コンパイル結果を置く出力用のフォルダも作ります。

```bash
$ mkdir busybox_compiled
```

次に、静的にコンパイルします。いくつか選択ができるように、`menuconfig` オプションを使います。

```bash
$ cd busybox-1.36.1
$ make O=../busybox_compiled menuconfig
```

メニューが表示されたら、`Settings` で `Enter` を押します。`Build static binary (no shared libs)` のオプションまで下矢印キーで移動し、`Space` で選択してから、`Escape` を 2 回押して抜けます。設定を保存することを必ず選んでください。

新しいオプションでビルドします。

```bash
$ cd ../busybox_compiled
$ make -j
$ make install
```

次に、ファイルシステムを作ります。

```bash
$ cd ..
$ mkdir initramfs
$ cd initramfs
$ mkdir -pv {bin,dev,sbin,etc,proc,sys/kernel/debug,usr/{bin,sbin},lib,lib64,mnt/root,root}
$ cp -av ../busybox_compiled/_install/* .
$ sudo cp -av /dev/{null,console,tty,sda1} dev/
```

あとは、システムの起動時に実行される、おなじみの `init` スクリプトだけが足りません。今のところは仮のもので十分です。

```bash
#!/bin/sh
 
mount -t proc none /proc
mount -t sysfs none /sys
 
echo -e "\nBoot took $(cut -d' ' -f1 /proc/uptime) seconds\n"
 
exec /bin/sh
```

実行可能にします。

```bash
$ chmod +x init
```

最後に、QEMU が認識できる `cpio` アーカイブにまとめます。

```bash
find . -not -name *.cpio | cpio -o -H newc > initramfs.cpio
```

{% hint style="warning" %}
* `-not -name *.cpio` は、アーカイブ自身が含まれてしまうのを防ぐためのものです
* ファイルシステムを `.cpio.gz` ファイルに圧縮することもでき、QEMU はそれも認識します
{% endhint %}

`cpio` アーカイブを展開したい場合(たとえば CTF の最中など)は、次のコマンドを使えます。

```bash
$ cpio -i -F initramfs.cpio
```

### QEMU で読み込む

`bzImage` と `initramfs.cpio` を同じフォルダに置きます。QEMU を起動する短い `run.sh` スクリプトを書きます。

```bash
#!/bin/sh

qemu-system-x86_64 \
    -kernel bzImage \
    -initrd initramfs.cpio \
    -append "console=ttyS0 quiet loglevel=3 oops=panic" \
    -monitor /dev/null \
    -nographic \
    -no-reboot
```

<details>

<summary>フラグの説明</summary>

* `-kernel bzImage` - カーネルとして、コンパイルした `bzImage` を指定する
* `-initrd initramfs.cpio` - ファイルシステムを渡す
* `-append ...` - 基本的な機能を指定する。今後、このフラグは保護機構の設定にも使います
  * `console=ttyS0` - カーネルのメッセージを最初のシリアルポート(`ttyS0`)に出力する
  * `quiet` - カーネルからは重要なメッセージだけを表示する
  * `loglevel=3` - エラーメッセージとそれより優先度の高いメッセージだけを表示する
  * `oops=panic` - **oops**(カーネルエラー)が起きたら、カーネルをただちに panic させる
* `-monitor /dev/null` - QEMU モニタを無効にする
* `-nographic` - GUI を無効にし、ヘッドレスモードで動作させる(より高速)
* `no-reboot` - 問題が起きたときに VM を自動で再起動しない(クラッシュログが残るので、デバッグやクラッシュの原因の調査に便利です)

</details>

これを実行可能にして実行すると、VM が起動します。

### ユーザーアカウント

現時点で、起動できる最小限の Linux カーネルはできていますが、自分が誰なのかを調べようとすると、期待どおりには動作しません。

```
~ # whoami
whoami: unknown uid 0
```

これは `/etc/passwd` と `/etc/group` が存在しないためなので、作ってしまえば解決します。

{% code title="/etc/passwd" %}
```
root:x:0:0:root:/root:/bin/sh
user:x:1000:1000:User:/home/user:/bin/sh
```
{% endcode %}

{% code title="/etc/group" %}
```
root:x:0:
user:x:1000:
```
{% endcode %}

### カーネルモジュールを読み込む

最後の手順は、もちろんカーネルモジュールの読み込みです。ここでは、私の [Double Fetch](double-fetch/) の節で使ったモジュールを使います。

まず、`.ko` ファイルをファイルシステムのルートにコピーします。次に、`init` スクリプトを修正してそれを読み込ませ、起動するシェルの UID も `1000` に設定します(root にならないようにするためです)。

```bash
#!/bin/sh

insmod /double_fetch.ko
mknod /dev/double_fetch c 253 0
chmod 666 /dev/double_fetch

mount -t proc none /proc
mount -t sysfs none /sys

mknod -m 666 /dev/ttyS0 c 4 64

setsid /bin/cttyhack setuidgid 1000 /bin/sh
```

{% hint style="danger" %}
ここでは、`double_fetch` モジュールのメジャー番号が `253` であると仮定しています。

なぜそうするのでしょうか。

シェルに入って `cat /proc/devices` を実行すると、`double_fetch` が毎回メジャー番号 `253` で読み込まれていることが分かります。メジャー番号を推測_せずに_読み込む方法が見つからなかったので、今のところはこの方法で進めます。方法をご存じの方はぜひご連絡ください。
{% endhint %}

## 別のバージョンのカーネルをコンパイルする

最新**ではない**バージョンのカーネルをコンパイルしたい場合は、すべての[タグ](https://github.com/torvalds/linux/tags)を取得します。

<pre class="language-bash"><code class="lang-bash"><strong>$ git fetch --tags
</strong></code></pre>

当然ながら、実行にはかなり時間がかかります。取得できたら、好きなバージョンをチェックアウトできます。

<pre class="language-bash"><code class="lang-bash"><strong>$ git checkout v5.11
</strong></code></pre>

そこから先は同じ手順で進めます。

{% hint style="danger" %}
タグによっては、コンパイルに必要な正しいヘッダファイルがないようです。また、不思議なことに、ビルドは通るのに QEMU で一向に起動しないカーネルになるタグもあります。正直なところ、理由はよく分かっていません。
{% endhint %}
