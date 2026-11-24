---
description: 関数のハイジャック
---

# GOT Overwrite

GOT には `libc` 内の関数の実際のアドレスが格納されていることを覚えているでしょうか。であれば、そのエントリを上書きできれば、それによってコード実行を得られます。次のコードを考えてみましょう。

```c
char buffer[20];
gets(buffer);
printf(buffer);
```

ここにはバッファオーバーフロー(buffer overflow)とフォーマット文字列(format string)の脆弱性の両方があります。さらに、そのフォーマット文字列を使って `printf` の GOT エントリを `system` のアドレスで上書きしたとします。すると、コードは実質的に次のようになります。

```c
char buffer[20];
gets(buffer);
system(buffer);
```

ちょっとまずいですよね。そうです、入力がそのまま `system` に渡されてしまいます。
