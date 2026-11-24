---
description: メモリ安全性の代表格
---

# Rust

Rust のメモリ安全性は、**所有権(ownership)**と**借用(borrowing)**という 2 つの主要な原則に基づいています。

Rust のすべての値には**所有者(owner)**がいます。つまり、コード上のある時点で、その値の読み書きを制御できるのは**ひとつ**だけです。所有権は一時的に**借用**できますが、これは Rust の**コンパイラ**が追跡しており、所有権のルールに違反するコードは**コンパイルできません**。

これは他のプログラミング言語とは異なるアプローチです。ここまで見てきたとおり、C にはメモリ安全性という概念がありません。Python、Java、C# のような高水準の_マネージド_言語は、メモリ安全性を**ランタイム**で処理します。そのためランタイムが必要になるだけでなく、速度も犠牲になります。

[この記事](https://www.infoworld.com/article/2336661/rust-memory-safety-explained.html)にわかりやすい解説があり、[この Stack Overflow](https://stackoverflow.com/questions/36136201/how-does-rust-guarantee-memory-safety-and-prevent-segmentation-faults) の投稿も参考になります。[このテーマに関する公式ドキュメント](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)も素晴らしい内容です。

### 所有権(Ownership)

次のコードを考えてみます。

```rust
fn main() {
    let original = "Hello, World!".to_string();
    let other = original;
    println!("{}", original);
}
```

他の多くの言語ではこれは有効ですが、Rust では値が**ムーブ(move)**されるため、ここでエラーになります。

```
error[E0382]: borrow of moved value: `original`
 --> src/main.rs:4:20
  |
2 |     let original = "Hello, World!".to_string();
  |         -------- move occurs because `original` has type `String`, which does not implement the `Copy` trait
3 |     let other = original;
  |                 -------- value moved here
4 |     println!("{}", original);
  |                    ^^^^^^^^ value borrowed here after move
```

2 行目で `other` を定義した時点で、`original` を再び使うことは**無効**になります。これにより、**double free**、**UAF(use after free)**、そのほかダングリングポインタに起因するあらゆる種類の脆弱性を防げます。

{% hint style="info" %}
エラーメッセージが、`String` 型が [`Copy` トレイト](https://doc.rust-lang.org/std/marker/trait.Copy.html)を実装していないと述べている点に注目してください。ある型がこれを実装している場合、ここでの 2 行目のような代入は、すべてのビットをコピーして変数を**複製**します。この場合は、2 つの別個の変数がそれぞれ別の値を所有することになるので、問題は起きません。Rust が避けたいのは、2 つの変数が**メモリ上の同じデータ**を参照する状態です。`String` 型は実際の文字列へのポインタにすぎないため、複製するとまさにその状態になってしまいます。
{% endhint %}

### 借用(Borrowing)

Rust では、データをコピーしたり所有権を移したりする代わりに、データを**借用**できます。借用には**不変(immutable)**と**可変(mutable)**の 2 種類があり、**データ競合(data race)**、**イテレータの無効化(iterator invalidation)**、**並行処理が原因のバグ**を防ぐために、借用には制限が設けられています。

#### 不変借用(Immutable Borrowing)

不変借用は読み取り専用の借用です。同時に**いくつでも**この借用を行えます。

```rust
fn main() {
    let original = "Hello, World!".to_string();
    let a = &original;
    let b = &original;

    println!("{}", a);
    println!("{}", b);
}
```

これは問題なくコンパイルでき、期待どおりに動作します。

#### 可変借用(Mutable Borrowing)

可変借用は読み書き可能な借用です。

```rust
fn main() {
    let mut original = "Hello, World!".to_string();
    let a = &mut original;

    println!("{}", a);
    *a = "Test".to_string();
    println!("{}", a);
}
```

ただし、データ競合のようなバグを防ぐため、**可変借用を 2 つ同時に持つことはできません**。

```rust
fn main() {
    let mut original = "Hello, World!".to_string();
    let a = &mut original;
    let b = &mut original;

    println!("{}", a);
    *a = "Test".to_string();
    println!("{}", a);
    println!("{}", b);
}
```

```
error[E0499]: cannot borrow `original` as mutable more than once at a time
 --> src/main.rs:4:13
  |
3 |     let a = &mut original;
  |             ------------- first mutable borrow occurs here
4 |     let b = &mut original;
  |             ^^^^^^^^^^^^^ second mutable borrow occurs here
5 |
6 |     println!("{}", a);
  |                    - first borrow later used here
```

同様に、実は**不変**参照を取ることもできません。

```rust
fn main() {
    let mut original = "Hello, World!".to_string();
    let a = &mut original;
    let b = &original;

    println!("{}", a);
    *a = "Test".to_string();
    println!("{}", a);
    println!("{}", b);
}
```

```
error[E0502]: cannot borrow `original` as immutable because it is also borrowed as mutable
 --> src/main.rs:4:13
  |
3 |     let a = &mut original;
  |             ------------- mutable borrow occurs here
4 |     let b = &original;
  |             ^^^^^^^^^ immutable borrow occurs here
5 |
6 |     println!("{}", a);
  |                    - mutable borrow later used here
```

つまり、持てるのは次のどちらかです。

* 可変借用が**ひとつ**
* 不変借用が**いくつでも**

しかし、両者を混ぜることは許されません。**コンパイラがこれを強制します**。

注目すべき点として、借用が**不変**であっても、借用元の可変変数を変更することはできません。次の例を見てください。

```rust
fn main() {
    let mut original = "Hello, World!".to_string();
    let a = &original;

    println!("{}", a);
    original = "wot".to_string();
    println!("{}", a);
}
```

次のエラーになります。

```
error[E0506]: cannot assign to `original` because it is borrowed
 --> src/main.rs:6:5
  |
3 |     let a = &original;
  |             --------- `original` is borrowed here
...
6 |     original = "wot".to_string();
  |     ^^^^^^^^ `original` is assigned to here but it was already borrowed
7 |     println!("{}", a);
  |                    - borrow later used here
```

C のような言語に慣れていると、変数へのポインタを取っておいて、変数が変更されたあとにそのポインタで新しい値を読めると考えてしまっても無理はありません。しかし Rust ではそれは許されません。

### ライフタイム(Lifetimes)

**ライフタイム**は、コンパイラの借用チェッカ(borrow checker)が借用の妥当性を確認するために使うものです。ライフタイムは変数が作られたときに始まり、破棄されたときに終わります。[The Rust book](https://doc.rust-lang.org/rust-by-example/scope/lifetime.html) にライフタイムの素晴らしい解説があり、明示的に制御する方法も載っています。考え方としては、変数は他の変数の存在に結び付けられ、それらが消えると一緒に消えます。

次の例を考えてみます。

```rust
let r;
{
    let x = 5;
    r = &x;
}

println!("r: {}", r);
```

C のような言語では、`}` でスコープが終わった時点で `x` はスコープから外れて消え、`r` は `x` があった場所を指すダングリング参照として生き残ります。Rust ではコンパイラがこれを検出し、コンパイルを拒否します。

```
error[E0597]: `x` does not live long enough
 --> src/main.rs:5:13
  |
4 |         let x = 5;
  |             - binding `x` declared here
5 |         r = &x;
  |             ^^ borrowed value does not live long enough
6 |     }
  |     - `x` dropped here while still borrowed
7 |
8 |     println!("r: {}", r);
  |                       - borrow later used here
```

一方、`println!` を `{}` で定義されたスコープの中に移せば、`x` は借用した値が使われるまで十分に長く生きているので、問題なくコンパイルできます。

### ヌルポインタがない(No Null Pointers)

Rust にはヌルポインタ(null pointer)がなく、そうしたケースは明示的に処理しなければなりません。これにより、ヌルポインタ参照や、null かもしれない値に関するバグを防げます。

### 境界外アクセス(Out of Bounds)

Rust はコンパイル時に境界外(OOB)チェックを行います。それが不可能な場合(たとえばインデックスがユーザー入力で与えられる場合)は、実行時の OOB チェックが自動的に挿入されます。次のコードを例に考えます。

```rust
use std::io;

fn main() {
    let arr = [10, 20, 30];

    println!("Enter an index:");

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();

    let index: usize = input.trim().parse().unwrap();
    let value = arr[index];

    println!("Value: {}", value);
}
```

プログラムを実行して OOB となる `5` を入力すると、プログラムはパニック(panic)します。

```
thread 'main' (7216640) panicked at src/main.rs:13:17:
index out of bounds: the len is 3 but the index is 5
```
