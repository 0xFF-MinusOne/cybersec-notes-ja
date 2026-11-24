---
description: ドライバとやり取りするための、より便利な方法
---

# Interactivity with IOCTL

Linux には `ioctl` というシステムコールがあり、ドライバとの通信によく使われます。`ioctl()` は 3 つの引数を取ります。

* ファイルディスクリプタ `fd`
* `unsigned int`
* `unsigned long`

後ろの 2 つは、ドライバ側で、ほぼ何にでも合わせられます。構造体へのポインタや文字列などです。ドライバのソースでは、おおよそ次のようなコードになります。

```c
static ssize_t ioctl_handler(struct file *file, unsigned int cmd, unsigned long arg) {
    printk("Command: %d; Argument: %d", cmd, arg);

    return 0;
}
```

ただし、ドライバをそのように動かしたければ、`cmd` と `arg` をポインタとして解釈することもできます。

この場合にドライバと通信するには、C でインポートできる `ioctl()` 関数を使います。

```c
#include <sys/ioctl.h>

// [...]

ioctl(fd, 0x100, 0x12345678);    // data は文字列
```

そして、`file_operations` 構造体も更新する必要があります。

```c
static struct file_operations fops = {
    .ioctl = ioctl_handler
};
```

最近の Linux カーネルでは、[`.ioctl` は削除され、`.unlocked_ioctl` と `.compat_ioctl` に置き換えられました](https://lwn.net/Articles/119652/)。前者が `.ioctl` の後継で、後者は 32 ビットのプロセスが 64 ビットシステム上で `ioctl` を呼べるようにするものです。そのため、新しい `file_operations` は、次のような形になることが多いでしょう。

```c
static struct file_operations fops = {
    .compat_ioctl = ioctl_handler,
    .unlocked_ioctl = ioctl_handler
};
```
