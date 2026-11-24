# 基本的なカーネルとのやり取りの問題

## モジュール

正しいパスワードを入力するとフラグを読み取れる、ごく基本的な認証モジュールを作ります。関連するコードは次のとおりです。

```c
#define PASSWORD    "p4ssw0rd"
#define FLAG        "flag{YES!}"
#define FAIL        "FAIL: Not Authenticated!"

static int authenticated = 0;

static ssize_t auth_read(struct file *filp, char __user *buf, size_t len, loff_t *off) {
    printk(KERN_ALERT "[Auth] Attempting to read flag...");

    if (authenticated) {
        copy_to_user(buf, FLAG, sizeof(FLAG));      // ここでは `len` を無視している
        return 1;
    }

    copy_to_user(buf, FAIL, sizeof(FAIL));
    return 0;
}

static ssize_t auth_write(struct file *filp, const char __user *buf, size_t count, loff_t *f_pos) {
    char password_attempt[20];

    printk(KERN_ALERT "[Auth] Reading password from user...");

    copy_from_user(password_attempt, buf, count);

    if (!strcmp(password_attempt, PASSWORD)) {
        printk(KERN_ALERT "[Auth] Password correct!");
        authenticated = 1;
        return 1;
    }

    printk(KERN_ALERT "[Auth] Password incorrect!");

    return 0;
}
```

デバイスから `read()` しようとすると、`authenticated` フラグを確認して、フラグを返してよいかどうかを判断します。返せない場合は `FAIL: Not Authenticated!` が返されます。

`authenticated` を更新するには、カーネルモジュールに `write()` する必要があります。書き込もうとした内容は `p4ssw0rd` と比較されます。等しくなければ何も起こりません。等しければ `authenticated` が更新され、次に `read()` したときにフラグが返されます。

### やり取りする

まずは、カーネルから読み取ることでやり取りを試してみましょう。

{% hint style="info" %}
必ず `sudo chmod 666 /dev/authentication` を実行してください。
{% endhint %}

まずデバイスを開いて、そこから読み取ります。

```c
int fd = open("/dev/authentication", O_RDWR);

char buffer[20];
read(fd, buffer, 20);
printf("%s\n", buffer);
```

{% hint style="info" %}
モジュールのソースコードでは `read()` の長さがまったく考慮されていないため、どんな数値にしても構わないことに注意してください。`1` に変えて試してみると分かります。
{% endhint %}

コンパイルして実行すると、認証されていないことが分かります。

<pre class="language-bash"><code class="lang-bash"><strong>$ ./exploit 
</strong>FAIL: Not Authenticated!
</code></pre>

すばらしい。では、デバイスに正しいパスワードを書き込んで、もう一度試しましょう。ここでヌルバイトを送ることが非常に重要です。`copy_from_user()` はヌルバイトを自動では追加しないため、送らないと `strcmp` が失敗してしまいます。

```c
write(fd, "p4ssw0rd\0", 9);

read(fd, buffer, 20);
printf("%s\n", buffer);
```

うまくいきました。

```bash
$ ./exploit
FAIL: Not Authenticated!
flag{YES!}
```

すごい。ここで、本当に重要なことがあります。

```bash
$ ./exploit 
flag{YES!}
flag{YES!}
```

**状態は接続をまたいで保持されます**。カーネルモジュールは動き続けているため、モジュールが再読み込みされるまで(`rmmod` してから `insmod` するか、システムを再起動するまで)認証された状態が続きます。

### 最終的なコード

```c
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

int main() {
    int fd = open("/dev/authentication", O_RDWR);

    char buffer[20];
    read(fd, buffer, 1);
    printf("%s\n", buffer);

    write(fd, "p4ssw0rd", 8);

    read(fd, buffer, 20);
    printf("%s\n", buffer);
}
```

{% file src="../../.gitbook/assets/basic_interaction (1).zip" %}
ソースコード
{% endfile %}

## 課題: IOCTL

では、ここで課題です。**同じ**カーネルモジュールを、今度は `ioctl` を使って書いてください。そして、それとやり取りして同じ操作を行うプログラムを書きます。両方を含む ZIP ファイルを下に用意してありますが、ずるはしないでください。とてもよい練習になります。

{% file src="../../.gitbook/assets/basic_authentication_ioctl.zip" %}
解答例
{% endfile %}
