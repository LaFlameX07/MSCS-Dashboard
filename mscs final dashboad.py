import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output
from flask import Flask
import warnings

external_stylesheets = ['https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css']

server = Flask(__name__)
app = dash.Dash(__name__, external_stylesheets=external_stylesheets,server=server)
app.title='MSCS:Multi State Cooperative Societies'
custom_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load the Google Sheets data into a DataFrame
def load_data():
    SHEET_ID = '16l0tKPD7PCbZZXd01XYAL-95C9lnSJK-'
    sheet_names = ['Table 1', 'Table 2', 'Table 3', 'Table 4']  # Replace with your sheet names
    df_list = []

    for sheet_name in sheet_names:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        df = pd.read_csv(url)
        df['Date of Registration'] = pd.to_datetime(df['Date of Registration'], format='%d/%m/%Y')
        df_list.append(df)

    # Concatenate all the dataframes into a single dataframe
    df = pd.concat(df_list, ignore_index=True)
    return df

def create_stacked_bar_chart(df):
    by_sector_type = df.groupby(['State', 'Sector Type'])['Name of Society'].count().reset_index()
    sector_district_count = df.groupby(['Sector Type', 'District']).size().reset_index().groupby('Sector Type')[0].count().reset_index().rename(columns={0: 'Count'})
    stacked_bar_chart = px.bar(by_sector_type, x='State', y='Name of Society', color='Sector Type', title='Distribution of Societies by Sector and State')
    table = dash_table.DataTable(
        id='district_count_table',  # Add an ID to the table
        columns=[{'name': 'Sector Type', 'id': 'Sector Type'},
                 {'name': 'Count of Districts', 'id': 'Count'}],
        data=sector_district_count.to_dict('records'),
        style_table={'width': '100%'},
        style_cell={
            'textAlign': 'center',
            'font-family': 'Helvetica, sans-serif',
            'backgroundColor': '#f7f7f7'
        },
        style_header={
            'backgroundColor': '#1f77b4',
            'fontWeight': 'bold',
            'color': 'white',
            'font-family': 'Helvetica, sans-serif'
        }
    )
    total_count_container = html.Div(
        id='societies_count',
        children=[
            html.Div(
                children=[
                    html.H3("Total Societies:"),
                    html.P(f"{by_sector_type['Name of Society'].sum()+1}")
                ],
                style={
                    "border-radius": "5px",
                    "border": "1px solid #ccc",
                    "padding": "10px",
                    "margin-bottom": "10px",
                    "text-align": "center"
                }
            )
        ]
    )
    return stacked_bar_chart, table, total_count_container

@app.callback(
    Output('line_graph', 'figure'),
    Output('pie_chart_states', 'figure'),
    Output('pie_chart_societies', 'figure'),
    Output('bar_chart_districts', 'figure'),
    Output('stacked_bar_chart', 'figure'),
    Output('district_count_table', 'children'),
    Output('societies_count','children'),# Add the table as an output
    Input('dummy', 'children'),
    Input('scatter_option', 'value')
    )

