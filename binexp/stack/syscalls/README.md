---
description: Interfacing directly with the kernel
---

# Syscalls

### 概要

**syscall** は **sys**tem **call**(システムコール)の略で、プロセスの作成や I/O など、カーネルレベルのアクセスが必要な特定の処理を行うために、プログラムがカーネルに入る方法です。

[syscall の一覧](https://chromium.googlesource.com/chromiumos/docs/+/master/constants/syscalls.md)を眺めると、`open()`、`fork()`、`read()` など、libc の関数に似た syscall があることに気づくでしょう。これは、それらの関数が syscall の_ラッパー_にすぎず、プログラマにとって使いやすくしているからです。

### syscall の呼び出し

Linux では、syscall は `int80` 命令で呼び出されます。呼び出されると、カーネルは RAX に格納された値を確認します。これは**syscall 番号**で、**どの syscall を実行するか**を決めます。表にあるように、他のパラメータは RDI、RSI、RDX などに格納でき、各パラメータの意味は syscall ごとに異なります。

### execve

注目すべき syscall が `execve` で、RDI に渡されたプログラムを実行します。RSI と RDX には、それぞれ `arvp` と `envp` が入ります。

つまり、`system()` 関数がなくても、代わりに `execve` で `/bin/sh` を呼び出せます。必要なのは、RDI に `/bin/sh` へのポインタを渡し、RSI と RDX に `0` を入れることだけです(シェルを起動するには `argv` と `envp` の両方が `NULL` である必要があるためです)。

