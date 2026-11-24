---
description: Kernel Page Table Isolation
---

# KPTI

[KPTI ](https://www.kernel.org/doc/html/next/x86/pti.html)は、ユーザー空間とカーネル空間でアドレス空間が共有されていることを悪用する攻撃から守るために設計されています。もとは KAISER と呼ばれ、[Meltdown](https://meltdownattack.com/) 型のマイクロアーキテクチャ脆弱性を防ぐために作られた緩和策です。

KPTI は、ユーザー空間とカーネル空間のページテーブル(page table)を分離して、2 組のページテーブルを作ります。

* カーネルが使う 1 組目には、`copy_to_user()` などのためにカーネルが使えるよう、ユーザー空間の完全なマッピングが含まれます。このページテーブルでは、ユーザー空間のメモリに NX ビットが設定されています。
* ユーザー用の組は、マッピングするカーネル仮想メモリを可能な限り最小限にします(例えば、例外ハンドラや、ユーザーがカーネルへ移行するために必要なコードなど)。

コマンドラインから `nopti` 引数を付けると、KPTI を無効にできます。CPU が Meltdown の影響を受けない場合も、自動的に無効になります。

### Consequences and Bypasses

ユーザーコンテキストにいるとき、カーネルは完全にはマップされていません。私たちのエクスプロイトの多くはカーネルモードで実行されるので、これはほとんど影響しません。

しかし、カーネルモードにいるとき、ユーザー空間は実行不可としてマップされています。つまり、`iretq` で[私たちが定義した](../../types/kernel/kernel-rop-ret2usr.md) `escalate()` 関数にリターンすることはできません。解決策は、ページテーブルをユーザー用に切り替え直すことです。

そのために、`swapgs_restore_regs_and_return_to_usermode` という、名前そのままの便利な関数を悪用できます。これを逆アセンブルする(TODO!)と、最初に大量の `pop` 命令があり、その後にいくつかの `mov` と `push`、そしてページテーブルの切り替えと `swapgs`、`iretq` が続くことが分かります。`pop` 命令の _後_ にジャンプすれば、それらを埋める手間を省けます。これは一般に **KPTI トランポリン(KPTI Trampoline)** と呼ばれます。

TODO example

### Bypassing KPTI via a SIGSEGV Handler

ページテーブルを切り替えずに `iretq` でユーザーモードに戻ろうとすると、ユーザー空間にいるので、カーネルクラッシュではなく SIGSEGV になります。

そこで別の方法として、SIGSEGV ハンドラを使えます。エクスプロイトで root 権限を得た後、ユーザーランドにアクセスしようとして SIGSEGV を発生させます。カーネルのフォールトハンドラは、ハンドラへ処理を振り分けるときにページテーブルを切り替えてくれます。良い例は[こちら](https://trungnguyen1909.github.io/blog/post/matesctf/KSMASH/)にあります。

TODO example