def update_components(dummy, scatter_value):
    df = load_data()

    # Group the data by date and calculate the total count of registrations at each date
    registration_count = df.groupby('Date of Registration').size().cumsum()

    # Create the line graph figure
    line_graph = go.Figure()
    line_graph.add_trace(go.Scatter(
        x=registration_count.index,

        y=registration_count.values,
        mode='lines+markers',
        name='Total Registrations',
        line=dict(color='#1f77b4'),
        marker=dict(symbol='circle', size=5, color='#1f77b4')
    ))
    line_graph.update_layout(
        title='Total Registrations Over Time',
        xaxis=dict(title='Date of Registration'),
        yaxis=dict(title='Total Count of Registrations'),
        font=dict(family='Helvetica, sans-serif')
    )

    # Pie chart for Sector Type and Number of States
    sector_states = df.groupby('Sector Type')['State'].nunique().reset_index().rename(columns={'State': 'Number of States'})
    pie_chart_states = px.pie(sector_states, names='Sector Type', values='Number of States', title='Sector Type and Number of States')

    # Pie chart for Sector Type and Number of Societies
    sector_societies = df.groupby('Sector Type')['Name of Society'].count().reset_index().rename(columns={'Name of Society': 'Number of Societies'})
    pie_chart_societies = px.pie(sector_societies, names='Sector Type', values='Number of Societies', title='Sector Type and Number of Societies')

    # Create the horizontal bar chart figure
    top_10_districts = df['District'].value_counts().head(10).reset_index()
    top_10_districts.columns = ['District', 'Number of Societies']

    bar_chart_districts = go.Figure(go.Bar(
        y=top_10_districts['District'],
        x=top_10_districts['Number of Societies'],
        orientation='h',
        marker=dict(color='#1f77b4')
    ))
    bar_chart_districts.update_layout(
        title='Top 10 Districts with Most Societies',
        xaxis=dict(title='Number of Societies'),
        yaxis=dict(title='District', autorange="reversed"),
        font=dict(family='Helvetica, sans-serif')
    )

    stacked_bar_chart, district_count_table, societies_count = create_stacked_bar_chart(df)  # Include the table

    return line_graph, pie_chart_states, pie_chart_societies, bar_chart_districts, stacked_bar_chart, district_count_table, societies_count

@app.callback(
    Output('scatter_plot', 'figure'),
    [Input('dummy', 'children')],
    [Input('scatter_option', 'value')]
)
def update_scatter_plot(dummy, scatter_value):
    df = load_data()

    # Remove rows with missing data
    df = df.dropna(subset=['District', 'Sector Type', 'Name of Society'])

    # Group data by state or district and sector type
    if scatter_value == 'district':
        group_cols = ['District', 'Sector Type']
        name_col = 'District'
    else:
        group_cols = ['State', 'Sector Type']
        name_col = 'State'

    group = df.groupby(group_cols, as_index=False)['Name of Society'].count()

    # Find the most dominant sector for each state or district
    dominant_sector = group.groupby(name_col)['Name of Society'].idxmax()
    dominant_group = group.loc[dominant_sector]

    # Map each sector type to a specific color
    colors_dict = {}
    all_sector_types = df['Sector Type'].unique()
    for i, sector_type in enumerate(all_sector_types):
        colors_dict[sector_type] = px.colors.qualitative.Alphabet[i % len(px.colors.qualitative.Alphabet)]

    scatter_plot = go.Figure()
    for i, row in dominant_group.iterrows():
        # Get the state or district and dominant sector for this row
        name = row[name_col]
        dominant = row['Sector Type']

        # Get the total number of societies for this state or district
        total_societies = group[group[name_col] == name]['Name of Society'].sum()

        # Specify the diameter for the marker based on the total number of societies
        diameter = 20 + (total_societies / 100) ** 2
        min_radius=5
        marker_size=35
        # Create a single marker for this state or district
        scatter_plot.add_trace(go.Scatter(
            x=[name],
            y=[total_societies],
            mode='markers',
            marker=dict(
                sizemode='diameter',
                sizeref=diameter/25,
                sizemin=min_radius,
                symbol='circle',
                size=marker_size,
                color=colors_dict.get(dominant, 'grey')  # Assign the corresponding color for the dominant sector type
            ),
            hovertemplate=f'{name}: {total_societies} Societies<br>Dominant Sector: {dominant}<br>Percentage of Dominant Sector: {row["Name of Society"] / total_societies:.0%}'
        ))

    scatter_plot.update_layout(
        title=f'Number of Societies by {name_col}',
        xaxis=dict(title=name_col),
        yaxis=dict(title='Number of Societies'),
        showlegend=False,
        font=dict(family='Helvetica, sans-serif')
    )

    return scatter_plot

