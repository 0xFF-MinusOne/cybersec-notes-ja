# その他の bin の動作

fastbin サイズではないチャンクを解放すると、そのチャンクは Unsorted Bin に入ります。新しくチャンクが**要求**されると、glibc はすべての bin を調べます。

* 要求サイズが fastbin サイズであれば、[対応する fastbin を確認します](https://elixir.bootlin.com/glibc/glibc-2.3.6/source/malloc/malloc.c#L3849)
  * チャンクがあれば、それを返します
* 要求サイズが small bin サイズであれば、[対応する small bin を確認します](https://elixir.bootlin.com/glibc/glibc-2.3.6/source/malloc/malloc.c#L3868)
  * チャンクがあれば、それを返します
* 要求されたチャンクが大きい(largebin サイズ)場合は、まず [`malloc_consolidate()`](../malloc_consolidate.md) で [largebin を統合(consolidate)します](https://elixir.bootlin.com/glibc/glibc-2.3.6/source/malloc/malloc.c#L3897)。この仕組みは後で詳しく扱いますが、要するに先ほどの説明は嘘でした。fastbin も統合**される**のです。ただし、解放時ではありません。
* 最後に、unsorted bin 内のチャンクを順にたどります
  * unsorted bin が空であれば、[top chunk を分割して](../the-top-chunk-and-remainder.md)ヒープを拡張することで要求に応えます。このとき、小さくなった top chunk はより高いメモリアドレスから始まる形になります
* 要求サイズが bin 内のチャンクのサイズと等しければ、そのチャンクを返します
* 小さければ、bin 内のチャンクを 2 つに分割し、適切なサイズの部分を返します
* 大きければ、[fastbin を統合します](https://elixir.bootlin.com/glibc/glibc-2.3.6/source/malloc/malloc.c#L3897)。その結果、要求を満たせるだけの大きさの解放済みチャンクができているかもしれません
  * できていなければ、あらためて [top chunk を分割して](../the-top-chunk-and-remainder.md)要求に応え、小さくなった top chunk をより高いメモリアドレスから始まる形にします

忘れやすく、少し直感に反するのが、_確保_ 時に起きることと _解放_ 時に起きることの違いです。たとえば、fastbin の統合は確保をきっかけに起こります。
