---
description: ROP に対抗する Arm のハードウェア保護
---

# Pointer Authentication

## Overview

Pointer Authentication は、ROP 攻撃から守るために Arm デバイスで利用できるハードウェア機能です。与えられたポインタの値から **Pointer Authentication Code**(PAC)が生成され、ポインタを使う前に、これを使って検証しなければなりません。この保護には **ハードウェアのサポート** が必要です。必要となるアセンブリ命令([`paciasp`](https://developer.arm.com/documentation/ddi0602/2024-03/Base-Instructions/PACIA--PACIA1716--PACIASP--PACIAZ--PACIZA--Pointer-Authentication-Code-for-Instruction-address--using-key-A-) や [`retaa`](https://developer.arm.com/documentation/ddi0602/2025-12/Base-Instructions/RETAA--RETAB--Return-from-subroutine--with-pointer-authentication-) など)がプロセッサ上に存在していなければならないためです。加えて、**コンパイラのサポート** も必要です。

PAC には Key A と Key B という2つの鍵があります。命令 `paciasp` は、Key A と SP レジスタを使ってリンクレジスタ(Link Register, `lr`)に署名します。これは、(リターンポインタを保存するために)関数の入口でよく使われます。`pacibsp` も同じことをしますが、Key B を使います。

関数の終了時に LR がスタックから pop されるときは、代わりに `retaa` 命令を使います。この命令は、Key A と SP を使って LR 内のアドレスを認証し、認証されたアドレスへ分岐します。Key B の場合は、代わりに `retab` を使います。