app.layout = html.Div(children=[
    html.Div(
        className='top-section',
        style={
            'background-color': '#006400',
            'position': 'relative',
            'overflow': 'hidden',
            'padding': '5%'
        },
        children=[
            html.Img(
                src='https://static.vecteezy.com/system/resources/previews/002/535/835/non_2x/light-blue-green-background-with-spots-abstract-decorative-design-in-gradient-style-with-bubbles-pattern-for-wallpapers-curtains-vector.jpg',
                style={
                    'position': 'absolute',
                    'top': '5px',
                    'left': '5px',
                    'bottom':'5px',
                    'right':'5px',
                    'object-fit': 'contain',
                    'opacity':'0.7'
                }
            ),
            html.Img(
                src='https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg',
                style={
                    'position': 'absolute',
                    'top': '60px',
                    'left': '10%',
                    'width': '150px',
                    'height': '150px',
                }
            ),
            html.Div(
                className='text-container',
                children=[
                    html.H1("MSCS: Multi State Cooperative Societies", style={'color': 'white'}),
                    html.H3("Ministry of Cooperation, Govt. of India", style={'color': '#ADFF9E'}),
                ],
                style={'text-align': 'center', 'margin-top': '50px','position': 'relative', 'z-index': '1'}
            ),
            html.Img(
                src='https://st.adda247.com/https://s3-ap-south-1.amazonaws.com/adda247jobs-wp-assets-adda247/articles/wp-content/uploads/2022/12/13174508/Multi-State-Cooperative-Societies-Amendment-Bill-2022.jpg',
                style={
                    'position': 'absolute',
                    'top': '60px',
                    'right': '10%',
                    'width': '150px',
                    'height': '150px',
                }
            ),
        ]
    ),
    html.Div(className='visualization-row', children=[
        html.Div(className='visualization-column', style={'width': '40%', 'margin':'20px', 'padding':'20px'}, children=[
            html.H2('               Total Count of Societies:-'),
            html.Div(id='societies_count',style={'border': '5px ridge #E2E2E2'})
        ]),
        html.Div(className='visualization-column', style={'width': '50%', 'margin':'20px', 'padding':'20px', 'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Count of Districts for Each Sector Type'),
            html.Div(id='district_count_table', style={'margin-bottom': '20px', 'padding':'20px'})
        ])        
    ], style={'display': 'flex', 'align-items': 'justify'}),
    html.Div(className='visualization-row', children=[
        html.Div(className='visualization-column', style={'width': '50%', 'margin':'20px', 'padding':'20px', 'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Pie Chart - States'),
            dcc.Graph(id='pie_chart_states')
        ]),
        html.Div(className='visualization-column', style={'width': '50%', 'margin':'20px', 'padding':'20px', 'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Pie Chart - Societies'),
            dcc.Graph(id='pie_chart_societies')
        ])
    ], style={'display': 'flex'}),
    html.Div(className='visualization-row', children=[
        html.Div(className='visualization-column', style={'width': '65%', 'margin':'20px', 'padding':'20px', 'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Line Graph'),
            dcc.Graph(id='line_graph')
        ]),
        html.Div(className='visualization-column', style={'width': '35%', 'margin':'20px', 'padding':'20px', 'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Bar Chart - Districts'),
            dcc.Graph(id='bar_chart_districts')
        ])
    ], style={'display': 'flex'}),
    html.Div(className='visualization-row', style={'margin':'20px', 'padding':'20px'}, children=[
        html.Div(className='visualization-column', style={'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Stacked Bar Chart'),
            dcc.Graph(id='stacked_bar_chart')
        ])
    ]),
    html.Div(className='visualization-row', style={'margin':'20px', 'padding':'20px'}, children=[
        html.Div(className='visualization-column', style={'border': '5px ridge #E2E2E2'}, children=[
            html.H2('Scatter Plot'),
            dcc.Graph(id='scatter_plot')
        ])
    ]),
    html.Div(
        id='dummy',
        style={'display': 'flex'}  # Hide the dummy element
    ),
    html.Div(
        id='scatter_option_container',
        children=[
            html.Label('Group Scatter Plot by:'),
            dcc.RadioItems(
                id='scatter_option',
                options=[
                    {'label': 'State', 'value': 'state'},
                    {'label': 'District', 'value': 'district'}
                ],
                value='state',
                labelStyle={'display': 'inline-block', 'margin-right': '10px'}
            )
        ],
        style={'margin-top': '20px', 'margin-bottom': '20px', 'text-align': 'center'}
    ),
])

if __name__ == '__main__':
    app.run_server(debug=True)
