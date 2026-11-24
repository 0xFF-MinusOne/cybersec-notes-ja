---
description: 自動メモリ管理に対する Apple の好むアプローチ
---

# Automatic Reference Counting

## Overview

[C++ Smart Pointers](../c++-smart-pointers.md) のセクションを読んだなら、ARC はほとんど理解できています。Swift のように ARC が唯一のメモリ管理手段として使われる言語では、事実上すべてのクラスインスタンスが `shared_ptr` として扱われます。公式ドキュメントは[こちら](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/)です。

公式の説明では、クラスインスタンスがプロパティ、定数、変数に代入されるたびに、そのインスタンスへの **強い参照(strong reference)** が作られます。この参照が「強い」と呼ばれるのは、そのような参照が 1 つでも存在する限り、インスタンスを解放できないからです。これらのプロパティ、定数、変数が、生存期間の終わりに達したり再代入されたりして参照を失うたびに、クラスインスタンスの参照カウンタは減ります。ゼロになると、インスタンスは解放されます。

## Drawback: Reference Cycles

ARC の欠点の 1 つが **循環参照(reference cycle)**(**retain cycle** とも呼ばれます)という問題で、2 つのクラスインスタンスが互いへの強い参照を持つ状態です。最小限の例は次のとおりです。

```swift
class A {
    var b: B?
}

class B {
    var a: A?
}

let a = A()
let b = B()
a.b = b
b.a = a
```

ここで、`A` のインスタンスは 2 つの強い参照(`a` と `b.a`)を持ち、`B` のインスタンスも 2 つの強い参照(`b` と `a.b`)を持っていることに注意してください。

`a` と `b` がスコープを抜けると、`A` と `B` のインスタンスへの強い参照は消え、両方のインスタンスの参照カウントは `1` に減ります。しかし `a.b` と `b.a` はまだそれぞれ `A` と `B` のインスタンスを指しているため、インスタンスは自動的には解放されません。さらに、`a.b` と `b.a` にはもうアクセスできないのに、強い参照が残っているため、解放されることは **決してありません**。これはメモリリークにつながり、ARC の主な欠点の 1 つです。

## Drawback: Multi-threading

プログラムがマルチスレッドの場合、あるスレッドが使っているオブジェクトを別のスレッドが削除してしまう可能性があるため、参照カウントはメモリ安全でない実行につながることがあります。この問題は、ガベージコレクションを使うプログラミング言語では起こりません。

## Uses of ARC

純粋に ARC だけを使うプログラミング言語は非常にまれで、Apple の言語である Objective-C と Swift だけがそうしています。

Python は[参照を数えます](https://docs.python.org/3/glossary.html#term-reference-count)が、循環参照を検出して断ち切るための[ガベージコレクタも持っています](https://docs.python.org/3/glossary.html#term-garbage-collection)。Python 3.13 までは、[グローバルインタプリタロック(Global Interpreter Lock)](https://blog.jetbrains.com/pycharm/2025/07/faster-python-unlocking-the-python-global-interpreter-lock/)(GIL)のせいで Python のマルチスレッドは実際にはすべて 1 つのスレッドで動いており、これがマルチスレッドのレースコンディションを打ち消していました。GIL の削除に伴い、この問題を解決するために[追加の作業](https://peps.python.org/pep-0703/)が必要になりました。
