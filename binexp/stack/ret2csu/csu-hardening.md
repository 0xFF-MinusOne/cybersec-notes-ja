# CSU Hardening

[glibc 2.34](https://lwn.net/Articles/864920/) 以降、CSU は強化され、有用なガジェットが取り除かれました。[このパッチ](https://sourceware.org/legacy-ml/libc-alpha/2018-06/msg00717.html)が原因で、これにより `__libc_csu_init`(およびほかのいくつかの関数)が完全に削除されます。

残念ながら、この変更は ABI(application binary interface)の互換性を壊します。つまり、この方法でコンパイルされたバイナリは、2.34 より前の glibc では **動作しません**。そのため、古い glibc を使っていると、CTF の問題で非常に面倒なことになりえます。一方、古い方法でコンパイルされたものは、新しいバージョンでも **動作します**。
