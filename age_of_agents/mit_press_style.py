"""
MIT Press Style Configuration for Agent Systems Book Diagrams

This module defines the visual style for all diagrams following MIT Press
academic publishing conventions with a clean, minimal aesthetic.
"""

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Primary colors - MIT Press inspired (matching book-style.sty)
    'navy': '#1a365d',           # primaryblue - main color for boxes/lines
    'navy_light': '#4682B4',     # primarylightblue - secondary elements

    # Accent colors
    'teal': '#2c7a7b',           # primaryteal - accent for highlights
    'teal_light': '#20B2AA',     # Lighter teal
    'burgundy': '#B45A32',       # primaryred - alternative accent

    # Neutrals
    'black': '#1a1a1a',          # Near-black for text
    'dark_gray': '#58595B',      # primarygray for secondary text
    'medium_gray': '#7a7a7a',    # Medium gray for tertiary elements
    'light_gray': '#C8C8C8',     # lightgray for borders
    'background': '#f8f9fa',     # Light background
    'white': '#ffffff',          # White for box fills

    # Semantic colors
    'success': '#2E7D32',        # primarygreen
    'warning': '#B45A32',        # primaryred (amber-ish)
    'error': '#B45A32',          # primaryred
    'info': '#1E3C72',           # primaryblue
}

# Color schemes for different diagram types
SCHEME_ARCHITECTURE = {
    'primary': COLORS['navy'],
    'secondary': COLORS['teal'],
    'tertiary': COLORS['light_gray'],
    'text': COLORS['black'],
    'background': COLORS['white'],
}

SCHEME_FLOW = {
    'primary': COLORS['navy'],
    'secondary': COLORS['burgundy'],
    'tertiary': COLORS['light_gray'],
    'text': COLORS['black'],
    'background': COLORS['white'],
}

SCHEME_HIERARCHY = {
    'primary': COLORS['navy'],
    'secondary': COLORS['navy_light'],
    'tertiary': COLORS['teal'],
    'text': COLORS['black'],
    'background': COLORS['white'],
}

# =============================================================================
# TYPOGRAPHY
# =============================================================================

FONTS = {
    'family': 'Helvetica Neue',
    'family_fallback': 'Arial, sans-serif',
    'size_title': 16,
    'size_label': 13,
    'size_small': 11,
    'size_edge': 11,
    'weight_bold': 'bold',
    'weight_normal': 'normal',
}

# =============================================================================
# DIMENSIONS AND SPACING
# =============================================================================

DIMENSIONS = {
    # Output specifications
    'dpi': 300,
    'format': 'png',

    # Default figure sizes (inches)
    'fig_width_full': 6.5,       # Full column width
    'fig_width_half': 3.0,       # Half column width
    'fig_height_default': 4.0,

    # Box dimensions
    'box_width': 1.5,
    'box_height': 0.6,
    'box_padding': 0.1,

    # Spacing
    'margin': 0.5,
    'spacing_horizontal': 0.8,
    'spacing_vertical': 0.6,

    # Line weights (points)
    'line_weight_heavy': 2.0,
    'line_weight_normal': 1.5,
    'line_weight_light': 1.0,
    'line_weight_thin': 0.5,
}

# =============================================================================
# GRAPHVIZ ATTRIBUTES
# =============================================================================

GRAPHVIZ_GRAPH = {
    'rankdir': 'TB',
    'splines': 'polyline',
    'nodesep': '0.6',
    'ranksep': '0.8',
    'bgcolor': 'white',
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_label']),
    'pad': '0.5',
    'dpi': str(DIMENSIONS['dpi']),
}

GRAPHVIZ_NODE_BOX = {
    'shape': 'box',
    'style': 'filled,rounded',
    'fillcolor': COLORS['white'],
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_label']),
    'fontcolor': COLORS['black'],
    'penwidth': '1.5',
    'width': '1.5',
    'height': '0.5',
    'margin': '0.15,0.1',
}

