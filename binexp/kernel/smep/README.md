---
description: Supervisor Memory Execute Protection
---

# SMEP

[ret2usr ](../../../types/kernel/kernel-rop-ret2usr.md)が ret2shellcode に相当するなら、SMEP は新しい [NX](../../stack/no-execute.md) です。SMEP は原始的な保護機構で、[カーネルモードで実行されるコードがすべてカーネル空間にあること](https://wiki.osdev.org/Supervisor_Memory_Protection)を保証します。これはページテーブルの User/Supervisor ビットに基づいて行われます。つまり、自分のシェルコードに単純に ROP で戻る方法はもう通用しません。SMEP を回避するには、(ユーザーランドのコードに切り替えずに)カーネル内にあるガジェットを使って目的を達成する必要があります。

古いカーネルバージョンでは、[ROP で SMEP を完全に無効化](kernel-rop-disabling-smep.md)できましたが、これはパッチで塞がれました。これが可能だったのは、SMEP が [CR4 レジスタの 20 ビット目](https://wiki.osdev.org/CPU_Registers_x86#CR4)で決まるためで、CR4 を制御できれば、SMEP がエクスプロイトの邪魔をしないよう無効化できたのです。

対応する QEMU のフラグを制御することで、カーネルで SMEP を有効にできます(`qemu64` に特に意味はありません)。

```
    -cpu qemu64,+smep
```

既定で有効になっていることもあり、その場合は `nosmep` を使う必要があります。
