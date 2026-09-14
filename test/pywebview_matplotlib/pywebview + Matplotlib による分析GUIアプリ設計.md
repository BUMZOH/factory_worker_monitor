# pywebview + Matplotlib による分析GUIアプリ設計

## 1. はじめに

この資料では、**pywebviewを操作用GUIとして使用し、Matplotlibのグラフを別ウィンドウで表示するアプリ**の基本構成を解説します。

今回の方式では、それぞれの得意分野を分担します。

-   **pywebview**：ボタン、ラベル、日付入力などの操作画面
-   **Python API**：HTML/JavaScriptからPython処理への橋渡し
-   **subprocess**：グラフ表示プログラムを別プロセスとして起動
-   **Matplotlib**：グラフ表示、拡大縮小、パン、保存などの分析操作

Matplotlibを単なる「グラフ画像作成ライブラリ」として使うのではなく、
Matplotlibが標準で持っているGUI機能をそのまま活用するのがポイントです。

------------------------------------------------------------------------

## 2. 設計の考え方

分析画面までWeb側ですべて実装するのではなく、

> **操作画面はpywebview、分析画面はMatplotlib**

と役割分担します。

Matplotlibの標準ウィンドウには、バックエンドによって多少異なりますが、
Zoom、Pan、Home、Back、Forward、Saveなどの分析に便利な機能があります。

この機能を自作せず、そのまま利用するのが今回の設計です。

------------------------------------------------------------------------

## 3. アプリ全体の構成

今回のサンプルは次の構成です。

``` text
pywebview_matplotlib/
│
├─ app.py
├─ graph1.py
├─ index.html
└─ style.css
```

処理の流れは次のようになります。

``` text
┌─────────────────────────────┐
│         pywebview           │
│                             │
│  日付入力                   │
│  [ 20260915 ]               │
│                             │
│  [ グラフ1表示 ]            │
└──────────────┬──────────────┘
               │
               │ JavaScript
               ▼
        Python API
        show_graph1()
               │
               │ subprocess.Popen()
               ▼
          graph1.py
               │
               ▼
        Matplotlib Window
```

pywebviewとMatplotlibを無理に同じウィンドウへ統合しないことが重要です。

------------------------------------------------------------------------

## 4. なぜ subprocess を使うのか

pywebviewのPython APIから直接、

``` python
plt.show()
```

を実行すると、MatplotlibのGUIをメインスレッド以外から開始することになり、
環境によって次のような警告が発生します。

``` text
UserWarning:
Starting a Matplotlib GUI outside of the main thread will likely fail.
```

そこでMatplotlibを直接起動せず、

``` python
subprocess.Popen(...)
```

によって**別のPythonプロセス**を起動します。

``` text
Process 1
└─ app.py
   └─ pywebview

Process 2
└─ graph1.py
   └─ Matplotlib
```

これによりMatplotlib側は独立したプロセスとして動作できます。

------------------------------------------------------------------------

## 5. app.py 全コード

``` python
from pathlib import Path
import subprocess
import sys

import webview


BASE_DIR = Path(__file__).resolve().parent


class Api:
    def show_graph1(self, target_date):
        """Start graph 1 with the target date."""
        subprocess.Popen(
            [
                sys.executable,
                str(BASE_DIR / "graph1.py"),
                target_date,
            ]
        )


api = Api()

window = webview.create_window(
    "Matplotlib Sample",
    "index.html",
    js_api=api,
    width=500,
    height=300,
)

webview.start()
```

### BASE_DIR

``` python
BASE_DIR = Path(__file__).resolve().parent
```

`app.py`自身が存在するフォルダを取得します。

これによって、

``` python
BASE_DIR / "graph1.py"
```

のように、カレントディレクトリに依存せずファイルを指定できます。

### Python API

``` python
class Api:
    def show_graph1(self, target_date):
```

HTML/JavaScript側から呼び出すPython APIです。

JavaScriptから渡された日付が`target_date`に入ります。

### subprocess.Popen()

``` python
subprocess.Popen(
    [
        sys.executable,
        str(BASE_DIR / "graph1.py"),
        target_date,
    ]
)
```

概念的には次の実行に相当します。

``` text
python graph1.py 20260915
```

`Popen()`は子プロセスの終了を待たないため、
Matplotlibを表示したままpywebview側を操作できます。

### sys.executable

``` python
sys.executable
```

には、現在`app.py`を実行しているPython実行ファイルのパスが入ります。

仮想環境`.venv`から起動している場合は、その仮想環境のPythonを使って
`graph1.py`を起動できます。

単純に`"python"`と指定するより、使用するPython環境を揃えやすい方法です。

### pywebviewウィンドウ

