# Python, Flask, sqlite3 による簡易的なサーバ

```python
# Copyright (C) 2022 Mono Wireless Inc. All Rights Reserved.
# Released under MW-OSSLA-1J,1E (MONO WIRELESS OPEN SOURCE SOFTWARE LICENSE AGREEMENT).
```

## このサンプルコードについて
TWELTIE STAGE のセンサーグラフ機能では、sqlite3 を用い取得したセンサーデータを保存します。
このサンプルでは、TWELITE STAGEこのデータベースをウェブサーバー上で参照します。

* Python3や関連パッケージのインストールが必要です。インストールのための pip3 コマンドなどの扱いは一般の情報を参照してください。
* パッケージのバージョン等に依存して動作状況が変化する場合があります。

## 必要なPython3パッケージ
* `sqlite3` : sqlite3 データベースへのアクセスを行います。最近の Python3 には含まれる場合があります。(参考: `pip3 install pysqlite3`)
* `Flask` : 軽量ウェブサーバーです。(参考：`pip3 install Flask`)
* `matplotlib` : グラフを描画します (参考：`pip3 install matplotlib`)

## ファイル構成
TWELITE STAGE インストールディレクトリを {TWELITE STAGE} とします。データベースファイルを相対パス `../log/TWELITE_Stage_WSns.sqlite`により開くため、以下のディレクトリ構成にしておきます。
```
{TWELITE STATE}/                    : STAGE 最上位、実行形式などが格納
    /log                            : ログディレクトリ
    /log/TWELITE_Stage_WSns.sqlite  : データベースファイル

    /flask_wsns_db                  : 本サンプルのトップディレクトリ
        static/                     : CSS など
        templates/                  : html ひな型
        app.py                      : サーバー用のスクリプト
```



## Flaskの起動

コマンドプロンプトやシェルで `{TWELITE STAGE}` ディレクトリに移動して、`python3 app.py` を実行します。終了はコマンド画面上で `Ctrl+C` などです。

```bash
$ cd {TWELITE STAGE}
$ python3 app.py
```

ブラウザからは http://localhost:5000 を開きます（デフォルト設定）。



## app.py について
※ この解説で引用されるソースコードは格納される最新コードと一部違う場合があります。

### import セクション
sqlite3, Flask関連のパッケージを読み込んでいます。
```python
import sqlite3
from flask import Flask,render_template,request,g
```

### データベース接続
セッションごとのデータベース接続を管理しています。
```python
def db_open():
    if 'db' not in g:
        g.db = sqlite3.connect('../log/TWELITE_Stage_WSns.sqlite')
    return g.db
```

### / ルートのアクセス
`@app.route('/')`で始まる関数 `def index():` は HTTP からの `/` のリクエストを処理します。

```python
@app.route('/')
def index():
    # query result
    result = []

    # open data base
    con = db_open()
    cur = con.cursor()

    # find SIDs
    cur.execute('''SELECT * FROM sensor_last ORDER BY ts DESC''')
    # find Desc for each SID
    for sid, ts in cur.fetchall():
        cur.execute('''SELECT * FROM sensor_node WHERE (sid = ?)''', (sid,))
        d = cur.fetchone()
        result.append((sid, d[1], d[2], ts, datetime.fromtimestamp(ts))) # SID(int32), SID(TEXT), DESC(TEXT), ts(EPOCH)

    # close connection
    con.close()

    # returns
    return render_template('index.html', data = result)
```

Webサーバーにルートアクセスがあった場合のふるまいを記述します。`@app.route('/')` 部分で `/` へのアクセスを指定します。
まずデータベースへの接続、sqlite3 操作用のカーソル `cur` を構築し、データベースからシリアルID(SID)一覧を検索します。
```python
    # open data base
    con = db_open()
    cur = con.cursor()
```

シリアル一覧は `sensor_last` テーブルより得ています。このテーブルは SID と最後にデータを受信したときのタイムスタンプを
記録しています。データの格納時に更新されるテーブルです。
```python
cur.execute('''SELECT * FROM sensor_last ORDER BY ts DESC''')
```

