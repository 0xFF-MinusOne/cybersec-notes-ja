# Pwntools, PIE and ROP

[pwntools の ELF のチュートリアル](../../../misc/pwntools/elf.md)で示したように、pwntools には、エクスプロイトを本当に動的にできる機能が数多くあります。`elf.address` を設定するだけで、すべての関数とシンボルのアドレスが自動的に更新されます。そのため、`readelf` などのコマンドラインツールを使う心配はなく、すべてを動的に受け取れます。

さらに、[ROP の機能](https://ironstone.gitbook.io/notes/pwntools/rop)も非常に強力です。
