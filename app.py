import os
import uuid

import pandas as pd

from flask_caching import Cache

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

# App
app = dash.Dash()
server = app.server  # Flask app for deployment.

# Cache config
CACHE_CONFIG = {
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory',

    # should be equal to maximum number of users on the app at a single time
    # higher numbers will store more data in the filesystem / redis cache
    'CACHE_THRESHOLD': 200
}
cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)


def interpolate_colors(col1, col2, cut):

    return ['rgb({},{},{})'.format(col1[0] + ((col2[0] - col1[0]) * n // cut),
                                   col1[1] + ((col2[1] - col1[1]) * n // cut),
                                   col1[2] + ((col2[2] - col1[2]) * n // cut)) for n in range(0, cut+1)]


# Pie color palette
pie_color = interpolate_colors((198, 212, 225), (68, 116, 157), 9)[::-1]

# Bar color palette
bar_color_last = 'rgb(198,212,225)'
bar_color_current = 'rgb(68,116,157)'

# Sankey color palette
node_color = 'rgb(198,212,225)'

top_n = 10
line_color = interpolate_colors((198, 212, 225), (68, 116, 157), top_n-1)[::-1]
line_color_default = 'rgba(100, 100, 100, 0.2)'

# Data manipulation
frames_net_in = []
frames_net_out = []

frames_in = []
frames_out = []

folder = './data/'
for file in os.listdir(folder):
    if file[-3:] == 'csv':
        if 'net' in file:
            if 'in' in file:
                frames_net_in.append(pd.read_csv(folder+file, encoding='cp949'))
            elif 'out' in file:
                frames_net_out.append(pd.read_csv(folder+file, encoding='cp949'))
            else:
                raise NameError
        else:
            if 'in' in file:
                frames_in.append(pd.read_csv(folder+file, encoding='cp949'))
            elif 'out' in file:
                frames_out.append(pd.read_csv(folder+file, encoding='cp949'))
            else:
                raise NameError

df_net_in = pd.concat(frames_net_in, axis=0)
df_net_out = pd.concat(frames_net_out, axis=0)

df_in = pd.concat(frames_in, axis=0)
df_out = pd.concat(frames_out, axis=0)

# Typo correction
df_net_out = df_net_out.rename({'부분명': '부문명'}, axis='columns')


@cache.memoize(timeout=300)
def global_store(year):
    df_net_iscope = df_net_in[df_net_in['회계연도'] == year]
    df_net_oscope = df_net_out[df_net_out['회계연도'] == year]

    df_iscope = df_in[df_in['회계연도'] == year]
    df_oscope = df_out[df_out['회계연도'] == year]

    return {'df_net_iscope': df_net_iscope, 'df_net_oscope': df_net_oscope,
            'df_iscope': df_iscope, 'df_oscope': df_oscope}


@cache.memoize(timeout=300)
def gen_bar_data(year):
    gstore = global_store(year)
    df_net_oscope = gstore['df_net_oscope']

    df_obar = df_net_oscope[['분야명', '부문명', '프로그램명', '전년도당초금액(천원)', '금년도국회확정(천원)']].sort_values('금년도국회확정(천원)', ascending=False)
    df_obar[['전년도당초금액(천원)', '금년도국회확정(천원)']] = df_obar[['전년도당초금액(천원)', '금년도국회확정(천원)']] / 1e5

    return {'df_obar': df_obar}


@cache.memoize(timeout=300)
def gen_pie_data(year):
    gstore = global_store(year)
    df_net_iscope = gstore['df_net_iscope']
    df_net_oscope = gstore['df_net_oscope']

    _ipie = df_net_iscope[['수입항명', '금년도국회확정(천원)']].groupby('수입항명', as_index=False).sum().sort_values('금년도국회확정(천원)',
                                                                                                     ascending=False)
    _ipie.iloc[9:, 0] = '기타'
    df_ipie = _ipie.groupby('수입항명', as_index=False).sum().sort_values('금년도국회확정(천원)', ascending=False)
    df_ipie['금년도국회확정(천원)'] = df_ipie['금년도국회확정(천원)'] / 1e5

    _opie = df_net_oscope[['분야명', '금년도국회확정(천원)']].groupby('분야명', as_index=False).sum().sort_values('금년도국회확정(천원)',
                                                                                                   ascending=False)
    _opie.iloc[9:, 0] = '기타'
    df_opie = _opie.groupby('분야명', as_index=False).sum().sort_values('금년도국회확정(천원)', ascending=False)
    df_opie['금년도국회확정(천원)'] = df_opie['금년도국회확정(천원)'] / 1e5

    return {'df_ipie': df_ipie, 'df_opie': df_opie}


@cache.memoize(timeout=300)
def gen_sankey_data(year):
    gstore = global_store(year)
    df_iscope = gstore['df_iscope']
    df_oscope = gstore['df_oscope']

    df_iflow_1 = df_iscope.groupby(['수입항명', '수입관명'], as_index=False)['금년도예산(천원)'].sum()
    df_iflow_1['수입항명'] = df_iflow_1['수입항명']
    df_iflow_1['수입관명'] = df_iflow_1['수입관명'] + ' '
    df_iflow_1['line_color'] = line_color_default
    df_iflow_1.loc[df_iflow_1['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    df_iflow_2 = df_iscope.groupby(['수입관명', '소관명'], as_index=False)['금년도예산(천원)'].sum()
    df_iflow_2['수입관명'] = df_iflow_2['수입관명'] + ' '
    df_iflow_2['소관명'] = df_iflow_2['소관명'] + ' '
    df_iflow_2['line_color'] = line_color_default
    df_iflow_2.loc[df_iflow_2['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    df_iflow_3 = df_iscope.groupby(['소관명', '회계명'], as_index=False)['금년도예산(천원)'].sum()
    df_iflow_3['소관명'] = df_iflow_3['소관명'] + ' '
    df_iflow_3['회계명'] = df_iflow_3['회계명']
    df_iflow_3['line_color'] = line_color_default
    df_iflow_3.loc[df_iflow_3['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    df_oflow_1 = df_oscope.groupby(['회계명', '소관명'], as_index=False)['금년도예산(천원)'].sum()
    df_oflow_1['회계명'] = df_oflow_1['회계명']
    df_oflow_1['소관명'] = ' ' + df_oflow_1['소관명']
    df_oflow_1['line_color'] = line_color_default
    df_oflow_1.loc[df_oflow_1['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    df_oflow_2 = df_oscope.groupby(['소관명', '부문명'], as_index=False)['금년도예산(천원)'].sum()
    df_oflow_2['소관명'] = ' ' + df_oflow_2['소관명']
    df_oflow_2['부문명'] = ' ' + df_oflow_2['부문명']
    df_oflow_2['line_color'] = line_color_default
    df_oflow_2.loc[df_oflow_2['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    df_oflow_3 = df_oscope.groupby(['부문명', '분야명'], as_index=False)['금년도예산(천원)'].sum()
    df_oflow_3['부문명'] = ' ' + df_oflow_3['부문명']
    df_oflow_3['분야명'] = df_oflow_3['분야명']
    df_oflow_3['line_color'] = line_color_default
    df_oflow_3.loc[df_oflow_3['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

    # Aggregate.
    node = pd.concat([df_iflow_1['수입항명'], df_iflow_1['수입관명'], df_iflow_2['소관명'], df_iflow_3['회계명'],
                      df_oflow_1['회계명'], df_oflow_1['소관명'], df_oflow_2['부문명'], df_oflow_3['분야명']]) \
        .drop_duplicates() \
        .reset_index(drop=True)

    source = pd.concat([df_iflow_1['수입항명'], df_iflow_2['수입관명'], df_iflow_3['소관명'],
                        df_oflow_1['회계명'], df_oflow_2['소관명'], df_oflow_3['부문명']]) \
        .map(lambda x: node[node == x].index.values[0]) \
        .reset_index(drop=True)

    target = pd.concat([df_iflow_1['수입관명'], df_iflow_2['소관명'], df_iflow_3['회계명'],
                        df_oflow_1['소관명'], df_oflow_2['부문명'], df_oflow_3['분야명']]) \
        .map(lambda x: node[node == x].index.values[0]) \
        .reset_index(drop=True)

    value = (pd.concat([df_iflow_1['금년도예산(천원)'], df_iflow_2['금년도예산(천원)'], df_iflow_3['금년도예산(천원)'],
                        df_oflow_1['금년도예산(천원)'], df_oflow_2['금년도예산(천원)'], df_oflow_3['금년도예산(천원)']]) / 1e5) \
        .reset_index(drop=True)

    color = pd.concat([df_iflow_1['line_color'], df_iflow_2['line_color'], df_iflow_3['line_color'],
                       df_oflow_1['line_color'], df_oflow_2['line_color'], df_oflow_3['line_color']]) \
        .reset_index(drop=True)

    return {'node': node, 'source': source, 'target': target, 'value': value, 'color': color}


def serve_layout():
    session_id = str(uuid.uuid4())

    return html.Div([
        html.Div(session_id, id='session-id', style={'display': 'none'}),

        html.H1('대한민국 정부 예산 대사', style={'textAlign': 'center', 'color': 'gray'}),
        html.H2('(Korean government budget reconciliation)', style={'textAlign': 'center', 'color': 'gray'}),

        html.Div([
            html.H3('메타 정보'),
            html.P('자료출처: 디지털예산회계시스템(http://www.openfiscaldata.go.kr/)'),
            html.P('원 데이터 이용허락조건: 출처표시-변경금지')
        ], style={'color': 'gray', 'marginTop': '5%', 'marginRight': '10%', 'marginBottom': '5%', 'marginLeft': '10%'}),

        html.Div([
            html.H3('대상연도', style={'textAlign': 'center', 'color': 'gray'}),
            dcc.Dropdown(
                id='scope_selection',
                options=[{'label': '{}'.format(y), 'value': y} for y in range(2007, 2019)],
                value=2018,
            )
        ], style={'marginTop': '5%', 'marginRight': '45%', 'marginBottom': '5%', 'marginLeft': '45%', }),

        # Pie
        html.Div([
            html.Div(
                dcc.Graph(
                    id='figure_in_pie',
                ), style={'width': '50%', 'display': 'inline-block'}),

            html.Div(
                dcc.Graph(
                    id='figure_out_pie',
                ), style={'width': '50%', 'display': 'inline-block'}),
        ], style={'marginTop': '5%', 'marginRight': '3%', 'marginLeft': '3%'}),

        html.Div([
            html.H3('분류체계'),
            html.P('분야: 정부 기능분류의 기본 틀 (예: 농림해양수산)'),
            html.P('부문: 정부 업무 분류의 기본 틀 (예: 해양수산·어촌)'),
            html.P('프로그램: 국가의 최소 정책단위로서 동일한 정책목표를 달성하기 위한 한 개 이상의 단위사업으로 구성 (예: 수산물 유통 및 안전관리)'),
            html.P('단위사업: 프로그램 달성을 위한 수단으로서 세부사업군(群)으로 구성 (예: 수산물 가격 안정)'),
        ], style={'color': 'gray', 'marginTop': '5%', 'marginRight': '10%', 'marginBottom': '5%', 'marginLeft': '10%'}),

        # Bar
        html.Div([
            html.Div(
                dcc.Graph(
                    id='figure_bar',
                    hoverData={'points': [{'x': '교육'}]},
                ), style={}),
        ], style={'marginTop': '5%', 'marginRight': '3%', 'marginLeft': '3%'}),

        html.Div([
            html.Div(
                dcc.Graph(
                    id='figure_out_bar_d1',
                    hoverData={'points': [{'x': '고등교육'}]},
                ), style={'width': '35%', 'display': 'inline-block'}
            ),

            html.Div(
                dcc.Graph(
                    id='figure_out_bar_d2',
                ), style={'width': '65%', 'display': 'inline-block'}
            ),
        ], style={'marginRight': '3%', 'marginLeft': '3%'}),

        # Sankey
        html.Div(
            dcc.Graph(
                id='figure_sankey',
            ), style={'marginTop': '5%'}
        ),
    ])


app.layout = serve_layout


@app.callback(Output('figure_in_pie', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_in_pie(year):
    scope = gen_pie_data(year)

    return {
        'data': [
            go.Pie(
                hole=.3,
                marker=dict(colors=pie_color, line=dict(color='white', width=2)),
                labels=scope['df_ipie']['수입항명'],
                values=scope['df_ipie']['금년도국회확정(천원)'],
                textposition='inside',
            )
        ],

        'layout': {
            'title': '{} 세입 예산 구성(억원)'.format(year),
        }
    }


@app.callback(Output('figure_out_pie', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_out_pie(year):
    scope = gen_pie_data(year)

    return {
        'data': [
            go.Pie(
                hole=.3,
                marker=dict(colors=pie_color, line=dict(color='white', width=2)),
                labels=scope['df_opie']['분야명'],
                values=scope['df_opie']['금년도국회확정(천원)'],
                textposition='inside',
            )
        ],

        'layout': {
            'title': '{} 세출 예산 구성(억원)'.format(year),
        }
    }


@app.callback(Output('figure_bar', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_bar(year):
    scope = gen_bar_data(year)

    d_ly = scope['df_obar'][['분야명', '전년도당초금액(천원)']].groupby('분야명', as_index=False).sum()
    d_cy = scope['df_obar'][['분야명', '금년도국회확정(천원)']].groupby('분야명', as_index=False).sum()

    return {
        'data': [
            go.Bar(
                x=d_ly['분야명'],
                y=d_ly['전년도당초금액(천원)'],
                name='전년도',
                marker=dict(color=bar_color_last),
            ),
            go.Bar(
                x=d_cy['분야명'],
                y=d_cy['금년도국회확정(천원)'],
                name='기준연도',
                marker=dict(color=bar_color_current),
            )
        ],

        'layout': {
            'title': '{} 세출 예산 분야별/부문별/프로그램별 상세(억원)'.format(year),
            'xaxis': dict(showgrid=False),
            'yaxis': dict(showgrid=False),
            'showlegend': False,
        }
    }


@app.callback(Output('figure_out_bar_d1', 'figure'), [Input('scope_selection', 'value'), Input('figure_bar', 'hoverData')])
def generate_figure_out_bar_d1(year, hoverData):
    scope = gen_bar_data(year)

    h = hoverData['points'][0]['x']
    d = scope['df_obar'].loc[scope['df_obar']['분야명'] == h, ['부문명', '전년도당초금액(천원)', '금년도국회확정(천원)']]
    d_ly = d[['부문명', '전년도당초금액(천원)']].groupby('부문명', as_index=False).sum()
    d_cy = d[['부문명', '금년도국회확정(천원)']].groupby('부문명', as_index=False).sum()

    return {
        'data': [
            go.Bar(
                x=d_ly['부문명'],
                y=d_ly['전년도당초금액(천원)'],
                name='전년도',
                marker=dict(color=bar_color_last),
            ),
            go.Bar(
                x=d_cy['부문명'],
                y=d_cy['금년도국회확정(천원)'],
                name='기준연도',
                marker=dict(color=bar_color_current),
            ),
        ],

        'layout': {
            'title': h,
            'xaxis': dict(showgrid=False),
            'yaxis': dict(showgrid=False),
            'showlegend': False,
        }
    }


@app.callback(Output('figure_out_bar_d2', 'figure'), [Input('scope_selection', 'value'), Input('figure_out_bar_d1', 'hoverData')])
def generate_figure_out_bar_d2(year, hoverData):
    scope = gen_bar_data(year)

    h = hoverData['points'][0]['x']
    d = scope['df_obar'].loc[scope['df_obar']['부문명'] == h, ['프로그램명', '전년도당초금액(천원)', '금년도국회확정(천원)']]
    d_ly = d[['프로그램명', '전년도당초금액(천원)']].groupby('프로그램명', as_index=False).sum()
    d_cy = d[['프로그램명', '금년도국회확정(천원)']].groupby('프로그램명', as_index=False).sum()

    return {
        'data': [
            go.Bar(
                x=d_ly['프로그램명'],
                y=d_ly['전년도당초금액(천원)'],
                name='전년도',
                marker=dict(color=bar_color_last),
            ),
            go.Bar(
                x=d_cy['프로그램명'],
                y=d_cy['금년도국회확정(천원)'],
                name='기준연도',
                marker=dict(color=bar_color_current),
            ),
        ],

        'layout': {
            'title': h,
            'xaxis': dict(showgrid=False),
            'yaxis': dict(showgrid=False),
            'showlegend': False,
        }
    }


@app.callback(Output('figure_sankey', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_sankey(year):
    scope = gen_sankey_data(year)

    return {
        'data': [
            go.Sankey(
                opacity=0.5,
                domain={'x': [0, 1], 'y': [0, 1]},
                orientation='h',
                textfont={'size': 10},
                arrangement='freeform',
                node=dict(
                    pad=12,
                    thickness=10,
                    line=dict(width=0),
                    label=scope['node'],
                    color=node_color
                ),
                link=dict(
                    source=scope['source'],
                    target=scope['target'],
                    value=scope['value'],
                    color=scope['color']
                ),
            )
        ],

        'layout': {
            'title': '{} 정부 세입/세출 예산편성현황(억원)'.format(year),
            'height': 2048
        }
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0')
    # app.run_server(host='127.0.0.1')