``` python
window = webview.create_window(
    "Matplotlib Sample",
    "index.html",
    js_api=api,
    width=500,
    height=300,
)
```

特に重要なのが、

``` python
js_api=api
```

です。

これによりJavaScriptから、

``` javascript
window.pywebview.api.show_graph1(...)
```

としてPythonメソッドを呼び出せます。

------------------------------------------------------------------------

## 6. index.html 全コード

``` html
<!DOCTYPE html>
<html lang="ja">

<head>
    <meta charset="UTF-8">
    <title>Matplotlib Sample</title>
</head>

<body>

    <h1>Matplotlib Sample</h1>

    <input
        type="text"
        id="targetDate"
        value="20260915"
    >

    <button onclick="showGraph1()">
        グラフ1表示
    </button>

    <script>
        async function showGraph1() {
            const targetDate =
                document.getElementById("targetDate").value;

            await window.pywebview.api.show_graph1(
                targetDate
            );
        }
    </script>

</body>

</html>
```

### 日付の取得

``` javascript
const targetDate =
    document.getElementById("targetDate").value;
```

入力欄の値を取得します。

### JavaScriptからPythonへ渡す

``` javascript
await window.pywebview.api.show_graph1(
    targetDate
);
```

Python側の、

``` python
def show_graph1(self, target_date):
```

が呼び出されます。

``` text
HTML input
    ↓
JavaScript
    ↓
pywebview API
    ↓
Python
```

という流れです。

------------------------------------------------------------------------

## 7. graph1.py 全コード

``` python
import sys

import matplotlib.pyplot as plt


target_date = sys.argv[1]

print(f"Target date: {target_date}")


x = [1, 2, 3, 4, 5]
y = [10, 20, 15, 30, 25]

plt.figure()

plt.plot(
    x,
    y,
)

plt.title(f"Graph 1 - {target_date}")
plt.xlabel("X")
plt.ylabel("Y")

plt.show()
```

### コマンドライン引数を受け取る

`app.py`から渡した日付は`sys.argv`に格納されます。

``` text
python graph1.py 20260915
```

なら、

``` python
sys.argv[0]
```

は`graph1.py`、

``` python
sys.argv[1]
```

は`20260915`です。

そのため、

``` python
target_date = sys.argv[1]
```

で表示対象の日付を取得できます。

### Matplotlibの表示

``` python
plt.show()
```

を通常どおり使用できます。

`graph1.py`は独立したPythonプロセスとして実行されているため、
pywebviewのGUIスレッドとは分離されています。

------------------------------------------------------------------------

## 8. style.css 全コード

``` css
body {
    font-family: sans-serif;
    text-align: center;
    padding: 40px;
}

button {
    width: 160px;
    height: 50px;
    margin: 10px;
    font-size: 16px;
}
```

GUI側は操作パネルとして割り切っているため、CSSも小さくできます。

------------------------------------------------------------------------

## 9. データの流れ

``` text
1. ユーザーが日付を入力
        ↓
   20260915

2. 「グラフ1表示」をクリック
        ↓
3. JavaScriptがinputから値を取得
        ↓
   targetDate = "20260915"

4. pywebview APIを呼び出す
        ↓
   show_graph1("20260915")

5. Python側が値を受け取る
        ↓
   target_date = "20260915"

6. subprocessで別プロセスを起動
        ↓
   graph1.py 20260915

7. graph1.pyがsys.argvで受け取る
        ↓
   sys.argv[1] = "20260915"

8. Matplotlibでグラフを表示
```

------------------------------------------------------------------------

## 10. 複数の値を渡す

たとえば日付、ROI番号、表示モードを渡す場合は、

``` python
subprocess.Popen(
    [
        sys.executable,
        str(BASE_DIR / "graph1.py"),
        target_date,
        roi_no,
        display_mode,
    ]
)
```

とできます。

受け取る側は、

``` python
target_date = sys.argv[1]
roi_no = sys.argv[2]
display_mode = sys.argv[3]
```

です。

引数が多くなった場合は`argparse`などを検討できますが、
少数の単純な値なら`sys.argv`でも十分です。

------------------------------------------------------------------------

## 11. Matplotlibを最大限利用する

今回の方式では、Matplotlibのグラフを静止画像としてpywebviewへ貼るのではなく、
**Matplotlib自身のGUIウィンドウ**として表示します。

これにより、一般的なMatplotlib GUIバックエンドが提供する、

-   Home
-   Back
-   Forward
-   Pan
-   Zoom
-   Save

などの機能をそのまま利用できます。

分析ツールでは特に、

> 気になる部分をその場で拡大して確認する

という操作が非常に便利です。

------------------------------------------------------------------------

