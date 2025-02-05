import dash
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import networkx as nx
import json
import os
import signal
import threading

def run_dash_app(as_data, start_configuration):
    """
    Run the Dash app for visualizing and interacting with the AS topology.
    
    :param as_data: Dictionary containing the Autonomous System (AS) topology.
    :param start_configuration: Initial configuration for RPKI, Collector, Hacker, and Victim nodes.
    """

    start_as = list(as_data.keys())[0]  # Define the root AS for the graph

    def build_graph_from_topology(as_data):
        """
        Build a directed graph from the given AS topology using NetworkX.

        :param as_data: Dictionary containing the AS topology.
        :return: A directed NetworkX graph representing the AS topology.
        """
        G = nx.DiGraph()

        def add_to_graph(node):
            """
            Recursively add nodes and edges to the graph based on parent-to-customer and peer-to-peer relationships.
            """
            # Add child nodes (provider-to-customer relationship)       
            for child in as_data[node].get("p2c", []):
                G.add_edge(node, child, relation="c2p")  # Add c2p relationship
                add_to_graph(child)

            # Add peer nodes (peer-to-peer relationship)
            for peer in as_data[node].get("p2p", []):
                if not G.has_edge(node, peer):  # Avoid duplicate edges
                    G.add_edge(node, peer, relation="p2p")  # Add bidirectional p2p relationship
                    G.add_edge(peer, node, relation="p2p")

        add_to_graph(start_as)
        return G

    # Build the graph from the AS topology
    G = build_graph_from_topology(as_data)

    # Generate positions for the nodes using Graphviz for a tree structure layout
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot", root=start_as)

    # Add positions to the graph nodes
    for node in G.nodes:
        x, y = pos[node]
        G.nodes[node]['pos'] = (x, y)
    
    traceRecode = []  # contains edge_trace, node_trace, text_trace

    # Define colors for edges based on their type
    edge_colors = {
        'c2p': 'LightGray',
        'p2c': 'LightGray',
        'p2p': 'dimgray'
    }

    # Function to create the Dash figure for the graph
    def create_figure(selected_square_nodes=None, selected_blackCircle_nodes=None, 
                      selected_red_node=None, selected_green_node=None, 
                      xaxis_range=None, yaxis_range=None):
        """
        Create the figure for the AS topology graph with visual elements for different node types.

        :param selected_square_nodes: List of nodes selected as RPKI.
        :param selected_blackCircle_nodes: List of nodes selected as Collectors.
        :param selected_red_node: List of nodes selected as Hackers.
        :param selected_green_node: List of nodes selected as Victims.
        :param xaxis_range: Range for the x-axis in the graph.
        :param yaxis_range: Range for the y-axis in the graph.
        :return: A Plotly figure object.
        """
        traceRecode = []  # Contains edge traces, node traces, and legend elements

        # Separate edges based on their relationship types (p2p, c2p)
        p2p_edges_x, p2p_edges_y = [], []
        c2p_edges_x, c2p_edges_y = [], []

        # Iterate over edges in the graph
        for edge in G.edges:
            x0, y0 = G.nodes[edge[1]]['pos']  # Position of the child node
            x1, y1 = G.nodes[edge[0]]['pos']  # Position of the parent node
            relation = G.edges[edge]['relation']

            # Categorize edges based on relationship type
            if relation == 'p2p':
                p2p_edges_x.extend([x0, x1, None])
                p2p_edges_y.extend([y0, y1, None])
            elif relation in ['c2p', 'p2c']:
                c2p_edges_x.extend([x0, x1, None])
                c2p_edges_y.extend([y0, y1, None])

        # Create a scatter trace for p2p edges
        p2p_trace = go.Scatter(
            x=p2p_edges_x,
            y=p2p_edges_y,
            mode='lines',
            line={'width': 0.8, 'color': 'dimgray'},
            opacity=1,
            hoverinfo='skip',
            name='peer-to-peer (bidirectional)',
            showlegend=True
        )
        traceRecode.append(p2p_trace)

        # Create a scatter trace for c2p edges
        c2p_trace = go.Scatter(
            x=c2p_edges_x,
            y=c2p_edges_y,
            mode='lines',
            line={'width': 0.8, 'color': 'LightGray'},
            opacity=1,
            hoverinfo='skip',
            name='customer-to-provider',
            showlegend=True
        )
        traceRecode.append(c2p_trace)

        # Create legend elements for node types
        not_rpki_trace = go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=20,
                color='rgba(0,0,0,0)',
                line=dict(width=2, color='LightGray'),
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
                line=dict(width=2, color='LightGray'),
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
                color='rgba(0,0,0,0)',  # Trasparente
                line=dict(width=2, color='Black')
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
                color='darkred',
                line=dict(width=2, color='darkred'),
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
                color='greenyellow',
                line=dict(width=2, color='greenyellow'),
                symbol='circle'
            ),
            name='Victim',
            showlegend=True
        )
        # Add legend traces
        traceRecode.append(not_rpki_trace)
        traceRecode.append(rpki_trace)
        traceRecode.append(collector_trace)
        traceRecode.append(hacker_trace)
        traceRecode.append(victim_trace)
        # Create node traces with colors, shapes, and text labels
        node_trace = go.Scatter(
            x=[],
            y=[],
            mode='markers+text',  # Add 'text' to include labels
            hoverinfo="text",
            marker={
                'size': 20,
                'color': [],  # Fill colors
                'line': {'width': 2, 'color': []},  # Border colors
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
            node_trace['text'] += tuple([node])  # Node name as label
            node_trace['hovertext'] += tuple([node])  # Node name for hover text

            # Determine the fill color based on node type
            if node in selected_red_node:
                node_color = 'darkred'  # Hacker
            elif node in selected_green_node:
                node_color = 'green'  # Victim
            else:
                node_color = 'SkyBlue'  # Default color

            # Determine shape based on RPKI selection
            node_shape = 'square' if node in selected_square_nodes else 'circle'

            # Determine border color for Collector nodes
            border_color = 'Black' if node in selected_blackCircle_nodes else 'LightGray'

            # Add color, border, and shape to node markers
            node_trace['marker']['color'] += tuple([node_color])
            node_trace['marker']['line']['color'] += tuple([border_color])
            node_trace['marker']['symbol'] += tuple([node_shape])

        traceRecode.append(node_trace)

        # Set axis ranges if not provided
        xaxis_range = xaxis_range or [
            min([pos[0] for pos in nx.get_node_attributes(G, 'pos').values()]),
            max([pos[0] for pos in nx.get_node_attributes(G, 'pos').values()])
        ]
        yaxis_range = yaxis_range or [
            min([pos[1] for pos in nx.get_node_attributes(G, 'pos').values()]),
            max([pos[1] for pos in nx.get_node_attributes(G, 'pos').values()])
        ]

        # Create the final figure
        figure = {
            "data": traceRecode,
            "layout": go.Layout(
                showlegend=True,
                legend={
                    "orientation": "v",  # Legenda orizzontale
                    "yanchor": "top",
                    "xanchor": "left",
                    "y": 1,  # Posiziona la legenda sotto i pulsanti
                    "x": 0
                },
                hovermode='closest',
                margin={'b': 0, 'l': 0, 'r': 0, 't': 0},
                xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False, 'range': xaxis_range},
                yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False, 'range': yaxis_range},
                annotations=[
                    dict(
                        ax=(G.nodes[edge[1]]['pos'][0] + G.nodes[edge[0]]['pos'][0]) / 2,
                        ay=(G.nodes[edge[1]]['pos'][1] + G.nodes[edge[0]]['pos'][1]) / 2, axref='x', ayref='y',
                        x=(G.nodes[edge[0]]['pos'][0] * 3 + G.nodes[edge[1]]['pos'][0]) / 4,
                        y=(G.nodes[edge[0]]['pos'][1] * 3 + G.nodes[edge[1]]['pos'][1]) / 4, xref='x', yref='y',
                        showarrow=True,
                        arrowhead=3,
                        arrowsize=3,
                        arrowwidth=0.8,
                        arrowcolor=edge_colors[G.edges[edge]['relation']],
                        opacity=1
                    ) for edge in G.edges
                ]
            )
        }
        return figure


    def shutdown_server():
        """
        Safely terminate the Dash server.
        """
        shutdown_event = threading.Event()
        shutdown_event.set()
        os.kill(os.getpid(), signal.SIGTERM)

    # Initialize the Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # Define the layout for the Dash app
    app.layout = html.Div([
        html.Div([
            html.Button("RPKI", id="rpki-button", n_clicks=0, style={"background-color": "white", "margin-right": "15px", "margin-left": "15px"}),
            html.Button("COLLECTOR", id="collector-button", n_clicks=0, style={"background-color": "white", "margin-right": "15px"}),
            html.Button("HACKER", id="hacker-button", n_clicks=0, style={"background-color": "white", "margin-right": "15px"}),
            html.Button("VICTIM", id="victim-button", n_clicks=0, style={"background-color": "white", "margin-right": "15px"}),
            html.Button("RESET", id="reset-button", n_clicks=0, style={"background-color": "lightgrey", "margin-right": "15px"}),
            html.Button("SAVE", id="save-button", n_clicks=0, style={"background-color": "lightgrey"})
        ], style={"margin-bottom": "20px"}),
        dcc.Graph(id="graph", config={"scrollZoom": True}, clear_on_unhover=True),
        dcc.Store(id="square-nodes-store", data=start_configuration["rpki_nodes"]),
        dcc.Store(id="blackCircle-nodes-store", data=start_configuration["collector_nodes"]),
        dcc.Store(id="hacker-node-store", data=start_configuration["hacker_node"]),
        dcc.Store(id="victim-node-store", data=start_configuration["victim_node"]),
        dcc.Store(id="rpki-mode", data=False),
        dcc.Store(id="collector-mode", data=False),
        dcc.Store(id="hacker-mode", data=False),
        dcc.Store(id="victim-mode", data=False),
        dcc.Store(id="xaxis-range", data=None),
        dcc.Store(id="yaxis-range", data=None),

        # Modal for error message when saving without valid selections
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Save Error")),
                dbc.ModalBody("You must select both a HACKER and a VICTIM node before saving."),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-error-modal", className="ms-auto", n_clicks=0)
                ),
            ],
            id="error-modal",
            is_open=False,  # Initially, the modal is closed
        ),

        # Modal for confirming the save action
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Save Confirmation")),
                dbc.ModalBody("Are you sure you want to save this configuration?"),
                dbc.ModalFooter(
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Button("Yes", id="confirm-save-button", className="ms-auto", n_clicks=0),
                                width="auto"
                            ),
                            dbc.Col(
                                dbc.Button("No", id="cancel-save-button", className="ms-auto", n_clicks=0),
                                width="auto",
                                style={"text-align": "right"}
                            ),
                        ],
                        justify="between",
                        className="w-100"
                    )
                ),
            ],
            id="confirm-modal",
            is_open=False,  # Initially, the modal is closed
        ),
    ])

    # Callback for toggling modes (RPKI, Collector, Hacker, Victim)
    @app.callback(
        [
            Output("rpki-button", "style"),
            Output("rpki-mode", "data"),
            Output("collector-button", "style"),
            Output("collector-mode", "data"),
            Output("hacker-button", "style"),
            Output("hacker-mode", "data"),
            Output("victim-button", "style"),
            Output("victim-mode", "data"),
        ],
        [
            Input("rpki-button", "n_clicks"),
            Input("collector-button", "n_clicks"),
            Input("hacker-button", "n_clicks"),
            Input("victim-button", "n_clicks"),
            Input("reset-button", "n_clicks"),
        ],
        [
            State("rpki-mode", "data"),
            State("collector-mode", "data"),
            State("hacker-mode", "data"),
            State("victim-mode", "data"),
        ]
    )
    def toggle_modes(rpki_clicks, collector_clicks, hacker_clicks, victim_clicks, reset_clicks, rpki_mode, collector_mode, hacker_mode, victim_mode):
        """
        Handle button clicks to toggle modes (RPKI, Collector, Hacker, Victim).
        
        :param rpki_clicks: Number of clicks on the RPKI button.
        :param collector_clicks: Number of clicks on the Collector button.
        :param hacker_clicks: Number of clicks on the Hacker button.
        :param victim_clicks: Number of clicks on the Victim button.
        :param reset_clicks: Number of clicks on the Reset button.
        :param rpki_mode: Current state of RPKI mode.
        :param collector_mode: Current state of Collector mode.
        :param hacker_mode: Current state of Hacker mode.
        :param victim_mode: Current state of Victim mode.
        :return: Updated button styles and mode states.
        """
        ctx = dash.callback_context

        # Reset all modes and button styles when RESET is clicked
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == "reset-button.n_clicks":
            return (
                {"background-color": "white", "margin-right": "15px"}, False,
                {"background-color": "white", "margin-right": "15px"}, False,
                {"background-color": "white", "margin-right": "15px"}, False,
                {"background-color": "white", "margin-right": "15px"}, False,
            )

        # Identify the button that triggered the callback
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Determine which mode to activate or deactivate
        rpki_active = button_id == "rpki-button" and not rpki_mode
        collector_active = button_id == "collector-button" and not collector_mode
        hacker_active = button_id == "hacker-button" and not hacker_mode
        victim_active = button_id == "victim-button" and not victim_mode

        # Update button styles and mode states
        return (
            {"background-color": "lightblue" if rpki_active else "white", "margin-right": "15px"}, rpki_active,
            {"background-color": "lightblue" if collector_active else "white", "margin-right": "15px"}, collector_active,
            {"background-color": "lightblue" if hacker_active else "white", "margin-right": "15px"}, hacker_active,
            {"background-color": "lightblue" if victim_active else "white", "margin-right": "15px"}, victim_active,
        )


    # Callback to update graph on node click or reset
    @app.callback(
        [
            Output("graph", "figure"),
            Output("square-nodes-store", "data"),
            Output("blackCircle-nodes-store", "data"),
            Output("hacker-node-store", "data"),
            Output("victim-node-store", "data"),
        ],
        [
            Input("graph", "clickData"),
            Input("reset-button", "n_clicks"),
        ],
        [
            State("square-nodes-store", "data"),
            State("blackCircle-nodes-store", "data"),
            State("hacker-node-store", "data"),
            State("victim-node-store", "data"),
            State("rpki-mode", "data"),
            State("collector-mode", "data"),
            State("hacker-mode", "data"),
            State("victim-mode", "data"),
            State("xaxis-range", "data"),
            State("yaxis-range", "data"),
        ]
    )
    def update_graph(
        clickData, reset_clicks, square_nodes, blackCircle_nodes, hacker_node, victim_node,
        rpki_mode, collector_mode, hacker_mode, victim_mode, xaxis_range, yaxis_range
    ):
        """
        Update the graph based on user interactions such as node clicks or reset button clicks.
        
        :param clickData: Data about the node clicked on the graph.
        :param reset_clicks: Number of clicks on the Reset button.
        :param square_nodes: List of nodes marked as RPKI nodes.
        :param blackCircle_nodes: List of nodes marked as Collector nodes.
        :param hacker_node: Node selected as Hacker.
        :param victim_node: Node selected as Victim.
        :param rpki_mode: Whether RPKI mode is active.
        :param collector_mode: Whether Collector mode is active.
        :param hacker_mode: Whether Hacker mode is active.
        :param victim_mode: Whether Victim mode is active.
        :param xaxis_range: Current x-axis range of the graph.
        :param yaxis_range: Current y-axis range of the graph.
        :return: Updated graph figure and node lists.
        """
        ctx = dash.callback_context
        if ctx.triggered and ctx.triggered[0]["prop_id"] == "reset-button.n_clicks":
            # Reset zoom as well when resetting nodes
            print("Reset clicked. Square nodes (RPKI): [], BlackCircle nodes (Collector): [], Red nodes (Hacker): [], Green nodes (Victim): []")
            return create_figure([], [], [], [], xaxis_range, yaxis_range), [], [], [], []

        # If no clickData or invalid clickData, just return the same figure with updated zoom
        if not clickData or "points" not in clickData or "text" not in clickData["points"][0] or clickData["points"][0]["text"] not in G.nodes():
            print(f"Updated Zoom. Square nodes (RPKI): {square_nodes}, BlackCircle nodes (Collector): {blackCircle_nodes},"
                  f" Red node (Hacker): {hacker_node}, Green node (Victim): {victim_node}")
            return create_figure(square_nodes, blackCircle_nodes, hacker_node, victim_node, xaxis_range, yaxis_range), square_nodes, blackCircle_nodes, hacker_node, victim_node

        clicked_node = clickData["points"][0]["text"]

        # Hacker mode: only one node can be selected
        if hacker_mode:
            if clicked_node in hacker_node:
                hacker_node.remove(clicked_node)  # Deselect node
            else:
                hacker_node = [clicked_node]  # Replace with new Hacker node
            return create_figure(square_nodes, blackCircle_nodes, hacker_node, victim_node, xaxis_range, yaxis_range), square_nodes, blackCircle_nodes, hacker_node, victim_node

        # Victim mode: only one node can be selected
        if victim_mode:
            if clicked_node in victim_node:
                victim_node.remove(clicked_node)  # Deseleziona il nodo
            else:
                victim_node = [clicked_node]  # Sostituisci con il nuovo nodo VICTIM
            return create_figure(square_nodes, blackCircle_nodes, hacker_node, victim_node, xaxis_range, yaxis_range), square_nodes, blackCircle_nodes, hacker_node, victim_node
        
        # RPKI mode: multiple nodes can be selected
        if rpki_mode:
            if clicked_node in square_nodes:
                square_nodes.remove(clicked_node)
            else:
                square_nodes.append(clicked_node)

        # Collector mode: multiple nodes can be selected
        if collector_mode:
            if clicked_node in blackCircle_nodes:
                blackCircle_nodes.remove(clicked_node)
            else:
                blackCircle_nodes.append(clicked_node)

        # Preserve zoom and update the graph
        print(f"Updated node selections - RPKI: {square_nodes}, Collector: {blackCircle_nodes}, Hacker: {hacker_node}, Victim: {victim_node}")
        return create_figure(square_nodes, blackCircle_nodes, hacker_node, victim_node, xaxis_range, yaxis_range), square_nodes, blackCircle_nodes, hacker_node, victim_node

    
    # Callback to handle zoom adjustments
    @app.callback(
        [Output("xaxis-range", "data"),
        Output("yaxis-range", "data")],
        [Input("graph", "relayoutData")],
        [State("xaxis-range", "data"),
        State("yaxis-range", "data")]
    )
    def update_zoom(relayoutData, xaxis_range, yaxis_range):
        """
        Update the graph's zoom level based on user interactions.
        
        :param relayoutData: Data from user zoom interactions.
        :param xaxis_range: Current x-axis range.
        :param yaxis_range: Current y-axis range.
        :return: Updated x-axis and y-axis ranges.
        """
        if relayoutData and "xaxis.range[0]" in relayoutData:
            xaxis_range = [relayoutData["xaxis.range[0]"], relayoutData["xaxis.range[1]"]]
            yaxis_range = [relayoutData["yaxis.range[0]"], relayoutData["yaxis.range[1]"]]
        return xaxis_range, yaxis_range

    # Callback to handle save functionality
    @app.callback(
        [
            Output("save-button", "style"),
            Output("error-modal", "is_open"),
            Output("confirm-modal", "is_open")
        ],
        [
            Input("save-button", "n_clicks"),
            Input("close-error-modal", "n_clicks"),
            Input("confirm-save-button", "n_clicks"),
            Input("cancel-save-button", "n_clicks")
        ],
        [
            State("square-nodes-store", "data"),
            State("blackCircle-nodes-store", "data"),
            State("hacker-node-store", "data"),
            State("victim-node-store", "data"),
            State("error-modal", "is_open"),
            State("confirm-modal", "is_open")
        ],
    )
    def save_and_confirm(
        n_clicks_save, n_clicks_close_error, n_clicks_confirm, n_clicks_cancel,
        square_nodes, blackCircle_nodes, hacker_node, victim_node,
        is_error_modal_open, is_confirm_modal_open
    ):
        """
        Handle save action, including validation and confirmation.

        :param n_clicks_save: Number of clicks on the Save button.
        :param n_clicks_close_error: Number of clicks to close the error modal.
        :param n_clicks_confirm: Number of clicks to confirm saving.
        :param n_clicks_cancel: Number of clicks to cancel saving.
        :param square_nodes: List of RPKI nodes.
        :param blackCircle_nodes: List of Collector nodes.
        :param hacker_node: Selected Hacker node.
        :param victim_node: Selected Victim node.
        :param is_error_modal_open: Whether the error modal is currently open.
        :param is_confirm_modal_open: Whether the confirmation modal is currently open.
        :return: Updated styles and modal states.
        """
        ctx = dash.callback_context
        if ctx.triggered:
            trigger = ctx.triggered[0]["prop_id"].split(".")[0]

            if trigger == "save-button" and n_clicks_save > 0:
                # Ensure both a Hacker and Victim node are selected
                if not hacker_node or not victim_node:
                    # Open error modal
                    return {"background-color": "red"}, True, False

                # Open confirmation modal
                return {"background-color": "lightblue"}, False, True

            if trigger == "close-error-modal" and n_clicks_close_error > 0:
                # Close error modal
                return {"background-color": "lightgrey"}, False, is_confirm_modal_open

            if trigger == "cancel-save-button" and n_clicks_cancel > 0:
                # Close confirmation modal
                return {"background-color": "lightgrey"}, is_error_modal_open, False

            if trigger == "confirm-save-button" and n_clicks_confirm > 0:
                # Save the configuration and terminate the server
                with open("output/saved_nodes.json", "w") as f:
                    json.dump({
                        "rpki_nodes": square_nodes,
                        "collector_nodes": blackCircle_nodes,
                        "hacker_node": hacker_node,
                        "victim_node": victim_node
                    }, f)

                with open("terminate.flag", "w") as f:
                    f.write("terminate")

                shutdown_server()

        return {"background-color": "white"}, is_error_modal_open, is_confirm_modal_open

    # Run the Dash app
    try:
        app.run(debug=True, dev_tools_hot_reload=True, use_reloader=True)
    except SystemExit:
        print("Dash app terminated.")
