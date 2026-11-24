---
description: シェルコードに対する防御
---

# No eXecute

想像がつくとおり、プログラマたちは、他人が自分のプログラムに勝手に命令を注入できることをまったく歓迎しませんでした。NX ビット(No eXecute の略)は、メモリ領域を **命令** か **データ** のどちらかとして定義します。これにより、入力は **データ** として保存され、それを命令として実行しようとするとプログラムがクラッシュするため、シェルコードは事実上無力化されます。

NX を回避するために、エクスプロイト開発者は **ROP**(Return-Oriented Programming)という手法を使う必要があります。

{% hint style="info" %}
Windows における NX に相当するものは DEP で、**D**ata **E**xecution **P**revention の略です
{% endhint %}

#### Checking for NX

pwntools の `checksec` か `rabin2` のどちらかを使えます。

```text
$ checksec vuln
[*] 'vuln'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      No PIE (0x8048000)
    RWX:      Has RWX segments
```

```text
$ rabin2 -I vuln
[...]
nx       false
[...]
```