続いて SID ごとに `sensor_node` テーブルを検索します。このテーブルは、SID に紐づいた補助情報 `desc` を格納しています。
結果はタプルを格納したリスト `[(SID, SID文字列, 補助情報文字列, タイムスタンプ), ...]` です。
```python
for sid, ts in cur.fetchall():
    cur.execute('''SELECT * FROM sensor_node WHERE (sid = ?)''', (sid,))
    d = cur.fetchone()
    result.append((sid, d[1], d[2], ts, datetime.fromtimestamp(ts))) # SID(int32), SID(TEXT), DESC(TEXT), ts(EPOCH)
```

データベース検索はここまでです。`con.close()`を呼び出しておきます。

ウェブのページには SID, 最終取得時間, 補助情報を表示させます。ウェブページはテンプレート `templates/index.html` で
構成されますが、このテンプレート対してデータ`data`を与えます。
```python
    return render_template('index.html', data = result)
```

### templates/index.html
HTMLのテンプレートでは、Flask から渡されたデータを `{{item[1]}}` のような式を用いて内容を構成します。
この HTML では、SID リスト（および無線ノードから得られた最新の情報）を表示します。
その SID のリンクをクリックすることで、センサーデータの格納される年度を検索する画面に遷移します。
（年度検索画面から月検索、日検索、日データ表示と画面遷移します）
また「最新データ」の日付をクリックすることで、そのデータから遡って１日分のグラフを表示します。

```html
<!DOCTYPE html>
<html lang="jp">
<head>
    <meta charset="UTF-8">
    <title>センサーノード</title>
    <link rel="stylesheet" type="text/css" href="static/css/style.css">
</head>
<body>
    <div>
        <table>
            <thead>
                <tr>
                    <th>SID</th>
                    <th>詳細</th>
                    <th>センサー種別</th>
                    <th>最新データ</th>
                    <th>LID</th>
                    <th>LQI</th>
                    <th>value</th>
                    <th>value1</th>
                    <th>value2</th>
                    <th>value3</th>
                    <th>val_vcc_mv</th>
                    <th>EVENT</th>
                </tr>
            </thead>
            <tbody>
                {% for item in data %}
                <tr>
                    <td>
                        <form method="POST" name="FORM_{{item[1]}}" action="/year">
                        <a href="javascript:FORM_{{item[1]}}.submit()">{{item[1]}}</a>
                        <input type="hidden" name="i32sid" value="{{item[0]}}">
                        <input type="hidden" name="sid" value="{{item[1]}}">
                        <input type="hidden" name="desc" value="{{item[2]}}">
                        <input type="hidden" name="latest_ts" value="{{item[3]}}">
                        </form>
                    </td>
                    <td>{{item[2]}}</td><!-- desc -->
                    <td>{{item[5][0]}}</td>
                    <td>
                        <form method="POST" name="FORM_L_{{item[1]}}" action="/graph_the_latest">
                            <a href="javascript:FORM_L_{{item[1]}}.submit()">{{item[4]}}</a>
                            <input type="hidden" name="i32sid" value="{{item[0]}}">
                            <input type="hidden" name="sid" value="{{item[1]}}">
                            <input type="hidden" name="desc" value="{{item[2]}}">
                            <input type="hidden" name="latest_ts" value="{{item[3]}}">
                        </form>
                    </td><!-- timestamp -->
                    <td>{{item[5][1]}}</td>
                    <td>{{item[5][2]}}</td>
                    <td>{{item[5][3]}}</td>
                    <td>{{item[5][4]}}</td>
                    <td>{{item[5][5]}}</td>
                    <td>{{item[5][6]}}</td>
                    <td>{{item[5][7]}}</td>
                    <td>{{item[5][9]}}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <div class="lastupd">
        Last updated at 
        <SCRIPT LANGUAGE="javascript" TYPE="text/javascript">
            options = { year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' };
            document.write(new Intl.DateTimeFormat('default', options).format(new Date()) + ".");
        </SCRIPT>
    </div>
</body>
</html>
```