GRAPHVIZ_NODE_CYLINDER = {
    'shape': 'cylinder',
    'style': 'filled',
    'fillcolor': COLORS['white'],
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_label']),
    'fontcolor': COLORS['black'],
    'penwidth': '1.5',
}

GRAPHVIZ_NODE_DIAMOND = {
    'shape': 'diamond',
    'style': 'filled',
    'fillcolor': COLORS['white'],
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['black'],
    'penwidth': '1.5',
}

GRAPHVIZ_NODE_ELLIPSE = {
    'shape': 'ellipse',
    'style': 'filled',
    'fillcolor': COLORS['background'],
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_label']),
    'fontcolor': COLORS['black'],
    'penwidth': '1.5',
}

GRAPHVIZ_NODE_INVISIBLE = {
    'shape': 'point',
    'width': '0',
    'height': '0',
}

GRAPHVIZ_EDGE = {
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['dark_gray'],
    'penwidth': '2',
    'arrowsize': '0.8',
    'arrowhead': 'vee',
}

GRAPHVIZ_EDGE_DASHED = {
    **GRAPHVIZ_EDGE,
    'style': 'dashed',
    'penwidth': '1.5',
}

GRAPHVIZ_EDGE_DOTTED = {
    **GRAPHVIZ_EDGE,
    'style': 'dotted',
    'penwidth': '1.0',
}

# Storage/persistence edge style
GRAPHVIZ_EDGE_STORAGE = {
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['dark_gray'],
    'penwidth': '1.5',
    'arrowsize': '0.8',
    'arrowhead': 'dot',
    'style': 'dashed',
}

