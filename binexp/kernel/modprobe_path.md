---
description: シェルを取る簡単な方法
---

# Overwriting modprobe\_path

カーネルは、実行時にカーネルモジュールの読み込みを要求できます。そのとき、[`request_module`](https://elixir.bootlin.com/linux/v6.16/source/kernel/module/kmod.c#L115) を呼び出そうとし、これが [`call_modprobe`](https://elixir.bootlin.com/linux/v6.16/source/kernel/module/kmod.c#L71) を使って `modprobe` ツールを起動します。`modprobe` は root 権限で動作するユーザー空間のプログラムで、必要なカーネルモジュールのバイナリをファイルシステム上から探して読み込みます。

`modprobe` のパスは、カーネルのグローバル変数である `modprobe_path` に入っています。この値は、root ではないユーザーでも `/proc/sys/kernel/modprobe` から読めます。既定値は `/sbin/modprobe` です。

`modprobe_path` を別のバイナリ(例えば `/tmp/exec`)で上書きできれば、それが root 権限で実行されます。これは **非常に** 簡単です。modprobe を起動する最も簡単な方法は、未知のシグネチャを持つバイナリを実行することです。

```bash
echo -e '\xff\xff\xff\xff' > /tmp/fake
chmod +x /tmp/fake
/tmp/fake
```

シグネチャを処理するためにどのプログラムを実行すべきかを判断するため、カーネルは [`binfmt`](https://elixir.bootlin.com/linux/v6.1/source/fs/exec.c#L1742) を使います(新しいバージョンではコードが少し異なります)。これは `request_module` から呼ばれますが、シグネチャには[少なくとも 1 文字、表示できない文字が含まれていなければなりません](https://elixir.bootlin.com/linux/v6.1/source/fs/exec.c#L1739)。

したがって、手順は単純です。まず、次のソースで `/tmp/hijack` をコンパイルします。

```c
int main()
{
    system("cp /usr/bin/sh /tmp/sh");
    system("chown root:root /tmp/sh");
    system("chmod 4755 /tmp/sh");
}
```

ペイロードは数多く考えられますが、最終的な結果は同じです。これは `/bin/sh` を `/tmp/sh` にコピーして SUID を付けます。次に、未知のシグネチャを持つファイルを作ります。

```
echo -n -e '\xff\xff\xff\xff' > /tmp/fake
chmod +x /tmp/fake
```

最後に、`modprobe_path` を `/tmp/hijack` に上書きします。通常ユーザーとして `/tmp/fake` を実行すると、カーネルが `/tmp/hijack` を root 権限で起動し、実行してくれます。

## Example

TODO