CSSは `static/` 以下に格納します。
```html
    <link rel="stylesheet" type="text/css" href="static/css/style.css">
```

Python側から渡された `data` にアクセスできます。以下では `for` 文を用いて
リストで与えられる `data` を要素ごとに展開し、テーブルに追加しています。
```html
{% for item in data %}
...
<td>{{item[2]}}</td>
{% endfor %}
```

続く年度検索を行うためにフォームの `"POST"` を用いますが、データベースでの諸情報も
パラメータとして(`i32sid`, `sid`, `desc`, `latest_ts`) 与えておきます。
また、リンク先を `javascript:FORM_XXX.submit()` としてフォームのボタンを押したの
と同じ動作をさせ `/year` にアクセスします。`/year` のアクセスは Python で処理します。
```html
<form method="POST" name="FORM_{{item[1]}}" action="/year">
<a href="javascript:FORM_{{item[1]}}.submit()">{{item[1]}}</a>
<input type="hidden" name="i32sid" value="{{item[0]}}">
<input type="hidden" name="sid" value="{{item[1]}}">
<input type="hidden" name="desc" value="{{item[2]}}">
<input type="hidden" name="latest_ts" value="{{item[3]}}">
</form>
```

### /year のアクセス (POST 処理)
`/` からのリンク `/year` を処理します。POST処理に対応するため `, methods=["POST"]` を指定します。
```python
@app.route('/year', methods=["POST"])
def list_years():
    sid = request.form['sid']
    i32sid = request.form['i32sid']
    latest_ts = request.form['latest_ts']
    desc = request.form["desc"]

    # open data base and query
    con = db_open()
    cur = con.cursor()
    cur.execute('''SELECT DISTINCT year FROM sensor_data WHERE sid = ? ORDER BY year ASC''', (i32sid,))
    result = cur.fetchall()
    con.close()
    return render_template('year.html', sid = sid, i32sid = i32sid, desc = desc, data = result)
```

`/` から渡されたパラメータは `request.form[]` よりアクセスできます。
```python
sid = request.form['sid']
i32sid = request.form['i32sid']
latest_ts = request.form['latest_ts']
desc = request.form["desc"]
```

ここでもデータベース検索を行います。sid と year を指定します。sid の検索キーは `int32_t` 型の整数値であることに注意してください。
```python
cur.execute('''SELECT DISTINCT year FROM sensor_data WHERE sid = ? ORDER BY year ASC''', (i32sid,))
```
※ TWELITE STAGE で作成されたデータベースでは、sid, year を効率的に検索できるようなインデックスは作成していません。データが巨大化した場合など、パフォーマンスが問題になる場合は ts(タイムスタンプ) による検索を行ったり、適切なインデックスを構成するなどしてください。

HTMLテンプレートファイル(`templates/year.html`)には、検索されたデータが存在する年度リスト(`data=result`) と、諸情報(`sid`, `i32sid`, `desc`) を渡します。
```python
return render_template('year.html', sid = sid, i32sid = i32sid, desc = desc, data = result)
```

テンプレートの構成は `index.html` とほぼ同様で、データのある年リストを表示し続く月検索 `/month` に年情報を含めた補助情報を渡しています。

### /month, /day の検索
データの存在する月、日を検索し、そのリストを渡します。処理自体は `/`や`/year`の処理とほぼ同じです。

日検索には２つのリンクを設定し、一つはリスト表示、一つはグラフです。

### センサーデータの検索（日表示、リスト表示）
このサンプルでは１日分のデータを表の形で出力します。センサーデータは以下の式で検索しています。検索式が長くなった以外は、先ほどまでの年月日の検索と
処理は大きく変わりません。検索した値をタプルを格納したリストとして html テンプレートに渡します。
```python
    cur.execute('''SELECT ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id FROM sensor_data
                   WHERE (sid=?) and (year=?) and (month=?) and (day=?)
                   ORDER BY ts ASC''', (i32sid,year,month,day,))
```

