import os
import pandas as pd

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly as py
import plotly.graph_objs as go


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


class ScopeControl:
    def __init__(self, year):
        self.year = year

        self.df_net_iscope = df_net_in[df_net_in['회계연도'] == self.year]
        self.df_net_oscope = df_net_out[df_net_out['회계연도'] == self.year]

        self.df_iscope = df_in[df_in['회계연도'] == self.year]
        self.df_oscope = df_out[df_out['회계연도'] == self.year]

    def gen_bar_data(self):
        self.df_obar = self.df_net_oscope[['분야명', '부문명', '프로그램명', '전년도당초금액(천원)', '금년도정부안(천원)']].sort_values('금년도정부안(천원)', ascending=False)
        self.df_obar[['전년도당초금액(천원)', '금년도정부안(천원)']] = self.df_obar[['전년도당초금액(천원)', '금년도정부안(천원)']]

    def gen_pie_data(self):
        _ipie = self.df_net_iscope[['수입항명', '금년도정부안(천원)']].groupby('수입항명', as_index=False).sum().sort_values('금년도정부안(천원)', ascending=False)
        _ipie.iloc[9:, 0] = '기타'
        self.df_ipie = _ipie.groupby('수입항명', as_index=False).sum().sort_values('금년도정부안(천원)', ascending=False)
        self.df_ipie['금년도정부안(천원)'] = self.df_ipie['금년도정부안(천원)']

        _opie = self.df_net_oscope[['분야명', '금년도정부안(천원)']].groupby('분야명', as_index=False).sum().sort_values('금년도정부안(천원)', ascending=False)
        _opie.iloc[9:, 0] = '기타'
        self.df_opie = _opie.groupby('분야명', as_index=False).sum().sort_values('금년도정부안(천원)', ascending=False)
        self.df_opie['금년도정부안(천원)'] = self.df_opie['금년도정부안(천원)']

    def gen_sankey_data(self):
        df_iflow_1 = self.df_iscope.groupby(['수입항명', '수입관명'], as_index=False)['금년도예산(천원)'].sum()
        df_iflow_1['수입항명'] = df_iflow_1['수입항명']
        df_iflow_1['수입관명'] = df_iflow_1['수입관명'] + ' '
        df_iflow_1['line_color'] = line_color_default
        df_iflow_1.loc[df_iflow_1['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        df_iflow_2 = self.df_iscope.groupby(['수입관명', '소관명'], as_index=False)['금년도예산(천원)'].sum()
        df_iflow_2['수입관명'] = df_iflow_2['수입관명'] + ' '
        df_iflow_2['소관명'] = df_iflow_2['소관명'] + ' '
        df_iflow_2['line_color'] = line_color_default
        df_iflow_2.loc[df_iflow_2['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        df_iflow_3 = self.df_iscope.groupby(['소관명', '회계명'], as_index=False)['금년도예산(천원)'].sum()
        df_iflow_3['소관명'] = df_iflow_3['소관명'] + ' '
        df_iflow_3['회계명'] = df_iflow_3['회계명']
        df_iflow_3['line_color'] = line_color_default
        df_iflow_3.loc[df_iflow_3['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        df_oflow_1 = self.df_oscope.groupby(['회계명', '소관명'], as_index=False)['금년도예산(천원)'].sum()
        df_oflow_1['회계명'] = df_oflow_1['회계명']
        df_oflow_1['소관명'] = ' ' + df_oflow_1['소관명']
        df_oflow_1['line_color'] = line_color_default
        df_oflow_1.loc[df_oflow_1['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        df_oflow_2 = self.df_oscope.groupby(['소관명', '부문명'], as_index=False)['금년도예산(천원)'].sum()
        df_oflow_2['소관명'] = ' ' + df_oflow_2['소관명']
        df_oflow_2['부문명'] = ' ' + df_oflow_2['부문명']
        df_oflow_2['line_color'] = line_color_default
        df_oflow_2.loc[df_oflow_2['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        df_oflow_3 = self.df_oscope.groupby(['부문명', '분야명'], as_index=False)['금년도예산(천원)'].sum()
        df_oflow_3['부문명'] = ' ' + df_oflow_3['부문명']
        df_oflow_3['분야명'] = df_oflow_3['분야명']
        df_oflow_3['line_color'] = line_color_default
        df_oflow_3.loc[df_oflow_3['금년도예산(천원)'].sort_values(ascending=False).index[:top_n], 'line_color'] = line_color

        # Aggregate.
        self.node = pd.concat([df_iflow_1['수입항명'], df_iflow_1['수입관명'], df_iflow_2['소관명'], df_iflow_3['회계명'],
                               df_oflow_1['회계명'], df_oflow_1['소관명'], df_oflow_2['부문명'], df_oflow_3['분야명']])\
            .drop_duplicates()\
            .reset_index(drop=True)

        self.source = pd.concat([df_iflow_1['수입항명'], df_iflow_2['수입관명'], df_iflow_3['소관명'],
                                 df_oflow_1['회계명'], df_oflow_2['소관명'], df_oflow_3['부문명']])\
            .map(lambda x: self.node[self.node == x].index.values[0])\
            .reset_index(drop=True)

        self.target = pd.concat([df_iflow_1['수입관명'], df_iflow_2['소관명'], df_iflow_3['회계명'],
                                 df_oflow_1['소관명'], df_oflow_2['부문명'], df_oflow_3['분야명']])\
            .map(lambda x: self.node[self.node == x].index.values[0])\
            .reset_index(drop=True)

        self.value = (pd.concat([df_iflow_1['금년도예산(천원)'], df_iflow_2['금년도예산(천원)'], df_iflow_3['금년도예산(천원)'],
                                 df_oflow_1['금년도예산(천원)'], df_oflow_2['금년도예산(천원)'], df_oflow_3['금년도예산(천원)']]) / 10e4)\
            .reset_index(drop=True)

        self.color = pd.concat([df_iflow_1['line_color'], df_iflow_2['line_color'], df_iflow_3['line_color'],
                                df_oflow_1['line_color'], df_oflow_2['line_color'], df_oflow_3['line_color']])\
            .reset_index(drop=True)

# Backend init
scope = ScopeControl(2018)

# App
app = dash.Dash()

# Append an externally hosted CSS stylesheet
# app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})

app.layout = html.Div([
                html.Div(
                    dcc.Dropdown(
                        id='scope_selection',
                        options=[{'label': '{}'.format(y), 'value': y} for y in range(2007, 2019)],
                        value=2018,
                    ), style={'margin-left': '3%', 'margin-right': '3%'}),

                # In
                html.Div([
                    html.Div(
                        dcc.Graph(
                            id='figure_in_pie',
                        ), style={'width': '50%', 'display': 'inline-block'}),

                    html.Div(
                        dcc.Graph(
                            id='figure_out_pie',
                        ), style={'width': '50%', 'display': 'inline-block'}),
                ], style={'margin-left': '3%', 'margin-right': '3%'}),

                # Out
                html.Div([
                    html.Div(
                        dcc.Graph(
                            id='figure_bar',
                            hoverData={'points': [{'x': '교육'}]},
                        ), style={}),
                ], style={'margin-left': '3%', 'margin-right': '3%'}),

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
                ], style={'margin-left': '3%', 'margin-right': '3%'}),

                html.Div(
                    dcc.Graph(
                        id='figure_sankey',
                    )
                ),
            ])


@app.callback(Output('figure_in_pie', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_in_pie(year):
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_pie_data()

    return {
        'data': [
            go.Pie(
                hole=.3,
                marker=dict(colors=pie_color, line=dict(color='white', width=2)),
                labels=scope.df_ipie['수입항명'],
                values=scope.df_ipie['금년도정부안(천원)'],
                textposition='inside',
            )
        ],

        'layout': {
            'title': '{} 세입 예산 구성'.format(scope.year),
        }
    }


@app.callback(Output('figure_out_pie', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_out_pie(year):
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_pie_data()

    return {
        'data': [
            go.Pie(
                hole=.3,
                marker=dict(colors=pie_color, line=dict(color='white', width=2)),
                labels=scope.df_opie['분야명'],
                values=scope.df_opie['금년도정부안(천원)'],
                textposition='inside',
            )
        ],

        'layout': {
            'title': '{} 세출 예산 구성'.format(scope.year),
        }
    }


@app.callback(Output('figure_bar', 'figure'), [Input('scope_selection', 'value')])
def generate_figure_bar(year):
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_bar_data()

    d_ly = scope.df_obar[['분야명', '전년도당초금액(천원)']].groupby('분야명', as_index=False).sum()
    d_cy = scope.df_obar[['분야명', '금년도정부안(천원)']].groupby('분야명', as_index=False).sum()

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
                y=d_cy['금년도정부안(천원)'],
                name='기준연도',
                marker=dict(color=bar_color_current),
            )
        ],

        'layout': {
            'title': '{} 세출 예산 상세(전년대비)'.format(scope.year),
            'xaxis': dict(showgrid=False),
            'yaxis': dict(showgrid=False),
            'showlegend': False,
        }
    }


@app.callback(Output('figure_out_bar_d1', 'figure'), [Input('scope_selection', 'value'), Input('figure_bar', 'hoverData')])
def generate_figure_out_bar_d1(year, hoverData):
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_bar_data()

    h = hoverData['points'][0]['x']
    d = scope.df_obar.loc[scope.df_obar['분야명'] == h, ['부문명', '전년도당초금액(천원)', '금년도정부안(천원)']]
    d_ly = d[['부문명', '전년도당초금액(천원)']].groupby('부문명', as_index=False).sum()
    d_cy = d[['부문명', '금년도정부안(천원)']].groupby('부문명', as_index=False).sum()

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
                y=d_cy['금년도정부안(천원)'],
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
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_bar_data()

    h = hoverData['points'][0]['x']
    d = scope.df_obar.loc[scope.df_obar['부문명'] == h, ['프로그램명', '전년도당초금액(천원)', '금년도정부안(천원)']]
    d_ly = d[['프로그램명', '전년도당초금액(천원)']].groupby('프로그램명', as_index=False).sum()
    d_cy = d[['프로그램명', '금년도정부안(천원)']].groupby('프로그램명', as_index=False).sum()

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
                y=d_cy['금년도정부안(천원)'],
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
    global scope
    if year != scope.year:
        scope = ScopeControl(year)

    scope.gen_sankey_data()

    return {
        'data': [
            go.Sankey(
                opacity=0.5,
                domain={'x': [0, 1], 'y': [0, 1]},
                orientation='h',
                textfont={'size': 10},
                valueformat=',.2f',
                valuesuffix=' 억원',
                arrangement='freeform',
                node=dict(
                    pad=12,
                    thickness=10,
                    line=dict(width=0),
                    label=scope.node,
                    color=node_color
                    ),
                link=dict(
                    source=scope.source,
                    target=scope.target,
                    value=scope.value,
                    color=scope.color
                    ),
                )
            ],

        'layout': {
            'title': '{} 정부 세입/세출 예산편성현황'.format(scope.year),
            'height': 2048
            }
        }


if __name__ == '__main__':
    app.run_server(debug=False)
