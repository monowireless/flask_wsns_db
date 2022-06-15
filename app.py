# Copyright (C) 2022 Mono Wireless Inc. All Rights Reserved.
# Released under MW-OSSLA-1J,1E (MONO WIRELESS OPEN SOURCE SOFTWARE LICENSE AGREEMENT).

import sys
import sqlite3
from datetime import datetime
from flask import Flask,render_template,request,g

import base64
from io import BytesIO

from matplotlib import pyplot as plt
import matplotlib.dates as mdates

# configs
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
try: conf_db_filename = config['SQLITE3']['db_file']
except: conf_db_filename = '../log/TWELITE_Stage_WSns.sqlite'

# some dictionaries 
dict_pkt_type = {
    1 : ('PAL MAG', 'MAG', 'N/A', 'N/A', 'N/A'),
    2 : ('PAL AMB', '温度[℃]', '湿度[%]', '照度[lx]', 'N/A'),
    3 : ('PAL MOT','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
    5 : ('CUE','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
    6 : ('ARIA','温度[℃]', '湿度[%]', 'N/A', 'N/A'),
    257 : ('App_TWELITE','DI0/1/2/3', 'AD1[V]', 'AD2[V]', 'AD3[V]'),
    'ARIA' : 6,
    'PAL_AMB' : 2,
    'PAL_MOT' : 3,
    'CUE' : 5,
    'MAG' : 1,
    'APPTWELITE' : 257
}

dict_mag = {
    0 : 'なし',
    1 : 'N極',
    2 : 'S極',
    3 :  None
}

dict_dio = {
    0 : 'H/H/H/H',
    1 : 'L/H/H/H',
    2 : 'H/L/H/H',
    3 : 'L/L/H/H',
    4 : 'H/H/L/H',
    5 : 'L/H/L/H',
    6 : 'H/L/L/H',
    7 : 'L/L/L/H',
    8 : 'H/H/H/L',
    9 : 'L/H/H/L',
    10: 'H/L/H/L',
    11: 'L/L/H/L',
    12: 'H/H/L/L',
    13: 'L/H/L/L',
    14: 'H/L/L/L',
    15: 'L/L/L/L',
}

dict_ev_cue = {
    1 : '面１',
    2 : '面２',
    3 : '面３',
    4 : '面４',
    5 : '面５',
    6 : '面６',
    8 : 'シェイク',
    16 : 'ムーブ',
}

# app def
app = Flask(__name__)

# convert integer value into hex value (assuming int32_t)
def tohex_i32(val):
    return hex((val + (1 << 32)) % (1 << 32))[2:].upper()

# convert hex value into integer value (assuming int32_t)
def toint_i32(val):
    x = int(val, 16)
    if x >= 2**31:
        x -= 2**32
    return x

# open the db in `g`, global for session
def db_open():
    if 'db' not in g:
        g.db = sqlite3.connect(conf_db_filename)
    return g.db

# query nodes and desc (/)
@app.route('/')
def index():
    global dict_pkt_type
    # query result
    r = []
    result = []

    # open data base
    con = db_open()
    cur = con.cursor()

    # find SIDs
    cur.execute('''SELECT * FROM sensor_last ORDER BY ts DESC''')
    # find Desc for each SID
    for sid, ts, lid, lqi, pkt_type, value, value1, value2, value3, val_vcc_mv, val_dio, ev_id in cur.fetchall():
        cur.execute('''SELECT * FROM sensor_node WHERE (sid = ?)''', (sid,))
        d = cur.fetchone()

        # PKT TYPE
        lblinfo = ('UNK',)
        if pkt_type in dict_pkt_type: lblinfo=dict_pkt_type[pkt_type]

        # CUE EVENT
        if pkt_type == dict_pkt_type['CUE']:
            if ev_id in dict_ev_cue: 
                ev_id = dict_ev_cue[ev_id]

        r.append((sid, d[1], d[2], ts, datetime.fromtimestamp(ts) # SID(int32), SID(TEXT), DESC(TEXT), ts(EPOCH)
                , (lblinfo[0], lid, lqi, value, value1, value2, value3, val_vcc_mv, val_dio, ev_id))) 
            
    
    # sort by ID
    result = sorted(r, key=lambda x : x[1])

    # close connection
    con.close()

    # returns
    return render_template('index.html', data = result)

# query years
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

# query months
@app.route('/month', methods=["POST"])
def list_months():
    sid = request.form['sid']
    i32sid = request.form['i32sid']
    latest_ts = request.form['latest_ts']
    desc = request.form["desc"]
    year = request.form["year"]
    
    # open data base and query
    con = db_open()
    cur = con.cursor()
    cur.execute('''SELECT DISTINCT month FROM sensor_data WHERE (sid=?) AND (year=?) ORDER BY month ASC''', (i32sid,year,))
    result = cur.fetchall()
    con.close()
    return render_template('month.html', sid = sid, i32sid = i32sid, desc = desc, year = year, data = result)

# query days 
@app.route('/day', methods=["POST"])
def list_days():
    sid = request.form['sid']
    i32sid = request.form['i32sid']
    latest_ts = request.form['latest_ts']
    desc = request.form["desc"]
    year = request.form["year"]
    month = request.form["month"]
    
    # open data base and query
    con = db_open()
    cur = con.cursor()
    cur.execute('''SELECT DISTINCT day FROM sensor_data 
                   WHERE (sid=?) AND (year=?) AND (month=?) ORDER BY month ASC''', (i32sid,year,month,))
    result = cur.fetchall()
    con.close()
    return render_template('day.html', sid = sid, i32sid = i32sid, desc = desc, year = year, month=month, data = result)

# query sensor data for the day.
@app.route('/show_the_day', methods=["POST"])
def show_the_day():
    global dict_pkt_type, dict_mag, dict_dio, dict_ev_cue

    sid = request.form['sid']
    i32sid = request.form['i32sid']
    latest_ts = request.form['latest_ts']
    desc = request.form["desc"]
    year = request.form["year"]
    month = request.form["month"]
    day = request.form["day"]

    # open data base and query
    con = db_open()
    cur = con.cursor()
    cur.execute('''SELECT ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id FROM sensor_data
                   WHERE (sid=?) and (year=?) and (month=?) and (day=?)
                   ''', (i32sid,year,month,day,))
    r = cur.fetchall()
    result =[]

    # check first sample (determine packet type, etc)
    lblinfo = ('UNKNOWN', 'VAL', 'VAL1', 'VAL2', 'VAL3')
    pkt_type = None
    lid = None
    if len(r) > 0:
        try:
            # pick first sample
            r0 = r[0]
            # packet type
            pkt_type = int(r0[3])
            if pkt_type in dict_pkt_type: lblinfo=dict_pkt_type[pkt_type]
            # logical ID (normally, all the same)
            lid = r0[1]
        except:
            pass

    ct = 0
    for ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id in r:
        try:
            lt = datetime.fromtimestamp(ts)

            # mag info
            mag = None
            if val_dio & 0x10000000:
                mag = dict_mag[(val_dio >> 24) & 0x3]

            if pkt_type == 1: value = mag

            # DIO
            if pkt_type == dict_pkt_type['APPTWELITE']:
                bm_dio = int(value)
                if bm_dio >= 0 and bm_dio <= 15:
                    value = dict_dio[bm_dio]

            # EVENT ON CUE
            if pkt_type == dict_pkt_type['CUE']:
                if ev_id in dict_ev_cue: 
                    ev_id = dict_ev_cue[ev_id]

        except:
            pass

        result.append((ct,lt,lqi,value,value1,value2,value3,val_vcc_mv,mag,ev_id))
        ct = ct + 1

    con.close()

    return render_template('show_the_day.html', 
                sid = sid, i32sid = i32sid, desc = desc, year = year, 
                month=month, day=day, data = result, lid=lid, lblinfo=lblinfo)

# grenrate graph data.
# @param latest_ts              if not 0, render graph from latest_ts - 1day to latest_ts.
# @param yera, month, day       specify YYYY/MM/DD (where latest_ts==0)
def _graph_a_day(sid, i32sid, latest_ts, year, month, day):
    dict_label = {
        1 : ('PAL MAG', 'MAG', 'N/A', 'N/A', 'N/A'),
        2 : ('PAL AMB', 'TEMP[C]', 'HUMID[%]', 'LUMI[lx]', 'N/A'),
        3 : ('PAL MOT','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
        5 : ('CUE','X[G]', 'Y[G]', 'Z[G]', 'N/A'),
        6 : ('ARIA','TEMP[C]', 'HUMID[%]', 'N/A', 'N/A'),
        257 : ('App_TWELITE','DI1/2/3/4', 'AD1[V]', 'AD2[V]', 'AD3[V]'),
    }

    # open data base and query
    con = db_open()
    cur = con.cursor()
    if latest_ts == 0:
        cur.execute('''SELECT ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id FROM sensor_data
                    WHERE (sid=?) and (year=?) and (month=?) and (day=?)
                    ORDER BY random() LIMIT 1024''', (i32sid,year,month,day,))
    else:
        cur.execute('''SELECT ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id FROM sensor_data
                    WHERE (sid=?) and (ts BETWEEN ? and ?)
                    ORDER BY random() LIMIT 1024''', (i32sid,latest_ts-86399,latest_ts,))
        lt = datetime.fromtimestamp(latest_ts)
        year = lt.year
        month = lt.month
        day = lt.day
        
    r = cur.fetchall()
    con.close()

    # check first sample (determine packet type, etc)
    lblinfo = ('UNKNOWN', 'VAL', 'VAL1', 'VAL2', 'VAL3')
    pkt_type = None
    lid = None
    if len(r) > 0:
        try:
            # pick first sample
            r0 = r[0]
            # packet type
            pkt_type = int(r0[3])
            if pkt_type in dict_label: lblinfo=dict_label[pkt_type]
            # logical ID (normally, all the same)
            lid = r0[1]
        except:
            pass

    # save vector
    v_0 = []
    v_1 = []
    v_2 = []
    v_t = []
    
    # sorting the list (use random pick during SQL query, but sorted by ts is better for grapphing)
    sr = sorted(r, key=lambda x : x[0])
    ct = 1
    for ts,lid,lqi,pkt_type,value,value1,value2,value3,val_vcc_mv,val_dio,ev_id in sr:
        lt = datetime.fromtimestamp(ts)
        v_0.append(value)
        v_1.append(value1)
        v_2.append(value2)
        v_t.append(lt)

    ### save fig
    fig = plt.figure()
    fig.set_size_inches(5, 10)

    fig.suptitle("%s - %04d/%02d/%02d - %s" % (sid, int(year), int(month), int(day), lblinfo[0]))
    
    ax = fig.add_subplot(3, 1, 1)
    ax.tick_params(labelsize = 6.5) 
    ax.plot(v_t, v_0, label=lblinfo[1], color='red')
    #ax.set_ylabel(lblinfo[1])
    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    if v_1.count(None) != len(v_1):
        ax1 = fig.add_subplot(3, 1, 2)
        ax1.tick_params(labelsize = 6.5) 
        ax1.plot(v_t, v_1, label=lblinfo[2], color='green')
        #ax1.set_ylabel(lblinfo[2])
        ax1.legend(loc='upper left')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    if v_2.count(None) != len(v_2):
        ax2 = fig.add_subplot(3, 1, 3)
        ax2.tick_params(labelsize = 6.5) 
        ax2.plot(v_t, v_2, label=lblinfo[3], color='blue')
        #ax2.set_ylabel(lblinfo[3])
        ax2.legend(loc='upper left')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    
    fig.tight_layout()  

    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"

# query sensor data for the day.
@app.route('/graph_the_day', methods=["POST"])
def graph_the_day():
    sid = request.form['sid']
    i32sid = request.form['i32sid']
    #latest_ts = request.form['latest_ts']
    #desc = request.form["desc"]
    year = request.form["year"]
    month = request.form["month"]
    day = request.form["day"]

    return _graph_a_day(sid, i32sid, 0, year, month, day)

# query sensor data of the latest 24hours
@app.route('/graph_the_latest', methods=["POST"])
def graph_the_latest():
    sid = request.form['sid']
    i32sid = request.form['i32sid']
    latest_ts = request.form['latest_ts']
    #desc = request.form["desc"]

    return _graph_a_day(sid, i32sid, int(latest_ts), 0, 0, 0)

if __name__ == '__main__':
    app.debug = True
    app.run(host='localhost')
