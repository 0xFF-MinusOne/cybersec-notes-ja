---
description: A more in-depth look into parameters for 32-bit and 64-bit programs
---

# Calling Conventions

## パラメータが 1 つの場合

{% file src="../../../.gitbook/assets/calling-conventions-one-param.zip" caption="Calling Conventions - One Parameter" %}

## ソース

まずソースを軽く見てみましょう。

```c
#include <stdio.h>

void vuln(int check) {
    if(check == 0xdeadbeef) {
        puts("Nice!");
    } else {
        puts("Not nice!");
    }
}

int main() {
    vuln(0xdeadbeef);
    vuln(0xdeadc0de);
}
```

とても単純です。

32-bit 版と 64-bit 版のどちらを実行しても、同じ出力になります。

```text
Nice!
Not nice!
```

予想どおりです。

### 32-bit の解析

バイナリを radare2 で開いて、逆アセンブルしてみましょう。

```text
$ r2 -d -A vuln-32
$ s main; pdf

0x080491ac      8d4c2404       lea ecx, [argv]
0x080491b0      83e4f0         and esp, 0xfffffff0
0x080491b3      ff71fc         push dword [ecx - 4]
0x080491b6      55             push ebp
0x080491b7      89e5           mov ebp, esp
0x080491b9      51             push ecx
0x080491ba      83ec04         sub esp, 4
0x080491bd      e832000000     call sym.__x86.get_pc_thunk.ax
0x080491c2      053e2e0000     add eax, 0x2e3e
0x080491c7      83ec0c         sub esp, 0xc
0x080491ca      68efbeadde     push 0xdeadbeef
0x080491cf      e88effffff     call sym.vuln
0x080491d4      83c410         add esp, 0x10
0x080491d7      83ec0c         sub esp, 0xc
0x080491da      68dec0adde     push 0xdeadc0de
0x080491df      e87effffff     call sym.vuln
0x080491e4      83c410         add esp, 0x10
0x080491e7      b800000000     mov eax, 0
0x080491ec      8b4dfc         mov ecx, dword [var_4h]
0x080491ef      c9             leave
0x080491f0      8d61fc         lea esp, [ecx - 4]
0x080491f3      c3             ret
```

`sym.vuln` の呼び出しをよく見ると、パターンがあります。

```text
push 0xdeadbeef
call sym.vuln
[...]
push 0xdeadc0de
call sym.vuln
```

関数を呼ぶ前に、パラメータをそのままスタックに `push` しています。`sym.vuln` にブレークポイントを置きましょう。

```text
[0x080491ac]> db sym.vuln
[0x080491ac]> dc
hit breakpoint at: 8049162
[0x08049162]> pxw @ esp
0xffdeb54c      0x080491d4 0xdeadbeef 0xffdeb624 0xffdeb62c
```

最初の値は、前に説明した**リターンポインタ**です。2 つ目がパラメータです。リターンポインタは `call` の間に push されるので、スタックの先頭にあるのは自然なことです。では `sym.vuln` を逆アセンブルしましょう。

```text
┌ 74: sym.vuln (int32_t arg_8h);
│           ; var int32_t var_4h @ ebp-0x4
│           ; arg int32_t arg_8h @ ebp+0x8
│           0x08049162 b    55             push ebp
│           0x08049163      89e5           mov ebp, esp
│           0x08049165      53             push ebx
│           0x08049166      83ec04         sub esp, 4
│           0x08049169      e886000000     call sym.__x86.get_pc_thunk.ax
│           0x0804916e      05922e0000     add eax, 0x2e92
│           0x08049173      817d08efbead.  cmp dword [arg_8h], 0xdeadbeef
│       ┌─< 0x0804917a      7516           jne 0x8049192
│       │   0x0804917c      83ec0c         sub esp, 0xc
│       │   0x0804917f      8d9008e0ffff   lea edx, [eax - 0x1ff8]
│       │   0x08049185      52             push edx
│       │   0x08049186      89c3           mov ebx, eax
│       │   0x08049188      e8a3feffff     call sym.imp.puts           ; int puts(const char *s)
│       │   0x0804918d      83c410         add esp, 0x10
│      ┌──< 0x08049190      eb14           jmp 0x80491a6
│      │└─> 0x08049192      83ec0c         sub esp, 0xc
│      │    0x08049195      8d900ee0ffff   lea edx, [eax - 0x1ff2]
│      │    0x0804919b      52             push edx
│      │    0x0804919c      89c3           mov ebx, eax
│      │    0x0804919e      e88dfeffff     call sym.imp.puts           ; int puts(const char *s)
│      │    0x080491a3      83c410         add esp, 0x10
│      │    ; CODE XREF from sym.vuln @ 0x8049190
│      └──> 0x080491a6      90             nop
│           0x080491a7      8b5dfc         mov ebx, dword [var_4h]
│           0x080491aa      c9             leave
└           0x080491ab      c3             ret
```

ここではコマンドの出力を**全部**載せています。関係する部分が多いためです。`radare2` はローカル変数の検出がとても得意で、上のほうにあるように `arg_8h` という変数が見つかっています。これが後で `0xdeadbeef` と比較されています。

