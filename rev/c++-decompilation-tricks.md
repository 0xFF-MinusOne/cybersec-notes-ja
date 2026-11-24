---
description: デコンパイラの出力の読み方
---

# C++ Decompilation Tricks

ここで紹介するコツには Binary Ninja 向けのメモも含まれますが、IDA でも似た表示になります(Ghidra でもおそらく同様です)。

コード例です。

```cpp
char rax_3 = *std::vector<uint8_t>::operator[](&vector, sx.q(j))
*std::vector<uint8_t>::operator[](&vector, sx.q(j)) = *std::string::operator[](arg1, other: j) ^ rax_3
```

非常に奇妙で圧倒されそうに見えますが、単語をよく見てください。`std::vector<uint8_t>::operator[]` は文字どおり演算子 `[]`、つまり添字演算子(subscript operator)を意味します。第 1 引数の添字を取り出すもので、第 2 引数がその添字の値です。したがって、

```cpp
std::vector<uint8_t>::operator[](&vector, sx.q(j))
```

は、実際には単に次の意味です。

```cpp
vector[j]
```

また、意味が通らないときは、型を変更して引数を追加してみてください。自動検出の精度はかなり低いので、大きく役立つことがあります。

網羅的ではありませんが、一覧は次のとおりです。

<table data-full-width="true"><thead><tr><th>デコンパイル結果</th><th>意味</th><th>引数</th></tr></thead><tbody><tr><td><code>std::T::~T</code></td><td>クラス <code>T</code> のデストラクタ(destructor)</td><td><code>T*</code></td></tr><tr><td><code>std::vector&#x3C;T>::operator[](&#x26;vector, sx.q(j))</code></td><td><code>vector[j]</code></td><td><code>T*</code>, <code>int64_t</code></td></tr><tr><td></td><td></td><td></td></tr></tbody></table>
