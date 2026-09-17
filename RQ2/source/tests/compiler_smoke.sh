#!/usr/bin/env bash
set -euo pipefail
TD=$(mktemp -d)
trap 'rm -rf "$TD"' EXIT
cat > "$TD/Main.java" <<'JAVA'
import java.util.*;
public class Main {
  public static void main(String[] args) {
    String s = "abc"; List<Integer> xs = new ArrayList<>(); Object x = null;
    if (s.indexOf("b") != s.indexOf("b", 0)) throw new RuntimeException();
    if (xs.isEmpty() != (xs.size() == 0)) throw new RuntimeException();
    if ((x != null) != (null != x)) throw new RuntimeException();
  }
}
JAVA
javac "$TD/Main.java" && java -cp "$TD" Main
cat > "$TD/main.cpp" <<'CPP'
#include <vector>
#include <cassert>
int main(){ std::vector<int> xs; int *x=nullptr; assert(xs.empty()==(xs.size()==0)); assert((x!=nullptr)==(nullptr!=x)); }
CPP
g++ -std=c++17 "$TD/main.cpp" -o "$TD/a.out" && "$TD/a.out"
cat > "$TD/main.js" <<'JS'
const xs=[]; const x=null; const s='abc';
if (s.indexOf('b') !== s.indexOf('b',0)) process.exit(1);
if ((x != null) !== (null != x)) process.exit(2);
if (xs.indexOf(3) !== xs.indexOf(3,0)) process.exit(3);
JS
node "$TD/main.js"
echo "compiler/runtime smoke tests passed"
