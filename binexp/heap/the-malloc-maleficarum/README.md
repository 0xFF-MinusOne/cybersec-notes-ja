---
description: 最初期のヒープエクスプロイト
---

# The Malloc Maleficarum

2001 年に、ヒープエクスプロイトに関する最も有名な論文のうち 2 本が、有名な雑誌 [Phrack](http://phrack.org) に掲載されました。[Vudo malloc tricks](http://phrack.org/issues/57/8.html) と [Once upon a free()](http://phrack.org/issues/57/9.html) です。これらは、公開された最初期のヒープエクスプロイト手法で、これまでに読んだものの一部も含まれています。

2004 年後半に glibc が強化され、これらのエクスプロイトは使えなくなりました。次に有名なヒープエクスプロイトの論文は 2005 年の [The Malloc Maleficarum](https://seclists.org/bugtraq/2005/Oct/118) で、手法を _House_ ごとに分類してまとめています。

* The House of Prime
* The House of Mind
* The House of Force
* The House of Lore
* The House of Spirit
* The House of Chaos

それぞれに独自の工夫がありました。この伝統にならって、現代のヒープエクスプロイトも、[House of Rust](https://c4ebt.github.io/2021/01/22/House-of-Rust.html) のように、独自の _House_ としてあだ名が付けられることがよくあります。

オリジナルの House は現代のヒープエクスプロイトの礎であり、今ではもう実行できませんが、思っているより最近まで通用していました。知識を積み上げるうえでも、理解しておくことが重要です。
