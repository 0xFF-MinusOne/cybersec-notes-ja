---
description: 独自に libc の関数を解決する
---

# ret2dlresolve

## Broad Overview

ret2dlresolve では、攻撃者はバイナリをだまして、選んだ関数(`system` など)を PLT に解決させます。これにより攻撃者は、その PLT 関数を、もともとバイナリの一部だったかのように使え、(存在する場合は)ASLR を回避でき、libc のリークも不要になります。

## Detailed Overview

動的にリンクされた ELF オブジェクトは、PLT と GOT を使って、`libc` の関数を最初に呼ばれたときにインポートします。実行時のシンボルの再配置(relocation)の際に、RIP は PLT にジャンプし、シンボルを解決しようとします。この過程で「リゾルバ(resolver)」が呼び出されます。

{% hint style="info" %}
以下のスクリーンショットではすべて、`read@plt` で停止させています。表示が少し見やすいので、`pwndbg` プラグイン付きの GDB を使っています。
{% endhint %}

![](<../../../.gitbook/assets/image (41).png>)

PLT は、GOT が指す先へジャンプします。GOT が更新される前は、最初は PLT 内の `jmp` の次の命令を指し戻しており、それによって解決が行われます。

![](<../../../.gitbook/assets/image (35).png>)

関数を解決するには、バイナリ内に3つの構造体が存在する必要があります。この3つの構造体を偽造すれば、リンカをだまして選んだ関数を解決させられ、解決後には(`/bin/sh` などの)パラメータも渡せます。

## Structures

偽造する必要のある構造体は3つあります。

```
$readelf -d source

Dynamic section at offset 0x2f14 contains 24 entries:
  Tag        Type                         Name/Value
 0x00000005 (STRTAB)                     0x804825c
 0x00000006 (SYMTAB)                     0x804820c
 0x00000017 (JMPREL)                     0x80482d8
 [...]
```

### JMPREL

`JMPREL` セグメント(`.rel.plt`)には **再配置テーブル(Relocation Table)** が格納されており、各エントリをシンボルに対応づけます。

```
$readelf -r source

Relocation section '.rel.dyn' at offset 0x2d0 contains 1 entry:
 Offset     Info    Type            Sym.Value  Sym. Name
0804bffc  00000206 R_386_GLOB_DAT    00000000   __gmon_start__

Relocation section '.rel.plt' at offset 0x2d8 contains 2 entries:
 Offset     Info    Type            Sym.Value  Sym. Name
0804c00c  00000107 R_386_JUMP_SLOT   00000000   gets@GLIBC_2.0
0804c010  00000307 R_386_JUMP_SLOT   00000000   __libc_start_main@GLIBC_2.0
```

これらのエントリは `Elf32_Rel` 型です。

```c
typedef uint32_t Elf32_Addr;
typedef uint32_t Elf32_Word;
typedef struct
{
  Elf32_Addr    r_offset;               /* Address */
  Elf32_Word    r_info;                 /* Relocation type and symbol index */
} Elf32_Rel;
/* How to extract and insert information held in the r_info field.  */
#define ELF32_R_SYM(val)                ((val) >> 8)
#define ELF32_R_TYPE(val)               ((val) & 0xff)
```

`name` 列はシンボル名に対応します。`offset` はそのシンボルの GOT エントリです。`info` には追加のメタデータが格納されています。

これにより、`gets` の `R_SYM` は `1` になります。`0x107 >> 8 = 1` だからです。

### STRTAB

こちらはもっと単純で、名前用の文字列テーブルにすぎません。

![先ほど取得した STRTAB の位置が 0x0804825c です](<../../../.gitbook/assets/image (36).png>)

### SYMTAB

シンボル情報は、ここに `Elf32_Sym` 構造体として格納されています。

```c
typedef struct 
{ 
   Elf32_Word st_name ; /* Symbol name (string tbl index) */
   Elf32_Addr st_value ; /* Symbol value */ 
   Elf32_Word st_size ; /* Symbol size */ 
   unsigned char st_info ; /* Symbol type and binding */ 
   unsigned char st_other ; /* Symbol visibility under glibc>=2.2 */ 
   Elf32_Section st_shndx ; /* Section index */ 
} Elf32_Sym ;
```

ここで最も重要な値は `st_name` で、**シンボル名の STRTAB 内でのオフセット** を示します。そのほかのフィールドは、エクスプロイト自体には関係ありません。

## Linking the Structures

`JMPREL` から得た `R_SYM` の値と `SYMTAB` を組み合わせれば、シンボルの文字列の `STRTAB` オフセットが得られることが分かりました。

![](<../../../.gitbook/assets/image (40).png>)

ここでは `SYMTAB + R_SYM * size (16)` を読んでおり、そのオフセット(`SYMTAB` の `st_name` 変数)は `0x10` のようです。

![](<../../../.gitbook/assets/image (44).png>)

そして、そのオフセットを `STRTAB` で読むと、シンボルの名前が得られます。

## More on the PLT and GOT

GOT と PLT に戻って、もう少し詳しく見てみましょう。

![](<../../../.gitbook/assets/image (38).png>)

GOT のエントリがまだ設定されていなければ、`reloc_offset` の値を push し、`.plt` セクションの先頭へジャンプします。数命令後に `dl-resolve()` 関数が呼ばれ、`reloc_offset` がその引数の1つになります。そして、この `reloc_offset` を使って、**再配置エントリと symtab エントリ** を計算します。

## Resources

* [The Original Phrack Article](http://phrack.org/issues/58/4.html)
* [0ctf's babystack](https://gist.github.com/ricardo2197/8c7f6f5b8950ed6771c1cd3a116f7e62)
* [rk700 (in Chinese)](http://rk700.github.io/2015/08/09/return-to-dl-resolve/)
