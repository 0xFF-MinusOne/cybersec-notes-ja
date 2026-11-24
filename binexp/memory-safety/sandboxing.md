# サンドボックス(Sandboxing)

サンドボックスは、信頼できないコードを実行するためのセキュリティ機構です。目的は、最小限の権限しか持たない、厳しく制限された閉じた環境を作ることで、これはオペレーティングシステムのポリシーによって強制されます。

サンドボックスの内側では、ファイル、ネットワーク、デバイス、ユーザー、他のプロセスといった機密性の高いリソースへのアクセスが制限されます。これは「[多層防御(defence in depth)](https://www.fortinet.com/uk/resources/cyberglossary/defense-in-depth)」という考え方の重要な部分で、最善を尽くしても脆弱性は生じ得ると認めたうえで、そうした脆弱性の影響をできる限り小さく抑えるものです。

## Linux

Linux にはカーネルが提供する機能がいくつかあります。[Chromium](https://chromium.googlesource.com/chromium/src/+/0e94f26e8/docs/linux_sandboxing.md#user-namespaces-sandbox) は[名前空間(namespaces)](https://man7.org/linux/man-pages/man7/namespaces.7.html)と [seccomp-bpf](https://www.kernel.org/doc/html/v4.19/userspace-api/seccomp_filter.html) を使っています。

### 名前空間(Namespaces)

man ページから引用します。

> 名前空間は、グローバルなシステムリソースを抽象化で包み、その名前空間内のプロセスから見ると、そのグローバルリソースの独立した専用のインスタンスを持っているように見せます。グローバルリソースへの変更は、その名前空間のメンバーである他のプロセスからは見えますが、それ以外のプロセスからは見えません。

要するに、名前空間はカーネルが提供する機能で、名前空間内のものが、その外にあるファイル、プロセス、ネットワーク、ユーザーなどにアクセスすることを防ぎます。これにより、名前空間内のプロセスが名前空間の_外_のものに影響を与えることを止められます。

### seccomp-bpf

**Seccomp** はシステムコールをフィルタリングして許可したものだけを通します。これにより、攻撃者がコード実行を得たとしても、できることを減らせます。
