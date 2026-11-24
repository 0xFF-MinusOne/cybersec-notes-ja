---
description: Supervisor Memory Access Protection
---

# SMAP

SMAP は SMEP をより強力にしたものです。ユーザー空間にあるコードの実行を防ぐだけでなく、SMAP はデータへのアクセスであっても、ユーザー空間へのアクセス自体に **厳しい** 制限をかけます。SMAP は、ごく限られた特定の関数を除き、カーネル空間にないデータを _デリファレンス_(つまり _アクセス_)することすらカーネルに許しません。

例えば、SMAP が有効な場合、`strcpy` や `memcpy` のような関数ではユーザー空間との間でデータをコピーできません。代わりに `copy_from_user` と `copy_to_user` という関数が用意されていて、これらは動作している間だけ一時的に SMAP を回避することが許されています。これらの関数には、バッファオーバーフローなどの攻撃に対する追加の防御もあり、関数 `__copy_overflow` がそれらを防ぐガードとして働きます。

つまり、`write`/`read` でも `ioctl` でも、ポインタ経由で渡した構造体は、操作される前にこれらの関数ですべてカーネル空間にコピーされます。また、すべての操作は `copy_from_user` が呼ばれた時点でモジュールが取ったデータのスナップショットに基づくため(同じ構造体に対して `copy_from_user` が複数回呼ばれる場合を除く)、double-fetch はさらに起こりにくくなります。

SMEP と同様、SMAP は CR4 レジスタで制御され、この場合は 21 ビット目です。これも[ピン留め(pinned)](smep/kernel-rop-disabling-smep.md#failure)されているので、CR4 を上書きしても何も起こらず、代わりに回避策を考える必要があります。決まった「バイパス」はなく、問題ごとに異なり、単純に考慮に入れる必要があります。

SMAP の有効化は SMEP と同じくらい簡単です。

```
    -cpu qemu64,+smep,+smap
```

逆に _無効_ にする必要がある場合は、オプションは `nosmap` です。

### Stac and Clac Instructions

TODO

### Putting Exploit Data Into Kernel Memory instead of Userspace

TODO
