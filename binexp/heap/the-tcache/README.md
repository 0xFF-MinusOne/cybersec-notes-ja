---
description: 新しく効率的なヒープ管理
---

# The Tcache

[glibc 2.27](https://elixir.bootlin.com/glibc/glibc-2.27/source/malloc/malloc.c) から、**tcache** という新しいヒープの機能が導入されました。tcache は性能向上を目的に設計されており、動作はとても単純です。すべてのチャンクサイズ(**0x410** まで)がそれぞれ専用の **tcache bin** を持ち、最大 **7 個のチャンク**を保持できます。特定のサイズのチャンクを確保するときは、まず tcache bin が検索されます。解放されるときは、チャンクは tcache bin に追加され、満杯であれば通常の fastbin / unsortedbin に入ります。

tcache bin は fastbin のように動作し、特定のサイズの解放済みチャンクの単方向リンクリストです。`fd` ポインタを使ったリストの扱いも同じです。想像できるとおり、tcache への攻撃も fastbin への攻撃とよく似ています。

皮肉なことに、[double free 対策](../../../types/heap/double-free/double-free-protections.md)をはじめ、fastbin に長年にわたって実装されてきた防御は、tcache の最初の実装では無視されていました。つまり、glibc 2.27 で動くバイナリをヒープで攻撃するほうが、2.25 で動くバイナリを攻撃するよりも簡単なのです。
