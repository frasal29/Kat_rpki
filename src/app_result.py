import dash
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import networkx as nx
import threading

# Main function to run the Dash app
def run_dash_app(as_data, results, saved_nodes):
    """
    Launch the Dash app to visualize the AS topology and attack impact.

    :param as_data: Dictionary containing AS topology data.
    :param results: Results of the attack analysis (red/green nodes and edges).
    :param saved_nodes: Saved node configurations for RPKI, Collectors, Hacker, and Victim.
    """
    start_as = list(as_data.keys())[0]  # Start from the root AS

    def build_graph_from_topology(as_data):
        """
        Construct a directed graph from the AS topology.

        :param as_data: Dictionary containing AS topology data.
        :return: A directed graph (NetworkX DiGraph).
        """
        G = nx.DiGraph()

        def add_to_graph(node):
            # Add child nodes (customer-to-provider relationship)
            for child in as_data[node].get("p2c", []):
                G.add_edge(node, child, relation="c2p", color=None)
                add_to_graph(child)

            # Add peer nodes (peer-to-peer relationship)
            for peer in as_data[node].get("p2p", []):
                if not G.has_edge(node, peer):  # Avoid duplicate edges
                    G.add_edge(node, peer, relation="p2p", color=None)
                    G.add_edge(peer, node, relation="p2p", color=None)

        add_to_graph(start_as)
        return G

    G = build_graph_from_topology(as_data)  # Build the graph

    # Use Graphviz layout to position the nodes in a tree structure
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot", root=start_as)

    # Assign calculated positions to each node in the graph
    for node in G.nodes:
        x, y = pos[node]
        G.nodes[node]['pos'] = (x, y)

    traceRecode = []  # List to hold all graph traces (nodes and edges)

    # Define edge colors for different relationship types
    edge_colors = {
        'c2p': 'rgba(211, 211, 211, 0.5)',
        'p2c': 'rgba(211, 211, 211, 0.5)',
        'p2p': 'rgba(105, 105, 105, 0.5)'
    }

    # Function to create the figure (visualization of the graph)
    def create_figure(selected_square_nodes=None, selected_blackCircle_nodes=None, selected_red_node=None, 
                      selected_green_node=None, red_nodes=None, green_nodes=None, red_edges=None, 
                      green_edges=None, xaxis_range=None, yaxis_range=None):
        """
        Generate the Plotly figure for the AS topology visualization.

        :param selected_square_nodes: Nodes marked as RPKI-enabled.
        :param selected_blackCircle_nodes: Nodes marked as Collectors.
        :param selected_red_node: Node identified as the Hacker.
        :param selected_green_node: Node identified as the Victim.
        :param red_nodes: Nodes affected by the attack.
        :param green_nodes: Nodes unaffected by the attack.
        :param red_edges: Edges impacted by the attack.
        :param green_edges: Edges unaffected by the attack.
        :param xaxis_range: X-axis range for zoom.
        :param yaxis_range: Y-axis range for zoom.
        :return: A Plotly figure.
        """
        traceRecode = []  # Reset trace list for each figure update

        # Initialize lists to store edge coordinates based on types
        p2p_edges_x = []
        p2p_edges_y = []
        c2p_edges_x = []
        c2p_edges_y = []
        red_edges_x = []
        red_edges_y = []
        green_edges_x = []
        green_edges_y = []
        red_green_edges_x = []
        red_green_edges_y = []

        # Iterate over edges in the graph to classify and collect coordinates
        for edge in G.edges:
            x0, y0 = G.nodes[edge[1]]['pos']
            x1, y1 = G.nodes[edge[0]]['pos']
            edge_str = f"{edge[0]}->{edge[1]}"
            edge_str_rev = f"{edge[1]}->{edge[0]}"
            relation = G.edges[edge]['relation']
            
            if (edge_str in red_edges or edge_str_rev in red_edges) and (edge_str in green_edges or edge_str_rev in green_edges):
                red_green_edges_x.extend([x0, x1, None])
                red_green_edges_y.extend([y0, y1, None])
                continue

            elif edge_str in red_edges or edge_str_rev in red_edges:
                red_edges_x.extend([x0, x1, None])
                red_edges_y.extend([y0, y1, None])
                continue

            elif edge_str in green_edges or edge_str_rev in green_edges:
                green_edges_x.extend([x0, x1, None])
                green_edges_y.extend([y0, y1, None])
                continue

            elif relation == 'p2p':
                p2p_edges_x.extend([x0, x1, None])
                p2p_edges_y.extend([y0, y1, None])

            elif relation in ['c2p', 'p2c']:
                c2p_edges_x.extend([x0, x1, None])
                c2p_edges_y.extend([y0, y1, None])

        # Append traces for each edge type
        p2p_trace = go.Scatter(
            x=p2p_edges_x,
            y=p2p_edges_y,
            mode='lines',
            line={'width': 1.6, 'color': 'rgba(105, 105, 105, 0.5)'},
            opacity=1,
            hoverinfo='skip',
            name='peer-to-peer (bidirectional)',
            showlegend=True
        )
        traceRecode.append(p2p_trace)

        c2p_trace = go.Scatter(
            x=c2p_edges_x,
            y=c2p_edges_y,
            mode='lines',
            line={'width': 1.6, 'color': 'rgba(211, 211, 211, 0.5)'},
            opacity=1,
            hoverinfo='skip',
            name='customer-to-provider',
            showlegend=True
        )
        traceRecode.append(c2p_trace)

        red_edge_trace = go.Scatter(
            x=red_edges_x,
            y=red_edges_y,
            mode='lines',
            line={'width': 1.6, 'color': 'rgba(255, 99, 71, 0.5)'},
            opacity=1,
            hoverinfo='skip',
            name='route-advertising-attack',
            showlegend=True
        )
        traceRecode.append(red_edge_trace)
        
        green_edge_trace = go.Scatter(
            x=green_edges_x,
            y=green_edges_y,
            mode='lines',
            line={'width': 1.6, 'color': 'rgba(0, 128, 0, 0.5)'},
            opacity=1,
            hoverinfo='skip',
            name='route-not-affecting-by-attack',
            showlegend=True
        )
        traceRecode.append(green_edge_trace)

        red_green_edge_trace = go.Scatter(
            x=red_green_edges_x,
            y=red_green_edges_y,
            mode='lines',
            line={'width': 1.6, 'color': 'rgba(255, 255, 0, 0.5)'},
            opacity=1,
            hoverinfo='skip',
            name='route-both-attack-not-attack',
            showlegend=True
        )
        traceRecode.append(red_green_edge_trace)

        not_rpki_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(0,0,0,0)',
                line=dict(width=2, color='rgba(211, 211, 211, 0.5)'),
                symbol='circle'
            ),
            name='NotRPKI',
            showlegend=True
        )

        rpki_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(0,0,0,0)',
                line=dict(width=2, color='rgba(211, 211, 211, 0.5)'),
                symbol='square'
            ),
            name='RPKI',
            showlegend=True
        )

        collector_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(0,0,0,0)',  # Trasparent
                line=dict(width=2, color='rgba(0, 0, 0, 0.3)')
            ),
            name='Collector',
            showlegend=True
        )

        hacker_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(139, 0, 0, 0.7)',
                line=dict(width=2, color='rgba(139, 0, 0, 0.7)'),
                symbol='circle'
            ),
            name='Hacker',
            showlegend=True
        )

        victim_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(173, 255, 47, 0.7)',
                line=dict(width=2, color='rgba(173, 255, 47, 0.7)'),
                symbol='circle'
            ),
            name='Victim',
            showlegend=True
        )

        as_hijacked_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(255, 99, 71, 0.7)',
                line=dict(width=2, color='rgba(255, 99, 71, 0.7)'),
                symbol='circle'
            ),
            name='AS hijacked',
            showlegend=True
        )
        
        as_not_affected_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(0, 128, 0, 0.7)',
                line=dict(width=2, color='rgba(0, 128, 0, 0.7)'),
                symbol='circle'
            ),
            name='AS not-affected',
            showlegend=True
        )

        # Add trace to the legend
        traceRecode.append(not_rpki_trace)
        traceRecode.append(rpki_trace)
        traceRecode.append(collector_trace)
        traceRecode.append(hacker_trace)
        traceRecode.append(victim_trace)
        traceRecode.append(as_hijacked_trace)
        traceRecode.append(as_not_affected_trace)

        # Create node traces
        node_trace = go.Scatter(
            x=[],
            y=[],
            mode='markers+text',  # Add 'text' to include labels
            hoverinfo="text",
            marker={
                'size': 40,
                'color': [],  # Fill colors
                'line': {'width': 4, 'color': []},  # Border colors
                'symbol': [] # Circle or square
            },
            text=[],  # Add the node names as text for labels
            textposition='middle center',  # Position text in the center of the nodes
            hovertext=[],  # Add hovertext for clickData
            showlegend=False
        )

        for node in G.nodes():
            x, y = G.nodes[node]['pos']
            node_trace['x'] += tuple([x])
            node_trace['y'] += tuple([y])
            node_trace['text'] += tuple([node])  # Use node names as text labels
            node_trace['hovertext'] += tuple([node])  # Use node names for hovertext

            # Determine color (red for HACKER, green VICTIM)
            if node in red_nodes:
                if node == selected_red_node:
                    node_color = 'rgba(139, 0, 0, 0.7)'
                else:
                    node_color = 'rgba(255, 99, 71, 0.7)'  # HACKER node
            elif node in green_nodes:
                if node == selected_green_node:
                    node_color = 'rgba(173, 255, 47, 0.7)'
                else:
                    node_color = 'rgba(0, 128, 0, 0.7)'  # VICTIM node
            else:
                node_color = 'rgba(135, 206, 235, 0.7)'

            # Determine color/shape inside node(square if RPKI mode)
            if node in selected_square_nodes:
                node_shape = 'square' # change shape to square for RPKI
            else:
                node_shape = 'circle'

            # Determine node border color (black if collector mode)
            if node in selected_blackCircle_nodes:
                border_color = 'rgba(0, 0, 0, 0.3)'
            else:
                border_color = 'rgba(211, 211, 211, 0.5)'

            node_trace['marker']['color'] += tuple([node_color])
            node_trace['marker']['line']['color'] += tuple([border_color])
            node_trace['marker']['symbol'] += tuple([node_shape])

        traceRecode.append(node_trace)

        # Calculate axis value
        xaxis_range = xaxis_range or [min([pos[0] for pos in nx.get_node_attributes(G, 'pos').values()]),
                                    max([pos[0] for pos in nx.get_node_attributes(G, 'pos').values()])]
        yaxis_range = yaxis_range or [min([pos[1] for pos in nx.get_node_attributes(G, 'pos').values()]),
                                    max([pos[1] for pos in nx.get_node_attributes(G, 'pos').values()])]
        
        annotations = []
        
        for edge in G.edges:
            # Calculate edge coordinate
            ax = (G.nodes[edge[1]]['pos'][0] + G.nodes[edge[0]]['pos'][0]) / 2
            ay = (G.nodes[edge[1]]['pos'][1] + G.nodes[edge[0]]['pos'][1]) / 2
            x = (G.nodes[edge[0]]['pos'][0] * 3 + G.nodes[edge[1]]['pos'][0]) / 4
            y = (G.nodes[edge[0]]['pos'][1] * 3 + G.nodes[edge[1]]['pos'][1]) / 4

            # Determine arrow color
            edge_str = f"{edge[0]}->{edge[1]}"
            edge_str_rev = f"{edge[1]}->{edge[0]}"

            if (edge_str in red_edges or edge_str_rev in red_edges) and (edge_str in green_edges or edge_str_rev in green_edges):
                arrowcolor = 'rgba(255, 255, 0, 0.5)'

            elif (edge_str in red_edges or edge_str_rev in red_edges):
                arrowcolor = 'rgba(255, 99, 71, 0.5)'

            elif (edge_str in green_edges or edge_str_rev in green_edges):
                arrowcolor = 'rgba(0, 128, 0, 0.5)'

            elif G.edges[edge]['relation'] == 'p2p':
                arrowcolor = 'rgba(105, 105, 105, 0.5)'

            elif G.edges[edge]['relation'] in ['c2p', 'p2c']:
                arrowcolor = 'rgba(211, 211, 211, 0.5)'

            annotations.append(dict(
                ax=ax, ay=ay, axref='x', ayref='y',
                x=x, y=y, xref='x', yref='y',
                showarrow=True,
                arrowhead=3,
                arrowsize=3,
                arrowwidth=0.8,
                arrowcolor=arrowcolor,  # use calculate color
                opacity=1
            ))

        figure = {
            "data": traceRecode,
            "layout": go.Layout(
                showlegend=True,
                legend={
                    "orientation": "v",  # orizontal legend
                    "yanchor": "top",
                    "xanchor": "left",
                    "y": 1,
                    "x": 0
                },
                hovermode='closest',
                margin={'b': 0, 'l': 0, 'r': 0, 't': 0},
                xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False, 'range': xaxis_range},
                yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False, 'range': yaxis_range},
                annotations=annotations
            )
        }
        return figure
    # Instantiate the Dash app
    app = dash.Dash(__name__)

    app.layout = html.Div([
        html.Div([
            html.Button("RESET", id="reset-button", n_clicks=0, style={"background-color": "lightgrey", "margin-right": "15px", "margin-left": "15px"}),
        ], style={"margin-bottom": "20px"}),
        dcc.Graph(id="graph", config={"scrollZoom": True}, clear_on_unhover=True),
        dcc.Store(id="square-nodes-store", data=saved_nodes["rpki_nodes"]),
        dcc.Store(id="blackCircle-nodes-store", data=saved_nodes["collector_nodes"]),
        dcc.Store(id="hacker-node-store", data=saved_nodes["hacker_node"][0]),
        dcc.Store(id="victim-node-store", data=saved_nodes["victim_node"][0]),
        dcc.Store(id="xaxis-range", data=None),
        dcc.Store(id="yaxis-range", data=None),
        dcc.Store(id="results-store", data=results)
    ])


    # Callback to update graph on node click
    @app.callback(
        [Output("graph", "figure"),
        Output("square-nodes-store", "data"),
        Output("blackCircle-nodes-store", "data"),
        Output("hacker-node-store", "data"),
        Output("victim-node-store", "data")],
        [Input("graph", "clickData"),
        Input("reset-button", "n_clicks")],
        [State("square-nodes-store", "data"),
        State("blackCircle-nodes-store", "data"),
        State("hacker-node-store", "data"),
        State("victim-node-store", "data"),
        State("xaxis-range", "data"),
        State("yaxis-range", "data"),
        State("results-store", "data")]
    )

    def update_graph(clickData, reset_clicks, square_nodes, blackCircle_nodes, hacker_node, victim_node, xaxis_range, yaxis_range, results):
        """
        Update the graph based on user interactions (node clicks or reset).

        :param clickData: Data about the clicked node on the graph.
        :param reset_clicks: Number of clicks on the reset button.
        :param square_nodes: List of RPKI-enabled nodes.
        :param blackCircle_nodes: List of Collector nodes.
        :param hacker_node: Node identified as the Hacker.
        :param victim_node: Node identified as the Victim.
        :param xaxis_range: X-axis zoom range.
        :param yaxis_range: Y-axis zoom range.
        :param results: Attack analysis results.
        :return: Updated figure and node data.
        """
        ctx = dash.callback_context  # Get the context of the callback trigger

        # Handle missing results to avoid errors
        if not results:
            results = {"red_nodes": [], "green_nodes": [], "red_edges": [], "green_edges": []}

        # Check if the reset button was clicked
        if ctx.triggered and ctx.triggered[0]["prop_id"] == "reset-button.n_clicks":
            return create_figure(
                selected_square_nodes=square_nodes,
                selected_blackCircle_nodes=blackCircle_nodes,
                selected_red_node=hacker_node,
                selected_green_node=victim_node,
                red_nodes=results["red_nodes"],
                green_nodes=results["green_nodes"],
                red_edges=results["red_edges"],
                green_edges=results["green_edges"],
                xaxis_range=xaxis_range,
                yaxis_range=yaxis_range
            ), square_nodes, blackCircle_nodes, hacker_node, victim_node

        # Handle invalid or missing clickData
        if not clickData or "points" not in clickData or "text" not in clickData["points"][0] or clickData["points"][0]["text"] not in G.nodes():
            return create_figure(
                selected_square_nodes=square_nodes,
                selected_blackCircle_nodes=blackCircle_nodes,
                selected_red_node=hacker_node,
                selected_green_node=victim_node,
                red_nodes=results["red_nodes"],
                green_nodes=results["green_nodes"],
                red_edges=results["red_edges"],
                green_edges=results["green_edges"],
                xaxis_range=xaxis_range,
                yaxis_range=yaxis_range
            ), square_nodes, blackCircle_nodes, hacker_node, victim_node

        # Handle valid node clicks
        clicked_node = None
        # Check if clickData is valido
        if clickData and "points" in clickData and "text" in clickData["points"][0]:
            clicked_node = clickData["points"][0]["text"]

        # Determine edges to highlight based on the clicked node
        if clicked_node:
            if clicked_node in results["red_nodes"]:
                if clicked_node == hacker_node:
                    red_edges_results = []
                    green_edges_results = []
                else:
                    red_edges_results = results["paths"][clicked_node]
                    green_edges_results = []

            elif clicked_node in results["green_nodes"]:
                if clicked_node == victim_node:
                    red_edges_results = []
                    green_edges_results = []
                else:
                    red_edges_results = []
                    green_edges_results = results["paths"][clicked_node]

            return create_figure(
                selected_square_nodes=square_nodes,
                selected_blackCircle_nodes=blackCircle_nodes,
                selected_red_node=hacker_node,
                selected_green_node=victim_node,
                red_nodes=results["red_nodes"],
                green_nodes=results["green_nodes"],
                red_edges=red_edges_results,
                green_edges=green_edges_results,
                xaxis_range=xaxis_range,
                yaxis_range=yaxis_range
            ), square_nodes, blackCircle_nodes, hacker_node, victim_node
        
        # Print updated store in terminal
        print(f"Square nodes (RPKI): {square_nodes}")
        print(f"BlackCircle nodes (Collector): {blackCircle_nodes}")
        print(f"Red node (Hacker): {hacker_node}")
        print(f"Green node (Victim): {victim_node}")

        # Preserve zoom and update the figure
        return create_figure(
            selected_square_nodes=square_nodes,
            selected_blackCircle_nodes=blackCircle_nodes,
            selected_red_node=hacker_node,
            selected_green_node=victim_node,
            red_nodes=results["red_nodes"],
            green_nodes=results["green_nodes"],
            red_edges=results["red_edges"],
            green_edges=results["green_edges"],
            xaxis_range=xaxis_range,
            yaxis_range=yaxis_range
        ), square_nodes, blackCircle_nodes, hacker_node, victim_node

    # Callback to handle zoom updates
    @app.callback(
        [Output("xaxis-range", "data"),
        Output("yaxis-range", "data")],
        [Input("graph", "relayoutData")],
        [State("xaxis-range", "data"),
        State("yaxis-range", "data")]
    )
    
    def update_zoom(relayoutData, xaxis_range, yaxis_range):
        """
        Update the zoom range when the user interacts with the graph.

        :param relayoutData: Data about the graph relayout.
        :param xaxis_range: Previous X-axis zoom range.
        :param yaxis_range: Previous Y-axis zoom range.
        :return: Updated X-axis and Y-axis ranges.
        """
        if relayoutData and "xaxis.range[0]" in relayoutData:
            xaxis_range = [relayoutData["xaxis.range[0]"], relayoutData["xaxis.range[1]"]]
            yaxis_range = [relayoutData["yaxis.range[0]"], relayoutData["yaxis.range[1]"]]
        return xaxis_range, yaxis_range

    # Start the Dash app in a separate thread
    def start_dash_app():
        """
        Start the Dash server in a separate thread and handle termination gracefully.
        """
        try:
            app.run_server(debug=False)
        except SystemExit:
            print("Dash app terminated.")

    dash_thread = threading.Thread(target=start_dash_app)
    dash_thread.start()

    # Wait for the Dash app thread to complete
    dash_thread.join()

