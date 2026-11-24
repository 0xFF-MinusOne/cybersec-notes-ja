# Garbage Collection

ガベージコレクション(Garbage Collection)は **自動メモリ管理** の一種で、(多くの場合)高水準のプログラミング言語が、複雑な手動のメモリ管理を不要にするために使います。その結果、手動のメモリ管理は **実装されておらず**、開発者はメモリの扱いをガベージコレクションに任せることで、[UAF](../../../types/heap/use-after-free.md)や[Double-Free](../../../types/heap/double-free/)のようなバグを防げます。

主な種類は 2 つあります。[トレーシングガベージコレクション(Tracing Garbage Collection)](tracing-garbage-collection.md)(単に「ガベージコレクション」と呼ばれることが多いです)と、[自動参照カウント(Automatic Reference Counting)](automatic-reference-counting.md)です。