```text
cmp dword [arg_8h], 0xdeadbeef
```

明らかに、これが私たちのパラメータです。

つまり、パラメータが 1 つのとき、パラメータはスタックに push され、スタックは次のようになります。

```text
return address        param_1
```

### 64-bit の解析

ここでもう一度 `main` を逆アセンブルします。

```text
0x00401153      55             push rbp
0x00401154      4889e5         mov rbp, rsp
0x00401157      bfefbeadde     mov edi, 0xdeadbeef
0x0040115c      e8c1ffffff     call sym.vuln
0x00401161      bfdec0adde     mov edi, 0xdeadc0de
0x00401166      e8b7ffffff     call sym.vuln
0x0040116b      b800000000     mov eax, 0
0x00401170      5d             pop rbp
0x00401171      c3             ret
```

ほほう、今度は違いますね。前に述べたとおり、パラメータは `rdi` に移されます(ここでの逆アセンブルでは `edi` と表示されていますが、`edi` は `rdi` の下位 32 ビットにすぎず、パラメータも 32 ビットしかないため、`EDI` と表示されます)。再び `sym.vuln` にブレークポイントを置けば、次のコマンドで `rdi` を確認できます。

```text
dr rdi
```

{% hint style="info" %}
`dr` だけを実行すると、すべてのレジスタが表示されます
{% endhint %}

```text
[0x00401153]> db sym.vuln 
[0x00401153]> dc
hit breakpoint at: 401122
[0x00401122]> dr rdi
0xdeadbeef
```

いいですね。

{% hint style="info" %}
パラメータにはレジスタが使われますが、戻りアドレスは引き続きスタックに push されます。ROP では、関数のアドレスのすぐ後ろに置きます
{% endhint %}

## パラメータが複数の場合

{% file src="../../../.gitbook/assets/calling-convention-multi-param.zip" caption="Calling Conventions - Multiple Parameters" %}

### ソース

```c
#include <stdio.h>

void vuln(int check, int check2, int check3) {
    if(check == 0xdeadbeef && check2 == 0xdeadc0de && check3 == 0xc0ded00d) {
        puts("Nice!");
    } else {
        puts("Not nice!");
    }
}

int main() {
    vuln(0xdeadbeef, 0xdeadc0de, 0xc0ded00d);
    vuln(0xdeadc0de, 0x12345678, 0xabcdef10);
}
```

### 32-bit

ほぼ同じバイナリの_完全な_逆アセンブルはすでに見たので、重要な部分だけを取り出します。

```text
0x080491dd      680dd0dec0     push 0xc0ded00d
0x080491e2      68dec0adde     push 0xdeadc0de
0x080491e7      68efbeadde     push 0xdeadbeef
0x080491ec      e871ffffff     call sym.vuln
[...]
0x080491f7      6810efcdab     push 0xabcdef10
0x080491fc      6878563412     push 0x12345678
0x08049201      68dec0adde     push 0xdeadc0de
0x08049206      e857ffffff     call sym.vuln
```

こちらも単純で、渡す順序とは逆の順に `push` します。`db sym.vuln` を実行してスタックを表示すると、この逆順が役に立ちます。

```text
[0x080491bf]> db sym.vuln
[0x080491bf]> dc
hit breakpoint at: 8049162
[0x08049162]> pxw @ esp
0xffb45efc      0x080491f1 0xdeadbeef 0xdeadc0de 0xc0ded00d
```

これで、パラメータが増えたときにスタックにどう置かれるかが、かなりはっきりしました。

```text
return pointer        param1        param2        param3        [...]        paramN
```

### 64-bit

```text
0x00401170      ba0dd0dec0     mov edx, 0xc0ded00d
0x00401175      bedec0adde     mov esi, 0xdeadc0de
0x0040117a      bfefbeadde     mov edi, 0xdeadbeef
0x0040117f      e89effffff     call sym.vuln
0x00401184      ba10efcdab     mov edx, 0xabcdef10
0x00401189      be78563412     mov esi, 0x12345678
0x0040118e      bfdec0adde     mov edi, 0xdeadc0de
0x00401193      e88affffff     call sym.vuln
```

このように、`rdi` に加えて `rdx` と `rsi` にも値を入れます(ここでは、それぞれの下位 32 ビットです)。

## 64-bit の大きな値

実際に使われるのは `edi` ではなく、最終的には `rdi` であることを示すために、元の 1 パラメータのコードを、もっと大きな数を使うように書き換えます。

```c
#include <stdio.h>

void vuln(long check) {
    if(check == 0xdeadbeefc0dedd00d) {
        puts("Nice!");
    }
}

int main() {
    vuln(0xdeadbeefc0dedd00d);
}
```

`main` を逆アセンブルすると、次のようになります。

```text
movabs rdi, 0xdeadbeefc0ded00d
call sym.vuln
```

{% hint style="info" %}
`movabs` は、64-bit の `mov` 命令をエンコードするのに使われます。`mov` と同じものとして扱って構いません。
{% endhint %}