## 12. pywebviewとMatplotlibの役割分担

  担当         用途
  ------------ -----------------------------
  pywebview    メインGUI
  HTML         ボタン、入力欄、ラベル
  CSS          GUIデザイン
  JavaScript   GUI操作、Python API呼び出し
  Python API   GUIとPython処理の橋渡し
  subprocess   分析プログラムの独立起動
  Matplotlib   グラフ表示と対話的な分析

重要なのは、

> **すべてを一つの技術だけで実装しない**

ことです。

------------------------------------------------------------------------

## 13. Chart.jsとの使い分け

### pywebview + Chart.js が向いているもの

-   常時表示するダッシュボード
-   リアルタイム表示
-   見た目を重視するUI
-   HTML画面の中へグラフを配置したい場合

### Matplotlibが向いているもの

-   データ分析
-   散布図
-   ヒストグラム
-   異常値確認
-   実験データ確認
-   拡大して細部を調べる用途
-   必要なときだけ開く分析画面

``` text
常時表示
    → Chart.js

詳しく調査
    → Matplotlib
```

という使い分けができます。

------------------------------------------------------------------------

## 14. 工場向けツールへの応用

この方式は作業者監視ツールにもそのまま応用できます。

``` text
┌──────────────────────────────────┐
│ Worker Detection Tool            │
│                                  │
│ Target Date                      │
│ [ 2026/09/15 ]                   │
│                                  │
│ [ Worker Timeline ]              │
│ [ Worker Position ]              │
│                                  │
│ [ Start Worker Detection ]       │
│ [ Merge Video Files ]            │
└──────────────────────────────────┘
```

たとえば、

``` text
Worker Timeline
        ↓
create_worker_timeline.py
        ↓
Matplotlib
```

または、

``` text
Worker Position
        ↓
worker_position_scatter.py
        ↓
Matplotlib
```

とできます。

------------------------------------------------------------------------

## 15. 小さなツールを組み合わせる

巨大な1本のPythonプログラムへ全部詰め込む必要はありません。

``` text
app.py
│
├─ detect_worker.py
├─ create_worker_timeline.py
├─ worker_position_scatter.py
└─ merge_videos.py
```

`app.py`を各ツールを起動するための操作盤と考えます。

各ツールを独立させると、

-   単体で動作確認しやすい
-   修正箇所が分かりやすい
-   不具合の影響範囲を限定しやすい
-   新しい分析ツールを追加しやすい

という利点があります。

------------------------------------------------------------------------

## 16. グラフ2を追加する例

Python APIには、

``` python
def show_graph2(self, target_date):
    subprocess.Popen(
        [
            sys.executable,
            str(BASE_DIR / "graph2.py"),
            target_date,
        ]
    )
```

を追加します。

HTMLには、

``` html
<button onclick="showGraph2()">
    グラフ2表示
</button>
```

を追加します。

JavaScriptは、

``` javascript
async function showGraph2() {
    const targetDate =
        document.getElementById("targetDate").value;

    await window.pywebview.api.show_graph2(
        targetDate
    );
}
```

とします。

このように分析ツールを横へ増やしていけます。

------------------------------------------------------------------------

## 17. この設計のポイント

今回の方式を一言で表すと、

> **pywebviewを操作盤として使い、Matplotlibを独立した分析画面として最大限利用する。**

という設計です。

``` text
HTML / CSS
    ↓
操作しやすいGUI

JavaScript
    ↓
Python API呼び出し

pywebview
    ↓
GUIとPythonの接続

subprocess
    ↓
分析処理を別プロセス化

Matplotlib
    ↓
高機能な分析ウィンドウ
```

------------------------------------------------------------------------

## 18. まとめ

今回の構成では、pywebviewの中へMatplotlibを無理に埋め込みません。

代わりに、

``` text
pywebview
    ↓
Python API
    ↓
subprocess
    ↓
Matplotlib
```

という構成にします。

主な特徴は次のとおりです。

-   GUIと分析処理を分離できる
-   Matplotlibの標準GUIをそのまま利用できる
-   ZoomやPanを自作しなくてよい
-   Matplotlibウィンドウを独立して開ける
-   Matplotlibを表示したままpywebviewを操作できる
-   既存のPython分析プログラムを再利用しやすい
-   新しい分析ツールを追加しやすい
-   日付などの条件をGUIから分析プログラムへ渡せる

特にデータ分析を伴う工場向けツールでは、

> **操作部分はシンプルなGUI、分析部分はMatplotlibの強力な機能を利用する**

という構成が実用的です。

Matplotlibを「グラフ画像を作るだけのライブラリ」ではなく、
**対話的な分析用GUIとして利用する**ことが今回の重要な考え方です。