ここでは、データ形式ごとにラベルを設定するための連想リストを構築しています。
```python
    dict_pkt_type = {
        1 : ('PAL MAG', 'MAG', 'N/A', 'N/A', 'N/A'),
        2 : ('PAL AMB', '温度[℃]', '湿度[%]', '照度[lx]', 'N/A'),
        3 : ('PAL MOT','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
        5 : ('CUE','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
        6 : ('ARIA','温度[℃]', '湿度[%]', 'N/A', 'N/A'),
        257 : ('App_TWELITE','DI0/1/2/3', 'AD1[V]', 'AD2[V]', 'AD3[V]'),
    }
```

DI情報や磁気センサーの情報が含まれる場合は、専用の表示に変更するなどしています。
```python
    ct = 1
    for ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id in r:
        try:
            lt = datetime.fromtimestamp(ts)
        
            # mag info
            mag = None
            if val_dio & 0x10000000:
                mag = dict_mag[(val_dio >> 24) & 0x3]

            if pkt_type == 1: value = mag

            # DIO
            if pkt_type == 257:
                bm_dio = int(value)
                if bm_dio >= 0 and bm_dio <= 15:
                    value = dict_dio[bm_dio]

            # EVENT ON CUE
            if pkt_type == 5:
                pass
                if ev_id is not None:
                    if ev_id in dict_ev_cue: 
                        ev_id = dict_ev_cue[ev_id]

        except:
            pass

        result.append((ct,lt,lqi,value,value1,value2,value3,val_vcc_mv,mag,ev_id))
        ct = ct + 1
```

HTMLテンプレートに情報を渡しています。リスト(`data`)に含まれない LID (`lid`) やラベル情報(`lblinfo`)
を別途渡しています。
```python
    return render_template('show_the_day.html', 
                sid = sid, i32sid = i32sid, desc = desc, year = year, 
                month=month, day=day, data = result, lid=lid, lblinfo=lblinfo)
```

### センサーデータの検索（日表示、グラフ）
グラフの機能は `_graph_a_day()` 関数に処理を集約しています。最新のタイムスタンプからグラフを描画する処理と
指定した年月日からグラフを描画する２種類を実行しています。

データ検索はリスト表示と流れは同じですが、表示用データを`ORDER BY random() LIMIT 1024`の指定を行い間引いています。
```python
    cur.execute('''SELECT ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id FROM sensor_data
                   WHERE (sid=?) and (year=?) and (month=?) and (day=?)
                   ORDER BY random() LIMIT 1024''', (i32sid,year,month,day,))
```

またグラフ表示用のリストを作成しています。グラフ描画のためランダム並びのデータを時間順にソートしています。
```python
    v_0 = []
    v_1 = []
    v_2 = []
    v_t = []
    
    sr = sorted(r, key=lambda x : x[0])
    ct = 1
    for ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id in sr:
        lt = datetime.fromtimestamp(ts)
        v_0.append(value)
        v_1.append(value1)
        v_2.append(value2)
        v_t.append(lt)
```

グラフのイメージはファイルを作成せず、直接転送しています。そのために `BytesIO()` を用いています。
```python
    fig = plt.figure()
    ...
    ax = fig.add_subplot(3, 1, 1)
    ax.tick_params(labelsize = 6.5) 
    ax.plot(v_t, v_0, label=lblinfo[1], color='red')
    ...
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"
```

## 動作について
* TWLITE STAGEでデータ取得中の場合もアクセスは可能ですが、TWELITE STAGEでのデータベース書き出しのタイミング（約１０秒ごと）までは、情報は更新されません。
* 本サンプルのデータベース検索では テーブル `sensor_data` 中の `year`, `month`, `day` カラムを用いていますが、パフォーマンスが必要な場合は `ts` カラムを用いた検索を行うか、適切なインデックスを構築してください。