# Error path edge style
GRAPHVIZ_EDGE_ERROR = {
    'color': COLORS['burgundy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['burgundy'],
    'penwidth': '1.5',
    'arrowsize': '0.8',
    'arrowhead': 'vee',
}

# Success path edge style
GRAPHVIZ_EDGE_SUCCESS = {
    'color': COLORS['success'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['success'],
    'penwidth': '2',
    'arrowsize': '0.8',
    'arrowhead': 'vee',
}

# Bidirectional edge style
GRAPHVIZ_EDGE_BIDIRECTIONAL = {
    'color': COLORS['navy'],
    'fontname': FONTS['family'],
    'fontsize': str(FONTS['size_small']),
    'fontcolor': COLORS['dark_gray'],
    'penwidth': '2',
    'arrowsize': '0.8',
    'arrowhead': 'vee',
    'arrowtail': 'vee',
    'dir': 'both',
}

# =============================================================================
# MATPLOTLIB CONFIGURATION
# =============================================================================

def configure_matplotlib():
    """Configure matplotlib with MIT Press style settings."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl

    plt.rcParams.update({
        # Figure
        'figure.facecolor': 'white',
        'figure.edgecolor': 'white',
        'figure.dpi': DIMENSIONS['dpi'],
        'savefig.dpi': DIMENSIONS['dpi'],
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,

        # Font
        'font.family': 'sans-serif',
        'font.sans-serif': [FONTS['family'], 'Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': FONTS['size_label'],

        # Axes
        'axes.facecolor': 'white',
        'axes.edgecolor': COLORS['light_gray'],
        'axes.linewidth': DIMENSIONS['line_weight_light'],
        'axes.labelcolor': COLORS['black'],
        'axes.titlesize': FONTS['size_title'],
        'axes.labelsize': FONTS['size_label'],

        # Grid
        'grid.color': COLORS['light_gray'],
        'grid.linewidth': DIMENSIONS['line_weight_thin'],

        # Lines
        'lines.linewidth': DIMENSIONS['line_weight_normal'],

        # Text
        'text.color': COLORS['black'],
    })

    return plt


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def attrs_to_string(attrs: dict) -> str:
    """Convert attribute dictionary to Graphviz attribute string."""
    pairs = [f'{k}="{v}"' for k, v in attrs.items()]
    return ', '.join(pairs)


def get_node_style(node_type: str) -> dict:
    """Get Graphviz node attributes by type."""
    styles = {
        'box': GRAPHVIZ_NODE_BOX,
        'cylinder': GRAPHVIZ_NODE_CYLINDER,
        'diamond': GRAPHVIZ_NODE_DIAMOND,
        'ellipse': GRAPHVIZ_NODE_ELLIPSE,
        'invisible': GRAPHVIZ_NODE_INVISIBLE,
    }
    return styles.get(node_type, GRAPHVIZ_NODE_BOX).copy()


def get_edge_style(edge_type: str) -> dict:
    """Get Graphviz edge attributes by type."""
    styles = {
        'solid': GRAPHVIZ_EDGE,
        'dashed': GRAPHVIZ_EDGE_DASHED,
        'dotted': GRAPHVIZ_EDGE_DOTTED,
        'storage': GRAPHVIZ_EDGE_STORAGE,
        'error': GRAPHVIZ_EDGE_ERROR,
        'success': GRAPHVIZ_EDGE_SUCCESS,
        'bidirectional': GRAPHVIZ_EDGE_BIDIRECTIONAL,
    }
    return styles.get(edge_type, GRAPHVIZ_EDGE).copy()


def create_highlighted_node(base_style: dict, highlight_color: str = None) -> dict:
    """Create a highlighted version of a node style."""
    style = base_style.copy()
    if highlight_color:
        style['fillcolor'] = highlight_color
        style['color'] = COLORS['navy']
    else:
        style['fillcolor'] = COLORS['teal']
        style['fontcolor'] = COLORS['white']
    return style


def create_subgraph_attrs(label: str, style: str = 'rounded') -> dict:
    """Create attributes for a subgraph/cluster."""
    return {
        'label': label,
        'style': style,
        'color': COLORS['light_gray'],
        'bgcolor': COLORS['background'],
        'fontname': FONTS['family'],
        'fontsize': str(FONTS['size_label']),
        'fontcolor': COLORS['navy'],
        'penwidth': '1.0',
        'margin': '20',
        'labeljust': 'l',
    }


# =============================================================================
# UNICODE ICONS FOR DIAGRAMS
# =============================================================================

ICONS = {
    # Process/Flow icons
    'eye': '👁',           # Perceive
    'brain': '🧠',         # Think
    'gear': '⚙',           # Act/Execute
    'database': '💾',      # Store/Learn
    'lightning': '⚡',     # Fast/Trigger
    'lock': '🔒',          # Security
    'unlock': '🔓',        # Unlocked
    'check': '✓',          # Success/Approve
    'cross': '✗',          # Fail/Deny
    'arrow_right': '→',    # Flow
    'arrow_left': '←',     # Return
    'arrow_both': '↔',     # Bidirectional
    'arrow_down': '↓',     # Down
    'arrow_up': '↑',       # Up

    # Status icons
    'green_circle': '●',   # Active/Success (use with color)
    'yellow_circle': '●',  # Warning
    'red_circle': '●',     # Error/Blocked
    'empty_circle': '○',   # Inactive

    # Agent/Entity icons
    'robot': '🤖',         # Agent
    'person': '👤',        # Human
    'group': '👥',         # Team/Council
    'shield': '🛡',        # Guardian

    # Data icons
    'doc': '📄',           # Document
    'folder': '📁',        # Collection
    'clock': '🕐',         # Time/Timeout
    'chart': '📊',         # Metrics

    # Simple ASCII alternatives (more compatible)
    'bullet': '•',
    'diamond': '◆',
    'square': '■',
    'triangle_right': '▶',
    'triangle_down': '▼',
}

# Text-based labels for icons (fallback for better compatibility)
ICON_LABELS = {
    'perceive': '[P]',
    'think': '[T]',
    'act': '[A]',
    'learn': '[L]',
    'approve': '[✓]',
    'deny': '[✗]',
    'agent': '[A]',
    'human': '[H]',
    'guardian': '[G]',
}
