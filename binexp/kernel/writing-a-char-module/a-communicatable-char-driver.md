# An Interactive Char Driver

対話的な Char ドライバを作るのは意外と簡単ですが、途中にいくつか落とし穴があります。

## Exposing it to the File System

ここは最も理解しにくい部分ですが、正直なところ、_完全_ に理解する必要はありません。新しい `intro_init` 関数は次のようになります。

```c
#define DEVICE_NAME "intro"
#define CLASS_NAME "intro"

// デバイスの設定
int major;
static struct class*  my_class  = NULL;
static struct device* my_device = NULL;

static int __init intro_init(void) {
    major = register_chrdev(0, DEVICE_NAME, &fops);    // 後で説明する

    if ( major < 0 )
        printk(KERN_ALERT "[Intro] Error assigning Major Number!");
    
    // デバイスクラスを登録する
    my_class = class_create(THIS_MODULE, CLASS_NAME);
    if (IS_ERR(my_class)) {
        unregister_chrdev(major, DEVICE_NAME);
        printk(KERN_ALERT "[Intro] Failed to register device class\n");
    }

    // デバイスドライバを登録する
    my_device = device_create(my_class, NULL, MKDEV(major, 0), NULL, DEVICE_NAME);
    if (IS_ERR(my_device)) {
        class_destroy(my_class);
        unregister_chrdev(major, DEVICE_NAME);
        printk(KERN_ALERT "[Intro] Failed to create the device\n");
    }

    return 0;
}
```

**メジャー番号(major number)** は、基本的にカーネルモジュールを一意に識別する ID です。`register_chrdev` の第 1 引数で指定できますが、`0` を渡すと、未使用のメジャー番号が自動的に割り当てられます。

次に、**クラス(class)** と **デバイス(device)** を登録する必要があります。正直なところ、これらが何をしているのかは私もよく理解していませんが、このコードでモジュールが `/dev/intro` に公開されます。

エラーが起きたときには、`class_destroy` と `unregister_chrdev` が呼ばれる点に注意してください。

## Cleaning it Up

これらの追加のクラスとデバイスは、`intro_exit` 関数で後片付けする必要があります。また、**メジャー番号** を再び利用可能にします。

```c
static void __exit intro_exit(void) {
    device_destroy(my_class, MKDEV(major, 0));              // デバイスを削除する
    class_unregister(my_class);                             // デバイスクラスの登録を解除する
    class_destroy(my_class);                                // デバイスクラスを削除する
    unregister_chrdev(major, DEVICE_NAME);                  // メジャー番号の登録を解除する
    printk(KERN_INFO "[Intro] Closing!\n");
}
```

## Controlling I/O

`intro_init` の最初の行は、分かりにくかったかもしれません。

```c
major = register_chrdev(0, DEVICE_NAME, &fops);
```

第 3 引数の `fops` がすべての要です。ここで、`read` や `write` といった操作のハンドラを作れます。ごく単純なものは、次のようになります。

```c
static ssize_t intro_read(struct file *filp, char __user *buffer, size_t len, loff_t *off) {
    printk(KERN_ALERT "reading...");

    copy_to_user(buffer, "QWERTY", 6);

    return 0;
}

static struct file_operations fops = {
    .read = intro_read
};
```

`intro_read` の引数は少し分かりにくいかもしれませんが、2 番目と 3 番目が、`read()` 関数自体の 2 番目と 3 番目の引数に対応しています。

```c
ssize_t read(int fd, void *buf, size_t count);
```

そして `copy_to_user` 関数を使い、引数として渡されたバッファに `QWERTY` を書き込みます。

## Full Code

```c
#include <linux/init.h>
#include <linux/module.h>

#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/device.h>
#include <linux/uaccess.h>

#define DEVICE_NAME "intro"
#define CLASS_NAME "intro"

MODULE_AUTHOR("ir0nstone");
MODULE_DESCRIPTION("Interactive Drivers");
MODULE_LICENSE("GPL");

// デバイスの設定
int major;
static struct class*  my_class  = NULL;
static struct device* my_device = NULL;

static ssize_t intro_read(struct file *filp, char __user *buffer, size_t len, loff_t *off) {
    printk(KERN_ALERT "reading...");

    copy_to_user(buffer, "QWERTY", 6);

    return 0;
}

static struct file_operations fops = {
    .read = intro_read
};

static int __init intro_init(void) {
    major = register_chrdev(0, DEVICE_NAME, &fops);

    if ( major < 0 )
        printk(KERN_ALERT "[Intro] Error assigning Major Number!");
    
    // デバイスクラスを登録する
    my_class = class_create(THIS_MODULE, CLASS_NAME);
    if (IS_ERR(my_class)) {
        unregister_chrdev(major, DEVICE_NAME);
        printk(KERN_ALERT "[Intro] Failed to register device class\n");
    }

    // デバイスドライバを登録する
    my_device = device_create(my_class, NULL, MKDEV(major, 0), NULL, DEVICE_NAME);
    if (IS_ERR(my_device)) {
        class_destroy(my_class);
        unregister_chrdev(major, DEVICE_NAME);
        printk(KERN_ALERT "[Intro] Failed to create the device\n");
    }

    return 0;
}

static void __exit intro_exit(void) {
    device_destroy(my_class, MKDEV(major, 0));              // デバイスを削除する
    class_unregister(my_class);                             // デバイスクラスの登録を解除する
    class_destroy(my_class);                                // デバイスクラスを削除する
    unregister_chrdev(major, DEVICE_NAME);                  // メジャー番号の登録を解除する
    printk(KERN_INFO "[Intro] Closing!\n");
}

module_init(intro_init);
module_exit(intro_exit);

```

読み込むには、[前と同じように](./#using-the-kernel-module) `sudo insmod` を使うだけです。

## Testing The Module

ごく基本的な `exploit.c` を作ります。

```c
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

int main() {
    int fd = open("/dev/intro", O_RDWR);    // デバイスを読み書き可能で開く
    printf("FD: %d\n", fd);                 // ファイルディスクリプタを表示する

    char buffer[6];
    memset(&buffer, 'A', 6);                // A で埋める
    printf("%s\n", buffer);                 // 表示する
    read(fd, buffer, 6);                    // モジュールから読み取る
    printf("%s\n", buffer);                 // もう一度表示する
}
```

モジュールが正しく読み込まれていれば、`read()` の呼び出しで `QWERTY` が `buffer` に読み込まれるはずです。

```
$ ./exploit

FD: 3
AAAAAA
QWERTY
```

成功です。
