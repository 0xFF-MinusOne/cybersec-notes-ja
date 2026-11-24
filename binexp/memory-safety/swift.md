---
description: >-
  Swift は純粋に ARC だけを使います。トレーシングガベージコレクタがない場合に生じる問題を、どのように解決しているのでしょうか?
---

# Swift

## 循環参照の解決(Fixing Reference Cycles)

Swift には、循環参照(reference cycle)が見つかったときに解決を助ける 2 つのキーワードがあります。ひとつ目は `weak` で、参照カウントを増やさず、参照先のインスタンスが解放(deallocate)されると `nil` になります。そのため `weak` 参照は nullable でなければなりません。

2 つ目のキーワードは `unowned` です。`weak` と同様に強参照(strong reference)を作りませんが、nullable にはできません。参照先のオブジェクトが解放されたあとに unowned 参照を使うと、アプリはクラッシュします。

まとめると、循環参照を見つけて直す責任は開発者に委ねられています。

## マルチスレッドが原因の競合の解決(Fixing Races caused by Multi-Threading)

Swift では、複数のスレッドから同時にアクセスされ得るオブジェクトへのアクセスを同期させる必要があります。これは、**競合する**操作が**順序付け**され、同時ではなく一つずつ実行されるという意味です。そのために、データ競合を防ぐ目的でアクセスを直列化するクラスである [Actor](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/#Actors) と、ある型がスレッド間(より正確には**並行ドメイン(concurrency domain)**間)で安全に送れることを Swift に知らせる型特性(trait)である [`Sendable`](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/#Sendable-Types) を使います。

ただし、Swift は不正なアクセスを**禁止**するわけではなく、並行処理モデルに従わない場合は**未定義(undefined)**として扱います。たとえば、次のコードはコンパイルできてしまいます。

```swift
class Box {
    var value = 0
}

let box = Box()

DispatchQueue.global().async {
    box.value += 1
}

DispatchQueue.global().async {
    box.value += 1
}
```
